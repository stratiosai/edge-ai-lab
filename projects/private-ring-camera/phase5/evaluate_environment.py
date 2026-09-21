"""Evaluate all required environmental labels before enabling live detection."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from evaluate_accuracy import evaluate_manifest

REQUIRED_CONDITIONS = (
    "daylight",
    "darkness",
    "rain",
    "glare",
    "shadows",
    "occlusion",
)


def parse_manifest_args(values: list[str]) -> dict[str, Path]:
    manifests: dict[str, Path] = {}
    for value in values:
        if "=" not in value:
            raise ValueError(f"manifest must be CONDITION=PATH: {value}")
        condition, raw_path = value.split("=", 1)
        if condition not in REQUIRED_CONDITIONS:
            raise ValueError(f"unsupported condition: {condition}")
        if not raw_path or condition in manifests:
            raise ValueError(f"duplicate or empty manifest for condition: {condition}")
        manifests[condition] = Path(raw_path)
    missing = [condition for condition in REQUIRED_CONDITIONS if condition not in manifests]
    if missing:
        raise ValueError("missing required conditions: " + ", ".join(missing))
    return manifests


def evaluate_environment(
    model: Path,
    manifests: dict[str, Path],
    *,
    size: int = 320,
    confidence: float = 0.45,
    min_precision: float = 0.9,
    min_recall: float = 0.9,
    max_duplicates: int = 0,
) -> dict[str, object]:
    results = {
        condition: evaluate_manifest(model, manifest, size=size, confidence=confidence)
        for condition, manifest in manifests.items()
    }
    failures = {
        condition: {
            "precision": float(result["precision"]) < min_precision,
            "recall": float(result["recall"]) < min_recall,
            "duplicates": int(result["duplicate_predictions"]) > max_duplicates,
        }
        for condition, result in results.items()
    }
    return {
        "model": str(model),
        "conditions": results,
        "thresholds": {
            "min_precision": min_precision,
            "min_recall": min_recall,
            "max_duplicates": max_duplicates,
        },
        "failures": failures,
        "accepted": not any(any(items.values()) for items in failures.values()),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("model", type=Path)
    parser.add_argument("--manifest", action="append", required=True, metavar="CONDITION=PATH")
    parser.add_argument("--size", type=int, default=320)
    parser.add_argument("--confidence", type=float, default=0.45)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        manifests = parse_manifest_args(args.manifest)
    except ValueError as exc:
        parser.error(str(exc))
    result = evaluate_environment(args.model, manifests, size=args.size, confidence=args.confidence)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    if not result["accepted"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
