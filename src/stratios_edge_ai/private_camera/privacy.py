"""Opt-in privacy masks for future shared-space or outdoor camera views."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass(frozen=True)
class PrivacyMask:
    """A normalized rectangle that is blacked out on a derived frame."""

    name: str
    left: float
    top: float
    right: float
    bottom: float
    enabled: bool = True

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("privacy-mask name is required")
        values = (self.left, self.top, self.right, self.bottom)
        if any(not 0.0 <= value <= 1.0 for value in values):
            raise ValueError("privacy-mask coordinates must be between 0 and 1")
        if self.left >= self.right or self.top >= self.bottom:
            raise ValueError("privacy-mask bounds must have positive area")


def apply_privacy_masks(frame: np.ndarray, masks: list[PrivacyMask]) -> np.ndarray:
    """Return a masked copy; never mutate the source/evidence frame."""

    if frame.ndim < 2:
        raise ValueError("frame must be at least two-dimensional")
    output = frame.copy()
    height, width = frame.shape[:2]
    for mask in masks:
        if not mask.enabled:
            continue
        left = max(0, min(width, round(mask.left * width)))
        top = max(0, min(height, round(mask.top * height)))
        right = max(left, min(width, round(mask.right * width)))
        bottom = max(top, min(height, round(mask.bottom * height)))
        output[top:bottom, left:right] = 0
    return output


def load_privacy_masks(path: Path) -> list[PrivacyMask]:
    """Load a JSON array of normalized masks from an owner-controlled file."""

    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise TypeError("privacy-mask file must contain a JSON array")
    return [PrivacyMask(**item) for item in payload]
