"""Pi-side health reporting, segment upload, and bounded outage buffering."""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import shutil
import ssl
import subprocess
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

LOG = logging.getLogger("edge-camera-pi-agent")


@dataclass(frozen=True, slots=True)
class PiAgentConfig:
    buffer_dir: Path
    server_url: str
    ingest_token_file: Path
    ca_file: Path | None = None
    max_buffer_seconds: int = 3600
    max_buffer_bytes: int = 2 * 1024**3
    poll_seconds: int = 10
    # FFmpeg writes the active one-minute MP4 directly to its final filename.
    # Do not probe it until after the segment window plus a small finalization
    # margin, otherwise an in-progress file has no completed MP4 index yet.
    closed_file_age_seconds: int = 75
    motion_threshold: float = 0.035

    def token(self) -> str:
        token = self.ingest_token_file.read_text(encoding="utf-8").strip()
        if not token:
            raise RuntimeError("ingest token file is empty")
        return token


def segment_times(path: Path) -> tuple[int, int]:
    try:
        started_at = int(path.stem)
    except ValueError as exc:
        raise ValueError(f"segment name must be an epoch timestamp: {path.name}") from exc

    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=15,
    )
    duration = max(1, round(float(result.stdout.strip())))
    return started_at, started_at + duration


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def motion_score_from_frames(raw_frames: bytes, frame_size: int) -> float:
    """Return robust low-resolution grayscale frame change, normalized 0..1."""
    if frame_size <= 0 or len(raw_frames) < frame_size * 2:
        return 0.0
    frame_count = len(raw_frames) // frame_size
    frames = memoryview(raw_frames[: frame_count * frame_size])
    changes = [
        sum(abs(current - previous) for current, previous in zip(
            frames[offset : offset + frame_size], frames[offset - frame_size : offset]
        )) / (frame_size * 255)
        for offset in range(frame_size, frame_count * frame_size, frame_size)
    ]
    if not changes:
        return 0.0
    # A short movement should not be averaged away across an otherwise quiet minute.
    strongest = sorted(changes)[-min(3, len(changes)) :]
    return round(sum(strongest) / len(strongest), 5)


def motion_summary(path: Path, threshold: float) -> tuple[float, bool]:
    """Analyze a closed segment at 1 fps/64x36; never change the source media."""
    width, height = 64, 36
    result = subprocess.run(
        [
            "ffmpeg", "-nostdin", "-v", "error", "-i", str(path),
            "-vf", f"fps=1,scale={width}:{height},format=gray",
            "-f", "rawvideo", "-",
        ],
        check=True,
        capture_output=True,
        timeout=30,
    )
    score = motion_score_from_frames(result.stdout, width * height)
    return score, score >= threshold


def post_bytes(
    url: str,
    token: str,
    body: bytes,
    headers: dict[str, str],
    ca_file: Path | None = None,
) -> dict[str, object]:
    request = urllib.request.Request(
        url,
        data=body,
        headers={"X-Ingest-Token": token, **headers},
        method="POST",
    )
    context = ssl.create_default_context(cafile=str(ca_file)) if ca_file else None
    with urllib.request.urlopen(request, timeout=30, context=context) as response:
        return json.loads(response.read())


def upload_segment(config: PiAgentConfig, path: Path) -> bool:
    started_at, ended_at = segment_times(path)
    motion_score, motion_detected = motion_summary(path, config.motion_threshold)
    response = post_bytes(
        f"{config.server_url.rstrip('/')}/api/ingest/segment",
        config.token(),
        path.read_bytes(),
        {
            "Content-Type": "application/octet-stream",
            "X-Segment-Started-At": str(started_at),
            "X-Segment-Ended-At": str(ended_at),
            "X-Segment-Extension": path.suffix,
            "X-Segment-Sha256": sha256_file(path),
            "X-Segment-Motion-Score": str(motion_score),
            "X-Segment-Motion-Detected": str(motion_detected).lower(),
        },
        config.ca_file,
    )
    return response.get("status") == "ok"


