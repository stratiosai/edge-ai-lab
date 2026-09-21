import pytest

from stratios_edge_ai.private_camera.metrics import (
    LabeledObject,
    aggregate_metrics,
    evaluate_frame,
)
from stratios_edge_ai.private_camera.tracking import Detection


def test_frame_metrics_match_same_class_and_count_duplicates() -> None:
    truth = [LabeledObject("car", (0.1, 0.1, 0.4, 0.4))]
    predictions = [
        Detection("car", 0.9, (0.1, 0.1, 0.4, 0.4)),
        Detection("car", 0.8, (0.11, 0.1, 0.41, 0.4)),
        Detection("person", 0.9, (0.1, 0.1, 0.4, 0.4)),
    ]
    result = evaluate_frame(truth, predictions)
    assert (result.true_positives, result.false_positives, result.false_negatives) == (1, 2, 0)
    assert result.duplicate_predictions == 1
    assert result.precision == pytest.approx(1 / 3)
    assert result.recall == 1.0


def test_aggregate_metrics_uses_counted_denominators() -> None:
    first = evaluate_frame([LabeledObject("person", (0, 0, 1, 1))], [])
    second = evaluate_frame([], [Detection("car", 0.7, (0, 0, 1, 1))])
    result = aggregate_metrics([first, second])
    assert (result.true_positives, result.false_positives, result.false_negatives) == (0, 1, 1)
    assert result.precision == 0.0
    assert result.recall == 0.0


def test_same_class_objects_are_not_duplicates_when_truth_has_two() -> None:
    truth = [
        LabeledObject("person", (0.0, 0.0, 0.4, 1.0)),
        LabeledObject("person", (0.6, 0.0, 1.0, 1.0)),
    ]
    predictions = [
        Detection("person", 0.9, (0.0, 0.0, 0.4, 1.0)),
        Detection("person", 0.9, (0.6, 0.0, 1.0, 1.0)),
    ]
    result = evaluate_frame(truth, predictions)
    assert result.duplicate_predictions == 0


def test_invalid_iou_threshold_is_rejected() -> None:
    with pytest.raises(ValueError):
        evaluate_frame([], [], iou_threshold=1.1)
