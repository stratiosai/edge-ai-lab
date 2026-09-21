import numpy as np
import pytest

from stratios_edge_ai.private_camera.motion import MotionGate, MotionZone


def test_motion_zone_scores_only_after_a_baseline() -> None:
    zone = MotionZone("center", 0.25, 0.25, 0.75, 0.75)
    gate = MotionGate([zone], threshold=5)
    still = np.zeros((100, 100, 3), dtype=np.uint8)
    changed = still.copy()
    changed[40:60, 40:60] = 255

    assert gate.active(still) is False
    assert gate.active(changed) is True
    assert gate.active(still) is True


def test_motion_zone_disabled_and_invalid_bounds() -> None:
    assert MotionGate([MotionZone("off", 0, 0, 1, 1, enabled=False)]).active(
        np.zeros((8, 8, 3), dtype=np.uint8)
    ) is False
    with pytest.raises(ValueError):
        MotionZone("bad", 0.8, 0, 0.2, 1)
    with pytest.raises(ValueError):
        MotionGate([], threshold=-1)


def test_zone_contains_detection_center() -> None:
    zone = MotionZone("left", 0, 0, 0.5, 1)
    assert zone.contains_center((0.1, 0.1, 0.3, 0.9))
    assert not zone.contains_center((0.6, 0.1, 0.9, 0.9))

