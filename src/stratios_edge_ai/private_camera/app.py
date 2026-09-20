"""Authenticated FastAPI application for the private camera."""

import asyncio
import hmac
import json
import os
import tempfile
import time
import zipfile
from contextlib import asynccontextmanager, suppress
from pathlib import Path
from typing import Annotated

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response, status
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from pydantic import BaseModel
from starlette.background import BackgroundTask

from .archive import Archive, ArchiveFullError
from .config import CameraServerConfig
from .database import Database
from .security import (
    SESSION_COOKIE,
    LoginLimiter,
    new_token,
    token_hash,
    verify_password,
)

WEB_ROOT = Path(__file__).with_name("web")
LIVE_MJPEG_BOUNDARY = "edge-camera-frame"


class LoginRequest(BaseModel):
    username: str
    password: str


def create_app(config: CameraServerConfig | None = None) -> FastAPI:
    config = config or CameraServerConfig.from_env()
    config.prepare()
    database = Database(config.database_path)
    database.initialize()
    archive = Archive(database, config.archive_dir, config.max_archive_bytes)
    limiter = LoginLimiter()

    async def expire_on_schedule() -> None:
        while True:
            archive.expire(int(time.time()) - config.retention_hours * 3600)
            await asyncio.sleep(config.retention_interval_minutes * 60)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        retention_task = asyncio.create_task(expire_on_schedule())
        try:
            yield
        finally:
            retention_task.cancel()
            with suppress(asyncio.CancelledError):
                await retention_task

    app = FastAPI(
        title="StratiosAI Private Camera",
        docs_url=None,
        redoc_url=None,
        lifespan=lifespan,
    )
    app.state.config = config
    app.state.database = database
    app.state.archive = archive

    def session_user(request: Request) -> dict[str, int | str]:
        raw_token = request.cookies.get(SESSION_COOKIE)
        if not raw_token:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
        now = int(time.time())
        with database.connect() as connection:
            row = connection.execute(
                """
                SELECT sessions.token_hash, sessions.csrf_token, sessions.expires_at,
                       users.id AS user_id, users.username, users.is_admin
                FROM sessions JOIN users ON users.id = sessions.user_id
                WHERE sessions.token_hash = ? AND sessions.expires_at > ?
                """,
                (token_hash(raw_token), now),
            ).fetchone()
            if row is None:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
            connection.execute(
                "UPDATE sessions SET last_seen_at = ? WHERE token_hash = ?",
                (now, row["token_hash"]),
            )
        return dict(row)

    def require_csrf(
        request: Request,
        user: Annotated[dict[str, int | str], Depends(session_user)],
        x_csrf_token: Annotated[str | None, Header()] = None,
    ) -> dict[str, int | str]:
        if not x_csrf_token or not hmac.compare_digest(str(user["csrf_token"]), x_csrf_token):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="invalid CSRF token")
        return user

    def require_ingest_token(x_ingest_token: str | None = Header(default=None)) -> None:
        if not config.ingest_token:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE)
        if not x_ingest_token or not hmac.compare_digest(config.ingest_token, x_ingest_token):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; img-src 'self' data:; media-src 'self'; "
            "style-src 'self'; script-src 'self'; connect-src 'self'"
        )
        return response

    @app.get("/", response_class=HTMLResponse)
    def index() -> HTMLResponse:
        return HTMLResponse((WEB_ROOT / "index.html").read_text(encoding="utf-8"))

    @app.get("/app.css")
    def css() -> FileResponse:
        return FileResponse(WEB_ROOT / "app.css", media_type="text/css")

    @app.get("/app.js")
    def javascript() -> FileResponse:
        return FileResponse(WEB_ROOT / "app.js", media_type="text/javascript")

    @app.post("/api/login")
    def login(payload: LoginRequest, request: Request, response: Response) -> dict[str, str]:
        client = request.client.host if request.client else "unknown"
        key = f"{client}:{payload.username.casefold()}"
        if not limiter.allow(key):
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS)
        with database.connect() as connection:
            row = connection.execute(
                "SELECT id, password_hash FROM users WHERE username = ?",
                (payload.username,),
            ).fetchone()
        if row is None or not verify_password(row["password_hash"], payload.password):
            limiter.fail(key)
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
        limiter.success(key)
        raw_token = new_token()
        csrf = new_token()
        now = int(time.time())
        expires = now + config.session_days * 86400
        with database.connect() as connection:
            connection.execute(
                """
                INSERT INTO sessions
                    (token_hash, user_id, csrf_token, created_at, expires_at, last_seen_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (token_hash(raw_token), row["id"], csrf, now, expires, now),
            )
        response.set_cookie(
            SESSION_COOKIE,
            raw_token,
            max_age=config.session_days * 86400,
            httponly=True,
            secure=config.secure_cookies,
            samesite="strict",
            path="/",
        )
        return {"status": "ok", "csrf_token": csrf}

    @app.get("/api/session")
    def session(
        user: Annotated[dict[str, int | str], Depends(session_user)],
    ) -> dict[str, int | str]:
        return {
            "username": user["username"],
            "is_admin": user["is_admin"],
            "expires_at": user["expires_at"],
            "csrf_token": user["csrf_token"],
        }

    @app.post("/api/logout")
    def logout(
        request: Request,
        response: Response,
        _user: Annotated[dict[str, int | str], Depends(require_csrf)],
    ) -> dict[str, str]:
        raw_token = request.cookies.get(SESSION_COOKIE, "")
        with database.connect() as connection:
            connection.execute(
                "DELETE FROM sessions WHERE token_hash = ?", (token_hash(raw_token),)
            )
        response.delete_cookie(SESSION_COOKIE, path="/")
        return {"status": "ok"}

    @app.post("/api/logout-all")
    def logout_all(
        response: Response,
        user: Annotated[dict[str, int | str], Depends(require_csrf)],
    ) -> dict[str, str]:
        with database.connect() as connection:
            connection.execute("DELETE FROM sessions WHERE user_id = ?", (user["user_id"],))
        response.delete_cookie(SESSION_COOKIE, path="/")
        return {"status": "ok"}

    @app.get("/api/health")
    def health(
        _user: Annotated[dict[str, int | str], Depends(session_user)],
    ) -> dict[str, object]:
        with database.connect() as connection:
            row = connection.execute(
                "SELECT payload_json, updated_at FROM camera_health WHERE singleton = 1"
            ).fetchone()
        return {
            "server": "ok",
            "archive_bytes": archive.bytes_used(),
            "camera": json.loads(row["payload_json"]) if row else None,
            "camera_updated_at": row["updated_at"] if row else None,
        }

    @app.post("/api/ingest/health", dependencies=[Depends(require_ingest_token)])
    async def ingest_health(request: Request) -> dict[str, str]:
        payload = await request.json()
        encoded = json.dumps(payload, separators=(",", ":"), sort_keys=True)
        if len(encoded) > 16384:
            raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE)
        with database.connect() as connection:
            connection.execute(
                """
                INSERT INTO camera_health(singleton, payload_json, updated_at) VALUES(1, ?, ?)
                ON CONFLICT(singleton) DO UPDATE SET
                    payload_json = excluded.payload_json,
                    updated_at = excluded.updated_at
                """,
                (encoded, int(time.time())),
            )
        return {"status": "ok"}

    @app.post("/api/ingest/segment", dependencies=[Depends(require_ingest_token)])
    async def ingest_segment(
        request: Request,
        x_segment_started_at: int = Header(),
        x_segment_ended_at: int = Header(),
        x_segment_extension: str = Header(default=".mp4"),
        x_segment_sha256: str | None = Header(default=None),
        x_segment_motion_score: float | None = Header(default=None),
        x_segment_motion_detected: bool | None = Header(default=None),
    ) -> dict[str, str]:
        body = await request.body()
        try:
            latest_accepted_time = int(time.time()) + config.max_clock_skew_seconds
            if x_segment_started_at > latest_accepted_time or x_segment_ended_at > latest_accepted_time:
                raise ValueError("segment timestamp is too far ahead; synchronize the Pi clock")
            segment_id, created = archive.ingest(
                body,
                x_segment_started_at,
                x_segment_ended_at,
                x_segment_extension,
                x_segment_sha256,
                x_segment_motion_score,
                x_segment_motion_detected,
            )
        except ArchiveFullError as exc:
            raise HTTPException(status_code=status.HTTP_507_INSUFFICIENT_STORAGE) from exc
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
            ) from exc
        return {
            "status": "ok",
            "segment_id": segment_id,
            "result": "created" if created else "already-present",
        }

    @app.get("/api/segments")
    def segments(
        _user: Annotated[dict[str, int | str], Depends(session_user)],
        since: int | None = None,
        until: int | None = None,
    ) -> dict[str, object]:
        now = int(time.time())
        since = since if since is not None else now - config.retention_hours * 3600
        until = until if until is not None else now + config.max_clock_skew_seconds
        return {"segments": archive.list_segments(since, until)}

    def segment_or_404(segment_id: str) -> tuple[Path, dict[str, int | str]]:
        resolved = archive.resolve(segment_id)
        if resolved is None or not resolved[0].is_file():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
        return resolved

    @app.get("/api/segments/{segment_id}/media")
    def media(
        segment_id: str,
        _user: Annotated[dict[str, int | str], Depends(session_user)],
    ) -> FileResponse:
        path, _ = segment_or_404(segment_id)
        return FileResponse(path, media_type="video/mp4")

    @app.get("/api/segments/{segment_id}/thumbnail")
    def thumbnail(
        segment_id: str,
        _user: Annotated[dict[str, int | str], Depends(session_user)],
    ) -> FileResponse:
        thumbnail_path = archive.thumbnail_path(segment_id)
        if thumbnail_path is not None and not thumbnail_path.is_file():
            archive.create_thumbnail(segment_id)
        if thumbnail_path is None or not thumbnail_path.is_file():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
        return FileResponse(thumbnail_path, media_type="image/jpeg")

    @app.get("/api/segments/export")
    def export_range(
        since: int,
        until: int,
        _user: Annotated[dict[str, int | str], Depends(session_user)],
    ) -> FileResponse:
        try:
            selections = archive.export_segments(since, until, config.max_export_bytes)
        except ArchiveFullError as exc:
            raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=str(exc)) from exc
        except (FileNotFoundError, ValueError) as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        descriptor, temporary_name = tempfile.mkstemp(
            prefix="edge-camera-export-", suffix=".zip", dir=config.export_dir
        )
        os.close(descriptor)
        temporary_path = Path(temporary_name)
        try:
            with zipfile.ZipFile(temporary_path, "w", compression=zipfile.ZIP_STORED) as bundle:
                manifest: list[dict[str, int | str]] = []
                for media_path, metadata in selections:
                    archive_name = f"recordings/{metadata['started_at']}-{metadata['id']}.mp4"
                    bundle.write(media_path, archive_name)
                    manifest.append({key: metadata[key] for key in ("id", "started_at", "ended_at", "sha256")})
                bundle.writestr("manifest.json", json.dumps(manifest, indent=2))
            temporary_path.chmod(0o600)
        except Exception:
            temporary_path.unlink(missing_ok=True)
            raise
        return FileResponse(
            temporary_path,
            media_type="application/zip",
            filename=f"edge-camera-{since}-{until}.zip",
            background=BackgroundTask(temporary_path.unlink, missing_ok=True),
        )

    @app.get("/api/segments/{segment_id}/export")
    def export(
        segment_id: str,
        _user: Annotated[dict[str, int | str], Depends(session_user)],
    ) -> FileResponse:
        path, metadata = segment_or_404(segment_id)
        return FileResponse(
            path,
            media_type="video/mp4",
            filename=f"edge-camera-{metadata['started_at']}.mp4",
        )

    @app.delete("/api/segments/{segment_id}")
    def delete_segment(
        segment_id: str,
        _user: Annotated[dict[str, int | str], Depends(require_csrf)],
    ) -> dict[str, str]:
        if not archive.delete(segment_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
        return {"status": "deleted"}

    @app.post("/api/retention/run")
    def retention(
        _user: Annotated[dict[str, int | str], Depends(require_csrf)],
    ) -> dict[str, object]:
        expired = archive.expire(int(time.time()) - config.retention_hours * 3600)
        return {"status": "ok", "expired_segment_ids": expired}

    @app.get("/api/live")
    async def live(
        _user: Annotated[dict[str, int | str], Depends(session_user)],
    ) -> StreamingResponse:
        if not config.pi_live_url or not config.pi_live_token:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE)

        async def stream():
            async with (
                httpx.AsyncClient(
                    timeout=None,
                    verify=str(config.pi_live_ca_file) if config.pi_live_ca_file else True,
                ) as client,
                client.stream("GET", config.pi_live_url, headers={"X-Live-Token": config.pi_live_token}) as upstream,
            ):
                upstream.raise_for_status()
                async for chunk in upstream.aiter_bytes():
                    yield chunk

        return StreamingResponse(
            stream(),
            media_type=f"multipart/x-mixed-replace; boundary={LIVE_MJPEG_BOUNDARY}",
        )

    return app
