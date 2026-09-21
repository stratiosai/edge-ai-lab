"""Evaluate a labeled private-camera frame manifest with the ONNX adapter.

Manifest format (kept outside Git because image paths are private)::

    {"frames": [{"image": "/private/frame.jpg", "objects":
      [{"label": "car", "box": [0.1, 0.2, 0.4, 0.8]}]}]}
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2

from stratios_edge_ai.private_camera.detector import DetectorConfig, OnnxDetector
from stratios_edge_ai.private_camera.metrics import LabeledObject, aggregate_metrics, evaluate_frame


def load_manifest(path: Path) -> list[tuple[Path, list[LabeledObject]]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        frames = payload["frames"]
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid annotation manifest: {path}") from exc
    if not isinstance(frames, list) or not frames:
        raise ValueError("annotation manifest must contain a non-empty frames list")
    loaded: list[tuple[Path, list[LabeledObject]]] = []
    for index, frame in enumerate(frames):
        if not isinstance(frame, dict) or not isinstance(frame.get("image"), str):
            raise TypeError(f"frame {index} is missing an image path")
        objects = frame.get("objects", [])
        if not isinstance(objects, list):
            raise TypeError(f"frame {index} objects must be a list")
        labels: list[LabeledObject] = []
        for object_index, item in enumerate(objects):
            if not isinstance(item, dict) or not isinstance(item.get("label"), str):
                raise TypeError(f"frame {index} object {object_index} is invalid")
            box = item.get("box")
            if not isinstance(box, list) or len(box) != 4:
                raise ValueError(f"frame {index} object {object_index} box must have four values")
            labels.append(LabeledObject(item["label"], tuple(float(value) for value in box)))
        loaded.append((Path(frame["image"]), labels))
    return loaded


def evaluate_manifest(model: Path, manifest: Path, *, size: int, confidence: float) -> dict[str, object]:
    detector = OnnxDetector(model, DetectorConfig(input_size=size, confidence_threshold=confidence))
    results: list[dict[str, object]] = []
    metrics = []
    for image_path, truth in load_manifest(manifest):
        image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
        if image is None:
            raise ValueError(f"cannot read labeled image: {image_path}")
        frame_metrics = evaluate_frame(truth, detector.detect(image))
        metrics.append(frame_metrics)
        results.append(
            {
                "image": str(image_path),
                "truth_count": len(truth),
                "true_positives": frame_metrics.true_positives,
                "false_positives": frame_metrics.false_positives,
                "false_negatives": frame_metrics.false_negatives,
                "duplicate_predictions": frame_metrics.duplicate_predictions,
            }
        )
    aggregate = aggregate_metrics(metrics)
    return {
        "model": str(model),
        "manifest": str(manifest),
        "frame_count": len(results),
        "true_positives": aggregate.true_positives,
        "false_positives": aggregate.false_positives,
        "false_negatives": aggregate.false_negatives,
        "duplicate_predictions": aggregate.duplicate_predictions,
        "precision": aggregate.precision,
        "recall": aggregate.recall,
        "frames": results,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("model", type=Path)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--size", type=int, default=320)
    parser.add_argument("--confidence", type=float, default=0.45)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = evaluate_manifest(args.model, args.manifest, size=args.size, confidence=args.confidence)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
