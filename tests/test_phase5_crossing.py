import pytest

from stratios_edge_ai.private_camera.crossing import CrossingDetector, CrossingLine


def test_crossing_line_emits_direction_once() -> None:
    detector = CrossingDetector(CrossingLine((0.5, 0.0), (0.5, 1.0)))
    assert detector.update(7, "car", (0.25, 0.5)) is None
    event = detector.update(7, "car", (0.75, 0.5))
    assert event is not None
    assert (event.track_id, event.label, event.direction) == (7, "car", "a-to-b")
    assert detector.update(7, "car", (0.9, 0.5)) is None


def test_deadband_avoids_jitter_and_forget_allows_reentry() -> None:
    detector = CrossingDetector(CrossingLine((0.5, 0.0), (0.5, 1.0)), deadband=0.1)
    detector.update(1, "person", (0.45, 0.5))
    assert detector.update(1, "person", (0.55, 0.5)) is None
    assert detector.update(1, "person", (0.7, 0.5)) is not None
    detector.forget(1)
    assert detector.update(1, "person", (0.2, 0.5)) is None
    assert detector.update(1, "person", (0.8, 0.5)) is not None


def test_degenerate_line_is_rejected() -> None:
    with pytest.raises(ValueError):
        CrossingLine((0.5, 0.5), (0.5, 0.5))
