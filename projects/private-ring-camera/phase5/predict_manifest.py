"""Write detector suggestions beside a private frame-label manifest."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2

from stratios_edge_ai.private_camera.detector import DetectorConfig, OnnxDetector
from stratios_edge_ai.private_camera.motion import MotionZone


def predict_manifest(
    manifest: Path,
    model: Path,
    output: Path,
    *,
    confidence: float = 0.20,
) -> Path:
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    detector = OnnxDetector(
        model,
        DetectorConfig(confidence_threshold=confidence, emit_unknown=True),
    )
    zone = MotionZone("controlled-test-area", 0.0, 0.0, 1.0, 1.0)
    frames: list[dict[str, object]] = []
    for item in payload.get("frames", []):
        image = Path(str(item["image"]))
        frame = cv2.imread(str(image))
        if frame is None:
            raise ValueError(f"cannot read image: {image}")
        detections = detector.detect(frame, [zone])
        frames.append(
            {
                "image": str(image),
                "predictions": [
                    {
                        "label": detection.label,
                        "confidence": round(detection.score, 6),
                        "box": [round(value, 6) for value in detection.box],
                    }
                    for detection in detections
                ],
            }
        )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(
            {
                "model": str(model),
                "confidence_threshold": confidence,
                "frames": frames,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("model", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--confidence", type=float, default=0.20)
    args = parser.parse_args()
    print(predict_manifest(**vars(args)))


if __name__ == "__main__":
    main()
