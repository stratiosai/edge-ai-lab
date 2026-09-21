import importlib.util
import json
from pathlib import Path

import pytest

MODULE_PATH = Path(__file__).parents[1] / "projects/private-ring-camera/phase5/evaluate_accuracy.py"
SPEC = importlib.util.spec_from_file_location("phase5_evaluate_accuracy", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
load_manifest = MODULE.load_manifest


def test_load_manifest_reads_normalized_boxes(tmp_path) -> None:
    manifest = tmp_path / "labels.json"
    manifest.write_text(
        json.dumps({"frames": [{"image": "/private/frame.jpg", "objects": [{"label": "car", "box": [0, 0.1, 0.5, 1]}]}]}),
        encoding="utf-8",
    )
    frames = load_manifest(manifest)
    assert frames[0][0].name == "frame.jpg"
    assert frames[0][1][0].box == (0.0, 0.1, 0.5, 1.0)


def test_load_manifest_rejects_empty_frames(tmp_path) -> None:
    manifest = tmp_path / "labels.json"
    manifest.write_text('{"frames": []}', encoding="utf-8")
    with pytest.raises(ValueError, match="non-empty"):
        load_manifest(manifest)
