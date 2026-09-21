import numpy as np
import pytest

from stratios_edge_ai.private_camera.detector import DetectorConfig, parse_nms_output
from stratios_edge_ai.private_camera.motion import MotionZone


def test_parse_nms_output_normalizes_and_filters_classes() -> None:
    rows = np.array(
        [[32, 64, 160, 256, 0.8, 2], [1, 1, 20, 20, 0.2, 0], [1, 1, 20, 20, 0.9, 99]],
        dtype=np.float32,
    )
    detections = parse_nms_output(rows, input_size=320, confidence_threshold=0.45)
    assert len(detections) == 1
    assert detections[0].label == "car"
    assert detections[0].box == (0.1, 0.2, 0.5, 0.8)


def test_detector_config_and_zone_validation() -> None:
    with pytest.raises(ValueError):
        DetectorConfig(input_size=300)
    zone = MotionZone("driveway", 0.0, 0.0, 0.5, 1.0)
    rows = np.array([[160, 100, 300, 300, 0.9, 2]], dtype=np.float32)
    detections = parse_nms_output(rows, input_size=320, confidence_threshold=0.45)
    assert zone.contains_center(detections[0].box) is False
