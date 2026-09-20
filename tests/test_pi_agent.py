from __future__ import annotations

import os
import time
from pathlib import Path

from stratios_edge_ai.private_camera import pi_agent
from stratios_edge_ai.private_camera.pi_agent import PiAgentConfig, closed_segments, prune_buffer


def config(tmp_path: Path, *, max_seconds: int = 3600, max_bytes: int = 100) -> PiAgentConfig:
    token = tmp_path / "token"
    token.write_text("test-token", encoding="utf-8")
    return PiAgentConfig(
        buffer_dir=tmp_path / "buffer",
        server_url="https://camera.invalid",
        ingest_token_file=token,
        max_buffer_seconds=max_seconds,
        max_buffer_bytes=max_bytes,
        closed_file_age_seconds=5,
    )


def segment(directory: Path, name: str, size: int, mtime: float) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / name
    path.write_bytes(b"x" * size)
    os.utime(path, (mtime, mtime))
    return path


def test_closed_segments_excludes_recent_and_non_mp4_files(tmp_path: Path) -> None:
    cfg = config(tmp_path)
    old = segment(cfg.buffer_dir, "100.mp4", 10, 100)
    segment(cfg.buffer_dir, "101.partial", 10, 100)
    segment(cfg.buffer_dir, "102.mp4", 10, 198)
    assert closed_segments(cfg, now=200) == [old]


def test_prune_buffer_enforces_age_then_size_oldest_first(tmp_path: Path) -> None:
    cfg = config(tmp_path, max_seconds=300, max_bytes=20)
    expired = segment(cfg.buffer_dir, "0.mp4", 10, 0)
    oldest = segment(cfg.buffer_dir, "200.mp4", 15, 200)
    newest = segment(cfg.buffer_dir, "300.mp4", 15, 300)

    removed = prune_buffer(cfg, now=350)
    assert removed == [expired, oldest]
    assert not expired.exists()
    assert not oldest.exists()
    assert newest.exists()


def test_partial_or_invalid_segment_stays_buffered_for_retry(tmp_path: Path, monkeypatch) -> None:
    cfg = config(tmp_path)
    partial = segment(cfg.buffer_dir, "500.mp4", 10, time.time() - 10)
    monkeypatch.setattr(pi_agent, "post_health", lambda _: None)
    monkeypatch.setattr(pi_agent, "upload_segment", lambda *_: (_ for _ in ()).throw(ValueError("N/A")))
    pi_agent.run_once(cfg)
    assert partial.exists()
