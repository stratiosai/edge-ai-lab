"""Create private, deterministic stress variants for evaluator smoke tests.

Synthetic variants validate evaluator wiring only; they are never real
environmental acceptance evidence.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np

CONDITIONS = ("daylight", "darkness", "rain", "glare", "shadows", "occlusion")


def transform(frame: np.ndarray, condition: str) -> np.ndarray:
    output = frame.copy()
    height, width = output.shape[:2]
    if condition == "daylight":
        return cv2.convertScaleAbs(output, alpha=1.1, beta=12)
    if condition == "darkness":
        return (output.astype(np.float32) * 0.2).astype(np.uint8)
    if condition == "glare":
        cv2.ellipse(output, (width // 3, height // 3), (width // 5, height // 6), 0, 0, 360, (255, 255, 255), -1)
        return cv2.addWeighted(output, 0.65, frame, 0.35, 0)
    if condition == "shadows":
        overlay = output.copy()
        cv2.rectangle(overlay, (0, height // 3), (width // 2, height), (0, 0, 0), -1)
        return cv2.addWeighted(overlay, 0.45, output, 0.55, 0)
    if condition == "rain":
        for x in range(-height, width, max(20, width // 24)):
            cv2.line(output, (x, 0), (x + height // 8, height), (220, 220, 220), 2)
        return cv2.addWeighted(output, 0.75, frame, 0.25, 0)
    if condition == "occlusion":
        cv2.rectangle(output, (width // 3, height // 4), (width // 2, height), (80, 80, 80), -1)
        return output
    raise ValueError(f"unsupported condition: {condition}")


def create_variants(manifest: Path, output_dir: Path) -> dict[str, Path]:
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    results: dict[str, Path] = {}
    for condition in CONDITIONS:
        condition_dir = output_dir / condition
        condition_dir.mkdir(parents=True, exist_ok=True)
        frames = []
        for index, item in enumerate(payload["frames"]):
            source = cv2.imread(str(item["image"]), cv2.IMREAD_COLOR)
            if source is None:
                raise ValueError(f"cannot read image: {item['image']}")
            destination = condition_dir / f"frame-{index:03d}.jpg"
            cv2.imwrite(str(destination), transform(source, condition), [cv2.IMWRITE_JPEG_QUALITY, 90])
            frames.append({**item, "image": str(destination), "condition": condition})
        target = condition_dir / "labels.json"
        target.write_text(json.dumps({"frames": frames}, indent=2) + "\n", encoding="utf-8")
        results[condition] = target
    return results


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()
    print(json.dumps({key: str(value) for key, value in create_variants(args.manifest, args.output_dir).items()}, indent=2))


if __name__ == "__main__":
    main()
