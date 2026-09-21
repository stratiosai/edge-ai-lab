import importlib.util
from pathlib import Path

import pytest

MODULE_PATH = Path(__file__).parents[1] / "projects/private-ring-camera/phase5/create_label_manifest.py"
SPEC = importlib.util.spec_from_file_location("create_label_manifest", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_manifest_rejects_empty_sample_count(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="positive"):
        MODULE.create_manifest(tmp_path / "missing.mp4", tmp_path / "frames", samples=0)
