"""Archive ingestion, indexing, retention, deletion, and storage safeguards."""

from __future__ import annotations

import hashlib
import hmac
import os
import shutil
import subprocess
import time
import uuid
from pathlib import Path

from .database import Database
from .events import EventSuggestion


class ArchiveFullError(RuntimeError):
    pass


class Archive:
    def __init__(self, database: Database, directory: Path, max_bytes: int):
        self.database = database
        self.directory = directory.resolve()
        self.max_bytes = max_bytes

    def bytes_used(self) -> int:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT COALESCE(SUM(size_bytes), 0) AS total FROM segments"
            ).fetchone()
        return int(row["total"])

    def ingest_event(self, event: EventSuggestion) -> bool:
        """Persist an idempotent detector event without touching source media."""

        with self.database.connect() as connection:
            existing = connection.execute("SELECT id FROM events WHERE id = ?", (event.event_id,)).fetchone()
            if existing is not None:
                return False
            connection.execute(
                """
                INSERT INTO events
                    (id, occurred_at, track_id, label, confidence, zone, count,
                     direction, segment_id, thumbnail_path, clip_start, clip_end, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.event_id, event.occurred_at, event.track_id, event.label,
                    event.confidence, event.zone, event.count, event.direction,
                    event.segment_id, event.thumbnail_path, event.clip_start,
                    event.clip_end, int(time.time()),
                ),
            )
        return True

    def list_events(self, since: int, until: int) -> list[dict[str, int | float | str | None]]:
        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT id, occurred_at, track_id, label, confidence, zone, count,
                       direction, segment_id, thumbnail_path, clip_start, clip_end
                FROM events
                WHERE occurred_at BETWEEN ? AND ?
                ORDER BY occurred_at DESC
                """,
                (since, until),
            ).fetchall()
        return [dict(row) for row in rows]

    def ingest(
        self,
        body: bytes,
        started_at: int,
        ended_at: int,
        extension: str = ".mp4",
        expected_sha256: str | None = None,
        motion_score: float | None = None,
        motion_detected: bool | None = None,
    ) -> tuple[str, bool]:
        if not body:
            raise ValueError("segment is empty")
        if ended_at <= started_at:
            raise ValueError("segment end must be after start")
        if extension not in {".mp4", ".m4s"}:
            raise ValueError("unsupported segment extension")
        if motion_score is not None and not 0.0 <= motion_score <= 1.0:
            raise ValueError("motion score must be between 0 and 1")
        if motion_detected is not None and motion_score is None:
            raise ValueError("motion detection requires a motion score")

        digest = hashlib.sha256(body).hexdigest()
        if expected_sha256 and not hmac.compare_digest(digest, expected_sha256.lower()):
            raise ValueError("segment SHA-256 does not match body")
        with self.database.connect() as connection:
            existing = connection.execute(
                """
                SELECT id FROM segments
                WHERE started_at = ? AND ended_at = ? AND sha256 = ?
                """,
                (started_at, ended_at, digest),
            ).fetchone()
        if existing is not None:
            return str(existing["id"]), False

        if self.bytes_used() + len(body) > self.max_bytes:
            raise ArchiveFullError("archive high-water limit reached")

        segment_id = str(uuid.uuid4())
        filename = f"{started_at}-{segment_id}{extension}"
        final_path = self.directory / filename
        temporary_path = self.directory / f".{filename}.partial"

        self.directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        with temporary_path.open("xb") as handle:
            handle.write(body)
            handle.flush()
            os.fsync(handle.fileno())
        temporary_path.chmod(0o600)
        temporary_path.replace(final_path)

        try:
            with self.database.connect() as connection:
                connection.execute(
                    """
                    INSERT INTO segments
                        (id, filename, started_at, ended_at, size_bytes, sha256, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        segment_id,
                        filename,
                        started_at,
                        ended_at,
                        len(body),
                        digest,
                        int(time.time()),
                    ),
                )
                if motion_score is not None:
                    connection.execute(
                        """
                        INSERT INTO segment_motion (segment_id, score, detected, analyzed_at)
                        VALUES (?, ?, ?, ?)
                        """,
                        (segment_id, motion_score, int(bool(motion_detected)), int(time.time())),
                    )
        except Exception:
            final_path.unlink(missing_ok=True)
            raise
        # A thumbnail is a convenience for the authenticated timeline, never a
        # second source of truth.  If a segment is partial or ffmpeg is not
        # available, keep the valid recording and let the UI show a fallback.
        self.create_thumbnail(segment_id)
        return segment_id, True

    def thumbnail_path(self, segment_id: str) -> Path | None:
        resolved = self.resolve(segment_id)
        if resolved is None:
            return None
        media_path, _ = resolved
        thumbnail = (self.directory / "thumbnails" / f"{media_path.stem}.jpg").resolve()
        thumbnail_directory = (self.directory / "thumbnails").resolve()
        if thumbnail.parent != thumbnail_directory:
            raise RuntimeError("thumbnail escaped archive directory")
        return thumbnail

    def create_thumbnail(self, segment_id: str) -> bool:
        resolved = self.resolve(segment_id)
        thumbnail = self.thumbnail_path(segment_id)
        if resolved is None or thumbnail is None:
            return False
        media_path, _ = resolved
        thumbnail.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        temporary = thumbnail.with_suffix(".partial.jpg")
        try:
            ffmpeg = shutil.which("ffmpeg")
            if ffmpeg is None:
                for candidate in (Path("/opt/homebrew/bin/ffmpeg"), Path("/usr/local/bin/ffmpeg")):
                    if candidate.is_file() and os.access(candidate, os.X_OK):
                        ffmpeg = str(candidate)
                        break
            if ffmpeg is None:
                return False
            subprocess.run(
                [
                    ffmpeg, "-nostdin", "-loglevel", "error", "-y", "-ss", "1",
                    "-i", str(media_path), "-frames:v", "1", "-vf", "scale=480:-2",
                    str(temporary),
                ],
                check=True,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=20,
            )
            temporary.chmod(0o600)
            temporary.replace(thumbnail)
            return True
        except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
            temporary.unlink(missing_ok=True)
            return False

    def list_segments(self, since: int, until: int) -> list[dict[str, int | float | str]]:
        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT segments.id, started_at, ended_at, size_bytes, sha256,
                       COALESCE(segment_motion.score, 0.0) AS motion_score,
                       COALESCE(segment_motion.detected, 0) AS motion_detected
                FROM segments
                LEFT JOIN segment_motion ON segment_motion.segment_id = segments.id
                WHERE ended_at >= ? AND started_at <= ?
                ORDER BY started_at DESC
                """,
                (since, until),
            ).fetchall()
        return [dict(row) for row in rows]

    def export_segments(self, since: int, until: int, max_bytes: int) -> list[tuple[Path, dict[str, int | str]]]:
        if since >= until:
            raise ValueError("export start must be before export end")
        selections: list[tuple[Path, dict[str, int | str]]] = []
        total = 0
        for metadata in reversed(self.list_segments(since, until)):
            resolved = self.resolve(str(metadata["id"]))
            if resolved is None or not resolved[0].is_file():
                continue
            path, resolved_metadata = resolved
            total += int(resolved_metadata["size_bytes"])
            if total > max_bytes:
                raise ArchiveFullError("requested export exceeds the configured size limit")
            selections.append((path, resolved_metadata))
        if not selections:
            raise FileNotFoundError("no recordings overlap that time range")
        return selections

    def resolve(self, segment_id: str) -> tuple[Path, dict[str, int | str]] | None:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM segments WHERE id = ?", (segment_id,)
            ).fetchone()
        if row is None:
            return None
        path = (self.directory / row["filename"]).resolve()
        if path.parent != self.directory:
            raise RuntimeError("indexed segment escaped archive directory")
        return path, dict(row)

    def delete(self, segment_id: str) -> bool:
        resolved = self.resolve(segment_id)
        if resolved is None:
            return False
        path, _ = resolved
        thumbnail = self.thumbnail_path(segment_id)
        path.unlink(missing_ok=True)
        if thumbnail is not None:
            thumbnail.unlink(missing_ok=True)
            try:
                thumbnail.parent.rmdir()
            except OSError:
                pass
        with self.database.connect() as connection:
            connection.execute("DELETE FROM segments WHERE id = ?", (segment_id,))
        return True

    def expire(self, older_than: int) -> list[str]:
        with self.database.connect() as connection:
            ids = [
                row["id"]
                for row in connection.execute(
                    "SELECT id FROM segments WHERE ended_at < ? ORDER BY ended_at", (older_than,)
                ).fetchall()
            ]
        for segment_id in ids:
            self.delete(segment_id)
        return ids
