import numpy as np
import pytest

from stratios_edge_ai.private_camera.privacy import (
    PrivacyMask,
    apply_privacy_masks,
    load_privacy_masks,
)


def test_privacy_mask_blacks_only_derived_copy() -> None:
    frame = np.full((10, 20, 3), 255, dtype=np.uint8)
    masked = apply_privacy_masks(frame, [PrivacyMask("window", 0.25, 0.2, 0.75, 0.8)])
    assert np.all(frame == 255)
    assert np.all(masked[2:8, 5:15] == 0)
    assert np.all(masked[:2] == 255)


def test_privacy_mask_validates_bounds() -> None:
    with pytest.raises(ValueError, match="between 0 and 1"):
        PrivacyMask("bad", -0.1, 0.0, 0.5, 0.5)
    with pytest.raises(ValueError, match="positive area"):
        PrivacyMask("bad", 0.5, 0.5, 0.5, 0.7)


def test_privacy_masks_load_from_owner_controlled_json(tmp_path) -> None:
    path = tmp_path / "masks.json"
    path.write_text('[{"name":"window","left":0,"top":0,"right":0.2,"bottom":1}]')
    masks = load_privacy_masks(path)
    assert masks[0].name == "window"