def camera_health(config: PiAgentConfig) -> dict[str, object]:
    usage = shutil.disk_usage(config.buffer_dir)
    temperature = subprocess.run(
        ["vcgencmd", "measure_temp"], capture_output=True, text=True, check=False, timeout=5
    ).stdout.strip()
    throttled = subprocess.run(
        ["vcgencmd", "get_throttled"], capture_output=True, text=True, check=False, timeout=5
    ).stdout.strip()
    camera = subprocess.run(
        ["rpicam-hello", "--list-cameras"],
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    return {
        "camera": "ok" if "Available cameras" in camera.stdout else "unavailable",
        "temperature": temperature,
        "throttled": throttled,
        "buffer_free_bytes": usage.free,
        "buffer_total_bytes": usage.total,
        "reported_at": int(time.time()),
    }


def post_health(config: PiAgentConfig) -> None:
    body = json.dumps(camera_health(config), separators=(",", ":")).encode()
    post_bytes(
        f"{config.server_url.rstrip('/')}/api/ingest/health",
        config.token(),
        body,
        {"Content-Type": "application/json"},
        config.ca_file,
    )


def closed_segments(config: PiAgentConfig, now: float | None = None) -> list[Path]:
    now = now if now is not None else time.time()
    return sorted(
        (
            path
            for path in config.buffer_dir.glob("*.mp4")
            if path.is_file() and now - path.stat().st_mtime >= config.closed_file_age_seconds
        ),
        key=lambda path: path.stat().st_mtime,
    )


def prune_buffer(config: PiAgentConfig, now: float | None = None) -> list[Path]:
    now = now if now is not None else time.time()
    removed: list[Path] = []
    segments = sorted(
        (
            path
            for path in config.buffer_dir.glob("*")
            if path.is_file() and path.suffix in {".mp4", ".partial"}
        ),
        key=lambda path: path.stat().st_mtime,
    )

    for path in list(segments):
        if now - path.stat().st_mtime > config.max_buffer_seconds:
            path.unlink()
            removed.append(path)
            segments.remove(path)

    total = sum(path.stat().st_size for path in segments)
    for path in segments:
        if total <= config.max_buffer_bytes:
            break
        size = path.stat().st_size
        path.unlink()
        removed.append(path)
        total -= size
    return removed


def run_once(config: PiAgentConfig) -> None:
    config.buffer_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    for path in prune_buffer(config):
        LOG.warning("removed expired buffer segment: %s", path.name)
    try:
        post_health(config)
    except (OSError, ValueError, urllib.error.URLError) as exc:
        LOG.warning("health upload failed: %s", exc)

    for path in closed_segments(config):
        try:
            if upload_segment(config, path):
                path.unlink()
                LOG.info("archived and removed local segment: %s", path.name)
        except (ValueError, subprocess.SubprocessError) as exc:
            partial_path = path.with_suffix(".partial")
            if not partial_path.exists():
                path.replace(partial_path)
                LOG.warning("preserved invalid segment for bounded cleanup: %s (%s)", path.name, exc)
            else:
                LOG.warning("invalid segment remains deferred: %s (%s)", path.name, exc)
            continue
        except (OSError, urllib.error.URLError) as exc:
            LOG.warning("segment upload deferred for %s: %s", path.name, exc)
            break


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--buffer-dir", type=Path, default=Path.home() / "edge-camera-buffer")
    parser.add_argument("--server-url", required=True)
    parser.add_argument(
        "--ingest-token-file", type=Path, default=Path("/etc/edge-camera/ingest-token")
    )
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--ca-file", type=Path)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    config = PiAgentConfig(args.buffer_dir, args.server_url, args.ingest_token_file, args.ca_file)
    if args.once:
        run_once(config)
        return
    while True:
        run_once(config)
        time.sleep(config.poll_seconds)


if __name__ == "__main__":
    main()
