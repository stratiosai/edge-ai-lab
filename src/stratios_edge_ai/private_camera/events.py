"""Pure event-suggestion records shared by the detector and authenticated UI."""

from __future__ import annotations

from dataclasses import dataclass

from .tracking import Box


@dataclass(frozen=True)
class EventSuggestion:
    """A reviewable event; it does not trigger notifications or actuators."""

    event_id: str
    occurred_at: int
    track_id: int
    label: str
    confidence: float
    zone: str
    count: int
    direction: str | None = None
    segment_id: str | None = None
    thumbnail_path: str | None = None
    clip_start: int | None = None
    clip_end: int | None = None

    def __post_init__(self) -> None:
        if not self.event_id or not self.label or not self.zone:
            raise ValueError("event id, label, and zone are required")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")
        if self.count < 1:
            raise ValueError("count must be positive")
        if (
            self.clip_start is not None
            and self.clip_end is not None
            and self.clip_end <= self.clip_start
        ):
            raise ValueError("clip end must be after clip start")


def clip_window(occurred_at: int, *, before: int = 5, after: int = 10) -> tuple[int, int]:
    """Return a bounded review window around an event timestamp."""

    if before < 0 or after < 0:
        raise ValueError("clip window values must be non-negative")
    return occurred_at - before, occurred_at + after


def thumbnail_box(box: Box, *, width: int, height: int) -> tuple[int, int, int, int]:
    """Convert a normalized detector box to a clamped pixel crop rectangle."""

    if width < 1 or height < 1:
        raise ValueError("thumbnail dimensions must be positive")
    x1, y1, x2, y2 = box
    left = max(0, min(width, round(x1 * width)))
    top = max(0, min(height, round(y1 * height)))
    right = max(left, min(width, round(x2 * width)))
    bottom = max(top, min(height, round(y2 * height)))
    return left, top, right, bottom
