"""Small ONNX Runtime detector adapter for the Raspberry Pi.

The adapter accepts Ultralytics NMS exports and returns normalized boxes. It
does not save frames or emit notifications; callers decide when motion makes
inference appropriate and how to persist event suggestions.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
import onnxruntime as ort

from .motion import MotionZone
from .tracking import Box, Detection

COCO_TARGET_CLASSES = {0: "person", 2: "car", 3: "motorcycle", 5: "bus", 7: "truck"}


@dataclass(frozen=True)
class DetectorConfig:
    input_size: int = 320
    confidence_threshold: float = 0.45
    unknown_threshold: float = 0.20
    emit_unknown: bool = False
    target_classes: dict[int, str] | None = None

    def __post_init__(self) -> None:
        if self.input_size < 32 or self.input_size % 32:
            raise ValueError("input size must be a positive multiple of 32")
        if not 0.0 <= self.confidence_threshold <= 1.0:
            raise ValueError("confidence threshold must be between 0 and 1")
        if not 0.0 <= self.unknown_threshold <= self.confidence_threshold:
            raise ValueError("unknown threshold must be between 0 and confidence threshold")


def parse_nms_output(
    rows: np.ndarray,
    *,
    input_size: int,
    confidence_threshold: float,
    unknown_threshold: float = 0.20,
    emit_unknown: bool = False,
    target_classes: dict[int, str] | None = None,
) -> list[Detection]:
    """Parse `[x1,y1,x2,y2,score,class_id]` rows into normalized detections."""

    classes = target_classes or COCO_TARGET_CLASSES
    detections: list[Detection] = []
    for row in np.asarray(rows).reshape(-1, 6):
        x1, y1, x2, y2, score, class_id = row.tolist()
        label = classes.get(int(class_id))
        if score < unknown_threshold:
            continue
        if label is None or score < confidence_threshold:
            if not emit_unknown:
                continue
            label = "unknown"
        box: Box = (
            max(0.0, min(1.0, x1 / input_size)),
            max(0.0, min(1.0, y1 / input_size)),
            max(0.0, min(1.0, x2 / input_size)),
            max(0.0, min(1.0, y2 / input_size)),
        )
        if box[2] <= box[0] or box[3] <= box[1]:
            continue
        detections.append(Detection(label, float(score), box))
    return detections


class OnnxDetector:
    def __init__(self, model: Path, config: DetectorConfig | None = None) -> None:
        self.config = config or DetectorConfig()
        self.session = ort.InferenceSession(str(model), providers=["CPUExecutionProvider"])
        self.input_name = self.session.get_inputs()[0].name

    def detect(self, frame: np.ndarray, zones: list[MotionZone] | None = None) -> list[Detection]:
        resized = cv2.resize(
            frame,
            (self.config.input_size, self.config.input_size),
            interpolation=cv2.INTER_LINEAR,
        )
        tensor = resized[:, :, ::-1].transpose(2, 0, 1).astype(np.float32)[None] / 255.0
        rows = self.session.run(None, {self.input_name: tensor})[0][0]
        detections = parse_nms_output(
            rows,
            input_size=self.config.input_size,
            confidence_threshold=self.config.confidence_threshold,
            unknown_threshold=self.config.unknown_threshold,
            emit_unknown=self.config.emit_unknown,
            target_classes=self.config.target_classes,
        )
        enabled_zones = [zone for zone in (zones or []) if zone.enabled]
        if not enabled_zones:
            return detections
        return [
            detection
            for detection in detections
            if any(zone.contains_center(detection.box) for zone in enabled_zones)
        ]
