"""Archive ingestion, indexing, retention, deletion, and storage safeguards."""

from __future__ import annotations

import hashlib
import hmac
import os
import time
import uuid
from pathlib import Path

from .database import Database


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

    def ingest(
        self,
        body: bytes,
        started_at: int,
        ended_at: int,
        extension: str = ".mp4",
        expected_sha256: str | None = None,
    ) -> tuple[str, bool]:
        if not body:
            raise ValueError("segment is empty")
        if ended_at <= started_at:
            raise ValueError("segment end must be after start")
        if extension not in {".mp4", ".m4s"}:
            raise ValueError("unsupported segment extension")

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
        except Exception:
            final_path.unlink(missing_ok=True)
            raise
        return segment_id, True

    def list_segments(self, since: int, until: int) -> list[dict[str, int | str]]:
        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT id, started_at, ended_at, size_bytes, sha256
                FROM segments
                WHERE ended_at >= ? AND started_at <= ?
                ORDER BY started_at DESC
                """,
                (since, until),
            ).fetchall()
        return [dict(row) for row in rows]

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
        path.unlink(missing_ok=True)
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
