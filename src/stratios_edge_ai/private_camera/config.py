"""Configuration for the private camera server."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

DEFAULT_DATA_DIR = Path.home() / "Library" / "Application Support" / "StratiosAI" / "edge-ai-camera"


@dataclass(frozen=True, slots=True)
class CameraServerConfig:
    data_dir: Path = DEFAULT_DATA_DIR
    retention_hours: int = 24
    session_days: int = 7
    secure_cookies: bool = True
    bind_host: str = "127.0.0.1"
    bind_port: int = 8443
    tls_cert_file: Path | None = None
    tls_key_file: Path | None = None
    pi_live_url: str | None = None
    pi_live_token: str | None = None
    pi_live_ca_file: Path | None = None
    ingest_token: str | None = None
    max_archive_bytes: int = 64 * 1024 * 1024 * 1024

    @property
    def archive_dir(self) -> Path:
        return self.data_dir / "archive"

    @property
    def database_path(self) -> Path:
        return self.data_dir / "camera.sqlite3"

    @classmethod
    def from_env(cls) -> CameraServerConfig:
        data_dir = Path(os.environ.get("EDGE_CAMERA_DATA_DIR", DEFAULT_DATA_DIR)).expanduser()
        return cls(
            data_dir=data_dir,
            retention_hours=int(os.environ.get("EDGE_CAMERA_RETENTION_HOURS", "24")),
            session_days=int(os.environ.get("EDGE_CAMERA_SESSION_DAYS", "7")),
            secure_cookies=os.environ.get("EDGE_CAMERA_SECURE_COOKIES", "true").lower()
            not in {"0", "false", "no"},
            bind_host=os.environ.get("EDGE_CAMERA_BIND_HOST", "127.0.0.1"),
            bind_port=int(os.environ.get("EDGE_CAMERA_BIND_PORT", "8443")),
            tls_cert_file=(
                Path(os.environ["EDGE_CAMERA_TLS_CERT_FILE"]).expanduser()
                if os.environ.get("EDGE_CAMERA_TLS_CERT_FILE")
                else None
            ),
            tls_key_file=(
                Path(os.environ["EDGE_CAMERA_TLS_KEY_FILE"]).expanduser()
                if os.environ.get("EDGE_CAMERA_TLS_KEY_FILE")
                else None
            ),
            pi_live_url=os.environ.get("EDGE_CAMERA_PI_LIVE_URL") or None,
            pi_live_token=os.environ.get("EDGE_CAMERA_PI_LIVE_TOKEN") or None,
            pi_live_ca_file=(
                Path(os.environ["EDGE_CAMERA_PI_LIVE_CA_FILE"]).expanduser()
                if os.environ.get("EDGE_CAMERA_PI_LIVE_CA_FILE")
                else None
            ),
            ingest_token=os.environ.get("EDGE_CAMERA_INGEST_TOKEN") or None,
            max_archive_bytes=int(
                os.environ.get("EDGE_CAMERA_MAX_ARCHIVE_BYTES", str(64 * 1024**3))
            ),
        )

    def prepare(self) -> None:
        self.archive_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        try:
            self.data_dir.chmod(0o700)
            self.archive_dir.chmod(0o700)
        except OSError:
            pass
