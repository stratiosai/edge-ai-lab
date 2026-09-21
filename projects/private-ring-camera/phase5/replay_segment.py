"""Replay one archived MP4 through the Phase 5 pipeline.

This is intentionally offline: it reads a chosen segment, writes JSON to a
private output path, and never changes the recording or sends notifications.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import cv2

from stratios_edge_ai.private_camera.detector import DetectorConfig, OnnxDetector
from stratios_edge_ai.private_camera.motion import MotionGate, MotionZone
from stratios_edge_ai.private_camera.pipeline import DetectionPipeline
from stratios_edge_ai.private_camera.tracking import IoUTracker


def replay(
    segment: Path,
    model: Path,
    output: Path,
    *,
    started_at: int,
    sample_fps: float = 2.0,
    confidence: float = 0.45,
) -> dict[str, object]:
    if sample_fps <= 0:
        raise ValueError("sample FPS must be positive")
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
    frame_index = 0
    event_records: list[dict[str, object]] = []
    try:
        while True:
            ok, frame = capture.read()
            if not ok:
                break
            if frame_index % stride == 0:
                timestamp = started_at + round(frame_index / source_fps)
                result = pipeline.process(frame, occurred_at=timestamp)
                event_records.extend(event.__dict__ for event in result.events)
            frame_index += 1
    finally:
        capture.release()
    payload = {
        "segment": str(segment),
        "model": str(model),
        "started_at": started_at,
        "sample_fps": sample_fps,
        "frames_read": frame_index,
        "events": event_records,
        "generated_at": int(time.time()),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("segment", type=Path)
    parser.add_argument("model", type=Path)
    parser.add_argument("--started-at", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--sample-fps", type=float, default=2.0)
    parser.add_argument("--confidence", type=float, default=0.45)
    args = parser.parse_args()
    print(json.dumps(replay(**vars(args)), indent=2, default=str))


if __name__ == "__main__":
    main()
