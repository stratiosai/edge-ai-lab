import importlib.util
from pathlib import Path

import pytest

MODULE_PATH = Path(__file__).parents[1] / "projects/private-ring-camera/phase5/evaluate_environment.py"
SPEC = importlib.util.spec_from_file_location("phase5_evaluate_environment", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_environment_manifest_requires_all_conditions(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="missing required conditions"):
        MODULE.parse_manifest_args([f"daylight={tmp_path / 'day.json'}"])


def test_environment_manifest_rejects_unknown_condition(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="unsupported condition"):
        MODULE.parse_manifest_args([f"fog={tmp_path / 'fog.json'}"])
