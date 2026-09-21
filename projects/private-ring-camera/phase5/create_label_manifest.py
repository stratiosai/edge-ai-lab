"""Extract private review frames and create a labeling-manifest template."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2

CONDITIONS = {"controlled-indoor", "daylight", "darkness", "rain", "glare", "shadows", "occlusion"}

def create_manifest(
    segment: Path,
    output_dir: Path,
    *,
    samples: int = 12,
    condition: str = "controlled-indoor",
) -> Path:
    if samples < 1:
        raise ValueError("samples must be positive")
    if condition not in CONDITIONS:
        raise ValueError(f"unsupported condition: {condition}")
    capture = cv2.VideoCapture(str(segment))
    if not capture.isOpened():
        raise ValueError(f"cannot open segment: {segment}")
    total = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = capture.get(cv2.CAP_PROP_FPS) or 15.0
    if total < 1:
        capture.release()
        raise ValueError("segment has no frames")
    output_dir.mkdir(parents=True, exist_ok=True)
    frames: list[dict[str, object]] = []
    for index in range(samples):
        frame_index = round(index * (total - 1) / max(1, samples - 1))
        capture.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
        ok, frame = capture.read()
        if not ok:
            continue
        image = output_dir / f"frame-{index:03d}.jpg"
        if not cv2.imwrite(str(image), frame, [cv2.IMWRITE_JPEG_QUALITY, 90]):
            raise OSError(f"could not write {image}")
        frames.append(
            {
                "image": str(image),
                "timestamp_seconds": round(frame_index / fps, 3),
                "condition": condition,
                "objects": [],
            }
        )
    capture.release()
    manifest = output_dir / "labels.json"
    manifest.write_text(json.dumps({"frames": frames}, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("segment", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--samples", type=int, default=12)
    parser.add_argument("--condition", choices=sorted(CONDITIONS), required=True)
    args = parser.parse_args()
    print(create_manifest(args.segment, args.output_dir, samples=args.samples, condition=args.condition))


if __name__ == "__main__":
    main()
