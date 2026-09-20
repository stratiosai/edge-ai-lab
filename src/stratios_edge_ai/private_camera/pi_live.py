"""Token-protected Pi MJPEG relay backed by the capture FIFO."""

from __future__ import annotations

import argparse
import hmac
import logging
import os
import select
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

LOG = logging.getLogger("edge-camera-pi-live")
BOUNDARY = b"edge-camera-frame"


class LatestJpeg:
    """Read JPEGs from a FIFO without letting disconnected viewers block capture."""

    def __init__(self, fifo: Path) -> None:
        self.fifo = fifo
        self.frame: bytes | None = None
        self.condition = threading.Condition()

    def run(self) -> None:
        fd = os.open(self.fifo, os.O_RDWR | os.O_NONBLOCK)
        pending = bytearray()
        try:
            while True:
                ready, _, _ = select.select([fd], [], [], 1)
                if not ready:
                    continue
                chunk = os.read(fd, 1024 * 1024)
                if not chunk:
                    continue
                pending.extend(chunk)
                while True:
                    start = pending.find(b"\xff\xd8")
                    end = pending.find(b"\xff\xd9", start + 2)
                    if start < 0 or end < 0:
                        if len(pending) > 8 * 1024 * 1024:
                            del pending[:-1024]
                        break
                    image = bytes(pending[start : end + 2])
                    del pending[: end + 2]
                    with self.condition:
                        self.frame = image
                        self.condition.notify_all()
        finally:
            os.close(fd)


def authorized(handler: BaseHTTPRequestHandler, token: str) -> bool:
    supplied = handler.headers.get("X-Live-Token", "")
    return bool(supplied) and hmac.compare_digest(supplied, token)


def make_handler(frames: LatestJpeg, token: str):
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, format: str, *args: object) -> None:
            LOG.info("%s - %s", self.address_string(), format % args)

        def do_GET(self) -> None:
            if not authorized(self, token):
                self.send_error(HTTPStatus.UNAUTHORIZED)
                return
            if self.path == "/health":
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", "15")
                self.end_headers()
                self.wfile.write(b'{"status":"ok"}')
                return
            if self.path != "/live.mjpg":
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=edge-camera-frame")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            seen: bytes | None = None
            try:
                while True:
                    with frames.condition:
                        frames.condition.wait_for(
                            lambda seen=seen: frames.frame is not None and frames.frame != seen,
                            timeout=10,
                        )
                        image = frames.frame
                    if image is None or image == seen:
                        continue
                    seen = image
                    self.wfile.write(b"--" + BOUNDARY + b"\r\n")
                    self.wfile.write(b"Content-Type: image/jpeg\r\n")
                    self.wfile.write(f"Content-Length: {len(image)}\r\n\r\n".encode())
                    self.wfile.write(image + b"\r\n")
                    self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                return

    return Handler


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fifo", type=Path, required=True)
    parser.add_argument("--token-file", type=Path, required=True)
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8090)
    args = parser.parse_args()
    token = args.token_file.read_text(encoding="utf-8").strip()
    if not token:
        raise RuntimeError("live token file is empty")
    if not args.fifo.is_fifo():
        raise RuntimeError(f"live FIFO is missing: {args.fifo}")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    frames = LatestJpeg(args.fifo)
    threading.Thread(target=frames.run, name="jpeg-reader", daemon=True).start()
    server = ThreadingHTTPServer((args.host, args.port), make_handler(frames, token))
    LOG.info("serving token-protected live MJPEG on %s:%s", args.host, args.port)
    server.serve_forever()


if __name__ == "__main__":
    main()
