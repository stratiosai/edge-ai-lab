"""Deterministic crossing-line event logic for tracked camera objects."""

from __future__ import annotations

from dataclasses import dataclass

Point = tuple[float, float]


@dataclass(frozen=True)
class CrossingLine:
    """A directed line in normalized image coordinates.

    Direction is reported as ``a-to-b`` or ``b-to-a`` based on which side of
    the infinite line the tracked center occupied before and after crossing.
    """

    a: Point
    b: Point

    def __post_init__(self) -> None:
        if self.a == self.b:
            raise ValueError("crossing line endpoints must differ")

    def side(self, point: Point) -> float:
        return (self.b[0] - self.a[0]) * (point[1] - self.a[1]) - (
            self.b[1] - self.a[1]
        ) * (point[0] - self.a[0])


@dataclass(frozen=True)
class CrossingEvent:
    track_id: int
    label: str
    direction: str


class CrossingDetector:
    """Emit at most one crossing event per track per detector instance."""

    def __init__(self, line: CrossingLine, *, deadband: float = 0.0) -> None:
        if deadband < 0:
            raise ValueError("deadband must be non-negative")
        self.line = line
        self.deadband = deadband
        self._last_side: dict[int, float] = {}
        self._emitted: set[int] = set()

    def update(self, track_id: int, label: str, center: Point) -> CrossingEvent | None:
        side = self.line.side(center)
        previous = self._last_side.get(track_id)
        if previous is None or abs(side) > self.deadband:
            self._last_side[track_id] = side
        if track_id in self._emitted or previous is None:
            return None
        if abs(previous) <= self.deadband and abs(side) <= self.deadband:
            return None
        if previous * side >= 0:
            return None
        direction = "a-to-b" if previous > side else "b-to-a"
        self._emitted.add(track_id)
        return CrossingEvent(track_id, label, direction)

    def forget(self, track_id: int) -> None:
        """Drop state after a tracker expires, allowing a future re-entry."""

        self._last_side.pop(track_id, None)
        self._emitted.discard(track_id)
