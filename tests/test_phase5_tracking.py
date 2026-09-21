from stratios_edge_ai.private_camera.tracking import Detection, IoUTracker, iou


def test_iou_and_single_object_are_stable_across_frames() -> None:
    assert iou((0, 0, 10, 10), (0, 0, 10, 10)) == 1
    tracker = IoUTracker(min_hits=2)
    detection = Detection("car", 0.9, (0.1, 0.1, 0.3, 0.3))
    tracks, events = tracker.update([detection])
    assert tracks == []
    assert events == []
    tracks, events = tracker.update([Detection("car", 0.8, (0.11, 0.1, 0.31, 0.3))])
    assert len(tracks) == 1
    assert len(events) == 1
    track_id = tracks[0].track_id
    tracks, events = tracker.update([Detection("car", 0.85, (0.12, 0.1, 0.32, 0.3))])
    assert tracks[0].track_id == track_id
    assert events == []


def test_tracker_expires_and_recounts_after_max_age() -> None:
    tracker = IoUTracker(max_age_frames=1, min_hits=1)
    tracker.update([Detection("person", 0.9, (0, 0, 0.2, 0.2))])
    tracker.update([])
    tracks, events = tracker.update([])
    assert tracks == []
    tracks, events = tracker.update([Detection("person", 0.9, (0, 0, 0.2, 0.2))])
    assert tracks[0].track_id == 2
    assert len(events) == 1

