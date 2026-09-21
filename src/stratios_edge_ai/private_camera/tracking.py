"""Small class-aware IoU tracker for Phase 5 event suggestions."""

from __future__ import annotations

from dataclasses import dataclass

Box = tuple[float, float, float, float]


@dataclass(frozen=True)
class Detection:
    label: str
    score: float
    box: Box


@dataclass
class Track:
    track_id: int
    label: str
    score: float
    box: Box
    hits: int = 1
    age: int = 0
    counted: bool = False


def iou(left: Box, right: Box) -> float:
    x1 = max(left[0], right[0])
    y1 = max(left[1], right[1])
    x2 = min(left[2], right[2])
    y2 = min(left[3], right[3])
    intersection = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    left_area = max(0.0, left[2] - left[0]) * max(0.0, left[3] - left[1])
    right_area = max(0.0, right[2] - right[0]) * max(0.0, right[3] - right[1])
    union = left_area + right_area - intersection
    return intersection / union if union else 0.0


class IoUTracker:
    def __init__(self, *, iou_threshold: float = 0.3, max_age_frames: int = 15, min_hits: int = 2):
        if not 0.0 <= iou_threshold <= 1.0:
            raise ValueError("IoU threshold must be between 0 and 1")
        if max_age_frames < 0 or min_hits < 1:
            raise ValueError("max age must be non-negative and min hits must be positive")
        self.iou_threshold = iou_threshold
        self.max_age_frames = max_age_frames
        self.min_hits = min_hits
        self._next_id = 1
        self.tracks: dict[int, Track] = {}

    def update(self, detections: list[Detection]) -> tuple[list[Track], list[Track]]:
        unmatched = set(range(len(detections)))
        matched: set[int] = set()
        # Greedy highest-overlap matching is deterministic and sufficient for
        # the first single-camera, low-object-count milestone.
        candidates = sorted(
            (
                iou(track.box, detection.box),
                track_id,
                index,
            )
            for track_id, track in self.tracks.items()
            for index, detection in enumerate(detections)
            if track.label == detection.label
        )
        for overlap, track_id, index in reversed(candidates):
            if overlap < self.iou_threshold or track_id in matched or index not in unmatched:
                continue
            track = self.tracks[track_id]
            detection = detections[index]
            track.box, track.score, track.hits, track.age = detection.box, detection.score, track.hits + 1, 0
            matched.add(track_id)
            unmatched.remove(index)

        for track_id, track in list(self.tracks.items()):
            if track_id not in matched:
                track.age += 1
                if track.age > self.max_age_frames:
                    del self.tracks[track_id]

        for index in sorted(unmatched):
            detection = detections[index]
            self.tracks[self._next_id] = Track(
                self._next_id, detection.label, detection.score, detection.box
            )
            self._next_id += 1

        confirmed = [track for track in self.tracks.values() if track.hits >= self.min_hits]
        new_events = [track for track in confirmed if not track.counted]
        for track in new_events:
            track.counted = True
        return sorted(confirmed, key=lambda track: track.track_id), new_events

