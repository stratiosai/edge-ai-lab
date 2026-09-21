"""Render a short, derived Phase 5 proof video from a private MP4 segment."""

from __future__ import annotations

import argparse
from pathlib import Path

import cv2

from stratios_edge_ai.private_camera.detector import DetectorConfig, OnnxDetector
from stratios_edge_ai.private_camera.overlay import render_overlay
from stratios_edge_ai.private_camera.tracking import IoUTracker


def render(segment: Path, model: Path, output: Path, *, start: float, duration: float) -> int:
    capture = cv2.VideoCapture(str(segment))
    if not capture.isOpened():
        raise ValueError(f"cannot open segment: {segment}")
    fps = capture.get(cv2.CAP_PROP_FPS) or 15.0
    width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
    capture.set(cv2.CAP_PROP_POS_MSEC, start * 1000)
    output.parent.mkdir(parents=True, exist_ok=True)
    writer = cv2.VideoWriter(str(output), cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height))
    detector = OnnxDetector(model, DetectorConfig(confidence_threshold=0.30))
    tracker = IoUTracker(min_hits=1, max_age_frames=8)
    limit = max(1, round(duration * fps))
    frames = 0
    try:
        while frames < limit:
            ok, frame = capture.read()
            if not ok:
                break
            detections = detector.detect(frame)
            tracks, _ = tracker.update(detections)
            writer.write(render_overlay(frame, tracks, active_zone="controlled-test-area"))
            frames += 1
    finally:
        capture.release()
        writer.release()
    if frames == 0:
        raise ValueError("segment produced no frames")
    return frames


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("segment", type=Path)
    parser.add_argument("model", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--start", type=float, default=25.0)
    parser.add_argument("--duration", type=float, default=10.0)
    args = parser.parse_args()
    print(render(args.segment, args.model, args.output, start=args.start, duration=args.duration))


if __name__ == "__main__":
    main()
