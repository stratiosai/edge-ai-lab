import cv2
import numpy as np

from stratios_edge_ai.private_camera.overlay import render_overlay
from stratios_edge_ai.private_camera.tracking import Track


def test_overlay_draws_on_copy_and_counts_confirmed_objects() -> None:
    frame = np.zeros((80, 120, 3), dtype=np.uint8)
    original = frame.copy()
    tracks = [Track(1, "car", 0.88, (0.1, 0.2, 0.4, 0.7)), Track(2, "unknown", 0.3, (0.5, 0.2, 0.8, 0.7))]
    output = render_overlay(frame, tracks, active_zone="driveway")
    assert np.array_equal(frame, original)
    assert output.shape == frame.shape
    assert np.any(output != frame)
    assert cv2.imencode(".jpg", output)[0]
