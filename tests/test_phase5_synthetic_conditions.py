import importlib.util
import json
from pathlib import Path

import cv2
import numpy as np

MODULE_PATH = Path(__file__).parents[1] / "projects/private-ring-camera/phase5/create_synthetic_conditions.py"
SPEC = importlib.util.spec_from_file_location("phase5_synthetic_conditions", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_synthetic_transform_changes_frame_without_mutating_source() -> None:
    source = np.full((30, 40, 3), 200, dtype=np.uint8)
    original = source.copy()
    output = MODULE.transform(source, "darkness")
    assert np.array_equal(source, original)
    assert output.mean() < source.mean()


def test_create_variants_writes_all_condition_manifests(tmp_path: Path) -> None:
    image = tmp_path / "frame.jpg"
    cv2.imwrite(str(image), np.full((20, 30, 3), 180, dtype=np.uint8))
    manifest = tmp_path / "labels.json"
    manifest.write_text(json.dumps({"frames": [{"image": str(image), "objects": []}]}), encoding="utf-8")
    result = MODULE.create_variants(manifest, tmp_path / "variants")
    assert set(result) == set(MODULE.CONDITIONS)
    assert all(path.is_file() for path in result.values())
