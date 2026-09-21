"""Non-destructive live overlay rendering for detector boxes and counts."""

from __future__ import annotations

from collections import Counter

import cv2
import numpy as np

from .tracking import Track


def render_overlay(frame: np.ndarray, tracks: list[Track], *, active_zone: str | None = None) -> np.ndarray:
    """Return an annotated copy of ``frame``; never mutate archived input."""

    if frame.ndim != 3 or frame.shape[2] != 3:
        raise ValueError("overlay frame must be a BGR image")
    output = frame.copy()
    height, width = output.shape[:2]
    counts = Counter(track.label for track in tracks if track.label != "unknown")
    summary = "  ".join(f"{label}: {count}" for label, count in sorted(counts.items())) or "No confirmed objects"
    cv2.rectangle(output, (0, 0), (width, 34), (8, 32, 45), thickness=-1)
    cv2.putText(output, summary, (10, 23), cv2.FONT_HERSHEY_SIMPLEX, 0.62, (235, 248, 255), 1, cv2.LINE_AA)
    for track in tracks:
        left, top, right, bottom = track.box
        x1, y1 = round(max(0, min(1, left)) * width), round(max(0, min(1, top)) * height)
        x2, y2 = round(max(0, min(1, right)) * width), round(max(0, min(1, bottom)) * height)
        color = (30, 200, 255) if track.label != "unknown" else (160, 160, 160)
        cv2.rectangle(output, (x1, y1), (x2, y2), color, 2)
        label = f"{track.label} {track.score:.2f} #{track.track_id}"
        cv2.putText(output, label, (x1, max(52, y1 - 7)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1, cv2.LINE_AA)
    if active_zone:
        cv2.putText(output, f"zone: {active_zone}", (10, height - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (180, 235, 255), 1, cv2.LINE_AA)
    return output
