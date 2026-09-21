"""Run a small, repeatable ONNX detector benchmark on the Pi.

The exported models include NMS (`[x1, y1, x2, y2, score, class_id]` rows),
so this script intentionally avoids installing the full training stack on the
Pi. It reports latency and target-class counts; it does not save camera frames.
"""

from __future__ import annotations

import argparse
import json
import statistics
import subprocess
import time
from pathlib import Path

import cv2
import numpy as np
import onnxruntime as ort

TARGET_CLASSES = {0: "person", 2: "car", 3: "motorcycle", 5: "bus", 7: "truck"}


def temperature_c() -> float | None:
    path = Path("/sys/class/thermal/thermal_zone0/temp")
    try:
        return int(path.read_text().strip()) / 1000
    except (OSError, ValueError):
        return None


def throttled() -> str | None:
    try:
        result = subprocess.run(
            ["vcgencmd", "get_throttled"], capture_output=True, text=True, check=False
        )
    except OSError:
        return None
    return result.stdout.strip() or None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("model", type=Path)
    parser.add_argument("image", type=Path)
    parser.add_argument("--size", type=int, default=320)
    parser.add_argument("--iterations", type=int, default=100)
    parser.add_argument("--confidence", type=float, default=0.45)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    image = cv2.imread(str(args.image), cv2.IMREAD_COLOR)
    if image is None:
        raise SystemExit(f"cannot read image: {args.image}")
    image = cv2.resize(image, (args.size, args.size), interpolation=cv2.INTER_LINEAR)
    tensor = image[:, :, ::-1].transpose(2, 0, 1).astype(np.float32)[None] / 255.0

    session = ort.InferenceSession(str(args.model), providers=["CPUExecutionProvider"])
    input_name = session.get_inputs()[0].name
    session.run(None, {input_name: tensor})  # warm up kernels
    latencies: list[float] = []
    counts: dict[str, int] = {name: 0 for name in TARGET_CLASSES.values()}
    for _ in range(args.iterations):
        start = time.perf_counter()
        output = session.run(None, {input_name: tensor})[0][0]
        latencies.append((time.perf_counter() - start) * 1000)
        for row in output:
            x1, y1, x2, y2, score, class_id = row.tolist()
            del x1, y1, x2, y2
            label = TARGET_CLASSES.get(int(class_id))
            if label and score >= args.confidence:
                counts[label] += 1

    result = {
        "model": str(args.model),
        "image": str(args.image),
        "input_size": args.size,
        "iterations": args.iterations,
        "median_latency_ms": statistics.median(latencies),
        "p95_latency_ms": sorted(latencies)[max(0, int(args.iterations * 0.95) - 1)],
        "average_fps": 1000 / statistics.mean(latencies),
        "target_class_hits": counts,
        "temperature_start_c": temperature_c(),
        "temperature_end_c": temperature_c(),
        "throttled": throttled(),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
