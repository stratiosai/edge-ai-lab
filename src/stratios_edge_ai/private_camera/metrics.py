"""Accuracy metrics for the Phase 5 labeled-camera gate."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from .tracking import Box, Detection, iou


@dataclass(frozen=True)
class LabeledObject:
    label: str
    box: Box


@dataclass(frozen=True)
class FrameMetrics:
    true_positives: int
    false_positives: int
    false_negatives: int
    duplicate_predictions: int

    @property
    def precision(self) -> float:
        denominator = self.true_positives + self.false_positives
        return self.true_positives / denominator if denominator else 1.0

    @property
    def recall(self) -> float:
        denominator = self.true_positives + self.false_negatives
        return self.true_positives / denominator if denominator else 1.0


def evaluate_frame(
    truth: list[LabeledObject],
    predictions: list[Detection],
    *,
    iou_threshold: float = 0.5,
) -> FrameMetrics:
    """Greedily match each truth object to at most one same-class prediction."""

    if not 0.0 <= iou_threshold <= 1.0:
        raise ValueError("IoU threshold must be between 0 and 1")
    candidates = sorted(
        (
            iou(actual.box, prediction.box),
            truth_index,
            prediction_index,
        )
        for truth_index, actual in enumerate(truth)
        for prediction_index, prediction in enumerate(predictions)
        if actual.label == prediction.label
    )
    matched_truth: set[int] = set()
    matched_predictions: set[int] = set()
    for overlap, truth_index, prediction_index in reversed(candidates):
        if overlap < iou_threshold or truth_index in matched_truth or prediction_index in matched_predictions:
            continue
        matched_truth.add(truth_index)
        matched_predictions.add(prediction_index)
    true_positives = len(matched_truth)
    unmatched_predictions = len(predictions) - len(matched_predictions)
    duplicate_predictions = sum(
        max(0, count - 1)
        for label, count in Counter(prediction.label for prediction in predictions).items()
        if any(actual.label == label for actual in truth)
    )
    return FrameMetrics(
        true_positives=true_positives,
        false_positives=unmatched_predictions,
        false_negatives=len(truth) - true_positives,
        duplicate_predictions=duplicate_predictions,
    )


def aggregate_metrics(frames: list[FrameMetrics]) -> FrameMetrics:
    """Aggregate frame counts before calculating precision/recall."""

    return FrameMetrics(
        true_positives=sum(frame.true_positives for frame in frames),
        false_positives=sum(frame.false_positives for frame in frames),
        false_negatives=sum(frame.false_negatives for frame in frames),
        duplicate_predictions=sum(frame.duplicate_predictions for frame in frames),
    )
