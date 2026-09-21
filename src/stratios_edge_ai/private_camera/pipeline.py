"""Deterministic Phase 5 motion-gated detector pipeline."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass

import numpy as np

from .crossing import CrossingDetector
from .events import EventSuggestion
from .motion import MotionGate, MotionZone
from .tracking import Detection, IoUTracker, Track


@dataclass(frozen=True)
class PipelineResult:
    tracks: list[Track]
    events: list[EventSuggestion]
    motion_active: bool


class DetectionPipeline:
    """Compose motion, detection, tracking, and event metadata without I/O."""

    def __init__(
        self,
        detect: Callable[[np.ndarray, list[MotionZone]], list[Detection]],
        zones: list[MotionZone],
        *,
        motion_gate: MotionGate | None = None,
        tracker: IoUTracker | None = None,
        crossing: CrossingDetector | None = None,
        event_id_factory: Callable[[], str] | None = None,
    ) -> None:
        self.detect = detect
        self.zones = zones
        self.motion_gate = motion_gate or MotionGate(zones)
        self.tracker = tracker or IoUTracker()
        self.crossing = crossing
        self.event_id_factory = event_id_factory or (lambda: str(uuid.uuid4()))

    def process(
        self,
        frame: np.ndarray,
        *,
        occurred_at: int,
        segment_id: str | None = None,
    ) -> PipelineResult:
        active = self.motion_gate.active(frame)
        if not active:
            tracks, _ = self.tracker.update([])
            return PipelineResult(tracks, [], False)
        previous_track_ids = set(self.tracker.tracks)
        detections = self.detect(frame, self.zones)
        tracks, new_tracks = self.tracker.update(detections)
        if self.crossing:
            for expired_id in previous_track_ids - {track.track_id for track in tracks}:
                self.crossing.forget(expired_id)
        events: list[EventSuggestion] = []
        zone = next((item.name for item in self.zones if item.enabled), "unknown")
        crossing_directions: dict[int, str] = {}
        if self.crossing:
            for track in tracks:
                center = ((track.box[0] + track.box[2]) / 2, (track.box[1] + track.box[3]) / 2)
                crossing_event = self.crossing.update(track.track_id, track.label, center)
                if crossing_event:
                    crossing_directions[track.track_id] = crossing_event.direction
        event_tracks = list(new_tracks)
        event_tracks.extend(
            track for track in tracks
            if track.track_id in crossing_directions and track not in event_tracks
        )
        for track in event_tracks:
            direction = crossing_directions.get(track.track_id)
            count = sum(item.label == track.label for item in tracks)
            events.append(
                EventSuggestion(
                    event_id=self.event_id_factory(),
                    occurred_at=occurred_at,
                    track_id=track.track_id,
                    label=track.label,
                    confidence=track.score,
                    zone=zone,
                    count=count,
                    direction=direction,
                    segment_id=segment_id,
                )
            )
        return PipelineResult(tracks, events, True)
