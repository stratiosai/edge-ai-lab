import pytest

from stratios_edge_ai.private_camera.events import EventSuggestion, clip_window, thumbnail_box


def test_event_suggestion_contains_review_metadata() -> None:
    event = EventSuggestion(
        event_id="evt-1",
        occurred_at=100,
        track_id=4,
        label="car",
        confidence=0.83,
        zone="driveway",
        count=2,
        direction="a-to-b",
        segment_id="seg-1",
        thumbnail_path="events/evt-1.jpg",
        clip_start=95,
        clip_end=110,
    )
    assert event.label == "car"
    assert clip_window(event.occurred_at) == (95, 110)


def test_thumbnail_box_is_clamped_to_frame() -> None:
    assert thumbnail_box((-0.2, 0.1, 1.2, 0.9), width=100, height=50) == (0, 5, 100, 45)


def test_event_validation_rejects_bad_confidence_and_clip() -> None:
    with pytest.raises(ValueError):
        EventSuggestion("evt", 1, 1, "person", 1.1, "yard", 1)
    with pytest.raises(ValueError):
        EventSuggestion("evt", 1, 1, "person", 0.5, "yard", 1, clip_start=2, clip_end=1)
