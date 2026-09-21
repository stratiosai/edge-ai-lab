"""Optional Pi-side Phase 5 analysis for completed camera segments.

This module is deliberately called only after a segment has been archived and
only when the Pi agent's detector flag is explicitly enabled. It never writes
over the source MP4 and emits review events, not notifications or actuations.
"""

from __future__ import annotations

import json
import logging
import urllib.error
from pathlib import Path

from .events import EventSuggestion

LOG = logging.getLogger("edge-camera-pi-detector")


def analyze_segment(
    segment: Path,
    model: Path,
    *,
    started_at: int,
    segment_id: str,
    sample_fps: float = 2.0,
    confidence: float = 0.45,
) -> list[EventSuggestion]:
    """Replay one closed MP4 and attach its archive ID to new-track events."""

    if sample_fps <= 0:
        raise ValueError("sample FPS must be positive")
    # Keep the heavyweight CV imports out of the normal health/archive path.
    import cv2

    from .detector import DetectorConfig, OnnxDetector
    from .motion import MotionGate, MotionZone
    from .pipeline import DetectionPipeline
    from .tracking import IoUTracker

    capture = cv2.VideoCapture(str(segment))
    if not capture.isOpened():
        raise ValueError(f"cannot open segment: {segment}")
    source_fps = capture.get(cv2.CAP_PROP_FPS) or 15.0
    stride = max(1, round(source_fps / sample_fps))
    zone = MotionZone("controlled-test-area", 0.0, 0.0, 1.0, 1.0)
    detector = OnnxDetector(model, DetectorConfig(confidence_threshold=confidence))
    pipeline = DetectionPipeline(
        detector.detect,
        [zone],
        motion_gate=MotionGate([zone], threshold=5.0),
        tracker=IoUTracker(min_hits=2),
    )
    events: list[EventSuggestion] = []
    frame_index = 0
    try:
        while True:
            ok, frame = capture.read()
            if not ok:
                break
            if frame_index % stride == 0:
                occurred_at = started_at + round(frame_index / source_fps)
                result = pipeline.process(
                    frame,
                    occurred_at=occurred_at,
                    segment_id=segment_id,
                )
                events.extend(result.events)
            frame_index += 1
    finally:
        capture.release()
    return events


def post_events(config, events: list[EventSuggestion]) -> int:
    """Submit events with the agent's existing token/TLS transport."""

    from .pi_agent import post_bytes

    posted = 0
    for event in events:
        body = json.dumps(event.__dict__, separators=(",", ":")).encode()
        try:
            response = post_bytes(
                f"{config.server_url.rstrip('/')}/api/ingest/event",
                config.token(),
                body,
                {"Content-Type": "application/json"},
                config.ca_file,
            )
        except (OSError, ValueError, urllib.error.URLError) as exc:
            LOG.warning("event upload failed for %s: %s", event.event_id, exc)
            continue
        if response.get("status") == "ok":
            posted += 1
    return posted
