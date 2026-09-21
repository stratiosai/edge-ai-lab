"""Optional non-destructive detector overlay for the Pi live MJPEG stream."""

from __future__ import annotations

import logging
import time
from pathlib import Path

import cv2
import numpy as np

from .detector import DetectorConfig, OnnxDetector
from .motion import MotionGate, MotionZone
from .overlay import render_overlay
from .pipeline import DetectionPipeline
from .tracking import IoUTracker, Track

LOG = logging.getLogger("edge-camera-pi-overlay")


class LiveOverlay:
    """Transform JPEG frames with sampled detector boxes and stable track IDs."""

    def __init__(
        self,
        model: Path,
        *,
        sample_fps: float = 2.0,
        confidence: float = 0.45,
        motion_threshold: float = 5.0,
    ) -> None:
        if sample_fps <= 0:
            raise ValueError("overlay sample FPS must be positive")
        self.sample_interval = 1.0 / sample_fps
        self.last_inference = 0.0
        self.last_tracks: list[Track] = []
        zone = MotionZone("controlled-test-area", 0.0, 0.0, 1.0, 1.0)
        detector = OnnxDetector(model, DetectorConfig(confidence_threshold=confidence))
        self.pipeline = DetectionPipeline(
            detector.detect,
            [zone],
            motion_gate=MotionGate([zone], threshold=motion_threshold),
            tracker=IoUTracker(min_hits=2),
        )

    def __call__(self, jpeg: bytes) -> bytes:
        array = np.frombuffer(jpeg, dtype=np.uint8)
        frame = cv2.imdecode(array, cv2.IMREAD_COLOR)
        if frame is None:
            return jpeg
        now = time.monotonic()
        if now - self.last_inference >= self.sample_interval:
            result = self.pipeline.process(frame, occurred_at=int(time.time()))
            self.last_tracks = result.tracks
            self.last_inference = now
        rendered = render_overlay(frame, self.last_tracks)
        ok, encoded = cv2.imencode(".jpg", rendered, [cv2.IMWRITE_JPEG_QUALITY, 80])
        return encoded.tobytes() if ok else jpeg
