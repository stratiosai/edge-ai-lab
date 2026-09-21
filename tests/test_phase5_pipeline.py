import numpy as np

from stratios_edge_ai.private_camera.crossing import CrossingDetector, CrossingLine
from stratios_edge_ai.private_camera.motion import MotionGate, MotionZone
from stratios_edge_ai.private_camera.pipeline import DetectionPipeline
from stratios_edge_ai.private_camera.tracking import Detection, IoUTracker


def test_pipeline_gates_inference_and_emits_confirmed_event() -> None:
    calls = []

    def detect(frame, zones):
        calls.append((frame.shape, [zone.name for zone in zones]))
        return [Detection("car", 0.9, (0.1, 0.1, 0.3, 0.3))]

    zone = MotionZone("driveway", 0, 0, 1, 1)
    pipeline = DetectionPipeline(
        detect,
        [zone],
        motion_gate=MotionGate([zone], threshold=0),
        tracker=IoUTracker(min_hits=1),
        event_id_factory=iter(["evt-1"]).__next__,
    )
    result = pipeline.process(np.zeros((20, 20, 3), dtype=np.uint8), occurred_at=100, segment_id="seg-1")
    assert calls == [((20, 20, 3), ["driveway"])]
    assert len(result.events) == 1
    assert result.events[0].segment_id == "seg-1"


def test_pipeline_does_not_infer_when_motion_is_quiet() -> None:
    called = False

    def detect(frame, zones):
        nonlocal called
        called = True
        return []

    zone = MotionZone("yard", 0, 0, 1, 1)
    pipeline = DetectionPipeline(detect, [zone], motion_gate=MotionGate([zone], threshold=1))
    result = pipeline.process(np.zeros((20, 20, 3), dtype=np.uint8), occurred_at=100)
    assert result.motion_active is False
    assert result.events == []
    assert called is False


def test_pipeline_emits_direction_when_confirmed_track_crosses_line() -> None:
    detections = iter(
        [
            [Detection("car", 0.9, (0.2, 0.4, 0.4, 0.6))],
            [Detection("car", 0.9, (0.3, 0.4, 0.5, 0.6))],
            [Detection("car", 0.9, (0.4, 0.4, 0.6, 0.6))],
            [Detection("car", 0.9, (0.5, 0.4, 0.7, 0.6))],
        ]
    )
    zone = MotionZone("driveway", 0, 0, 1, 1)
    pipeline = DetectionPipeline(
        lambda frame, zones: next(detections),
        [zone],
        motion_gate=MotionGate([zone], threshold=0),
        tracker=IoUTracker(iou_threshold=0.1, min_hits=1),
        crossing=CrossingDetector(CrossingLine((0.5, 0.0), (0.5, 1.0))),
    )

    pipeline.process(np.zeros((20, 20, 3), dtype=np.uint8), occurred_at=100)
    pipeline.process(np.zeros((20, 20, 3), dtype=np.uint8), occurred_at=101)
    pipeline.process(np.zeros((20, 20, 3), dtype=np.uint8), occurred_at=102)
    result = pipeline.process(np.zeros((20, 20, 3), dtype=np.uint8), occurred_at=103)

    assert len(result.events) == 1
    assert result.events[0].direction == "a-to-b"
