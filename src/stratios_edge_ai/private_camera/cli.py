"""Command-line entry points for the private camera service."""

from __future__ import annotations

import argparse
import getpass

import uvicorn

from .admin import set_admin
from .app import create_app
from .config import CameraServerConfig
from .database import Database


def serve() -> None:
    config = CameraServerConfig.from_env()
    if bool(config.tls_cert_file) != bool(config.tls_key_file):
        raise SystemExit("set both EDGE_CAMERA_TLS_CERT_FILE and EDGE_CAMERA_TLS_KEY_FILE")
    uvicorn.run(
        create_app(config),
        host=config.bind_host,
        port=config.bind_port,
        ssl_certfile=str(config.tls_cert_file) if config.tls_cert_file else None,
        ssl_keyfile=str(config.tls_key_file) if config.tls_key_file else None,
    )


def admin() -> None:
    parser = argparse.ArgumentParser(description="Create or reset the local camera administrator")
    parser.add_argument("username")
    args = parser.parse_args()
    password = getpass.getpass("New password (12+ characters): ")
    confirmation = getpass.getpass("Confirm password: ")
    if password != confirmation:
        raise SystemExit("passwords do not match")
    config = CameraServerConfig.from_env()
    config.prepare()
    database = Database(config.database_path)
    database.initialize()
    set_admin(database, args.username, password)
    print("Administrator updated; existing sessions for this account were revoked.")
