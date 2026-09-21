"""Small, deterministic motion-zone gate for Phase 5 inference."""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np


@dataclass(frozen=True)
class MotionZone:
    name: str
    left: float
    top: float
    right: float
    bottom: float
    enabled: bool = True

    def __post_init__(self) -> None:
        values = (self.left, self.top, self.right, self.bottom)
        if any(not 0.0 <= value <= 1.0 for value in values):
            raise ValueError("motion-zone coordinates must be between 0 and 1")
        if self.left >= self.right or self.top >= self.bottom:
            raise ValueError("motion-zone bounds must have positive area")

    def crop(self, frame: np.ndarray) -> np.ndarray:
        height, width = frame.shape[:2]
        left, right = int(self.left * width), max(int(self.right * width), 1)
        top, bottom = int(self.top * height), max(int(self.bottom * height), 1)
        return frame[top:bottom, left:right]

    def contains_center(self, box: tuple[float, float, float, float]) -> bool:
        left, top, right, bottom = box
        x = (left + right) / 2
        y = (top + bottom) / 2
        return self.left <= x <= self.right and self.top <= y <= self.bottom


class MotionGate:
    """Compare consecutive frames and report activity inside enabled zones."""

    def __init__(self, zones: list[MotionZone], threshold: float = 12.0) -> None:
        if threshold < 0:
            raise ValueError("motion threshold cannot be negative")
        self.zones = zones
        self.threshold = threshold
        self._previous: dict[str, np.ndarray] = {}

    def score(self, frame: np.ndarray) -> dict[str, float]:
        scores: dict[str, float] = {}
        for zone in self.zones:
            if not zone.enabled:
                continue
            gray = cv2.cvtColor(zone.crop(frame), cv2.COLOR_BGR2GRAY)
            previous = self._previous.get(zone.name)
            scores[zone.name] = 0.0 if previous is None else float(cv2.absdiff(gray, previous).mean())
            self._previous[zone.name] = gray
        return scores

    def active(self, frame: np.ndarray) -> bool:
        return any(value >= self.threshold for value in self.score(frame).values())

