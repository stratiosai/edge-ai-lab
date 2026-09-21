from __future__ import annotations

import hashlib
import time
import zipfile
from io import BytesIO
from pathlib import Path

from fastapi.testclient import TestClient

from stratios_edge_ai.private_camera.admin import set_admin
from stratios_edge_ai.private_camera.app import create_app
from stratios_edge_ai.private_camera.config import CameraServerConfig

PASSWORD = "correct horse camera battery"
INGEST_TOKEN = "test-ingest-token"


def make_client(tmp_path: Path, *, max_archive_bytes: int = 1024 * 1024) -> TestClient:
    config = CameraServerConfig(
        data_dir=tmp_path / "private-camera",
        secure_cookies=False,
        ingest_token=INGEST_TOKEN,
        max_archive_bytes=max_archive_bytes,
    )
    app = create_app(config)
    set_admin(app.state.database, "admin", PASSWORD)
    return TestClient(app)


def login(client: TestClient) -> str:
    response = client.post("/api/login", json={"username": "admin", "password": PASSWORD})
    assert response.status_code == 200
    return response.json()["csrf_token"]


def ingest(client: TestClient, *, started_at: int, ended_at: int, body: bytes = b"video") -> str:
    response = client.post(
        "/api/ingest/segment",
        content=body,
        headers={
            "X-Ingest-Token": INGEST_TOKEN,
            "X-Segment-Started-At": str(started_at),
            "X-Segment-Ended-At": str(ended_at),
            "X-Segment-Extension": ".mp4",
        },
    )
    assert response.status_code == 200
    return response.json()["segment_id"]


def test_protected_routes_require_authentication(tmp_path: Path) -> None:
    client = make_client(tmp_path)
    assert client.get("/api/session").status_code == 401
    assert client.get("/api/health").status_code == 401
    assert client.get("/api/segments").status_code == 401
    assert client.get("/api/events").status_code == 401
    assert client.get("/api/live").status_code == 401
    assert client.get("/api/segments/not-a-real-segment/thumbnail").status_code == 401
    assert client.get("/api/events/not-a-real-event/thumbnail").status_code == 401
    assert client.get("/latency-test").status_code == 401


def test_authenticated_latency_reference_is_available(tmp_path: Path) -> None:
    client = make_client(tmp_path)
    login(client)
    reference = client.get("/latency-test")
    assert reference.status_code == 200
    assert "LATENCY REFERENCE" in reference.text
    assert client.get("/latency-test.js").status_code == 200


def test_login_session_logout_and_security_headers(tmp_path: Path) -> None:
    client = make_client(tmp_path)
    assert (
        client.post(
            "/api/login", json={"username": "admin", "password": "incorrect password"}
        ).status_code
        == 401
    )

    csrf = login(client)
    session = client.get("/api/session")
    assert session.status_code == 200
    assert session.json()["username"] == "admin"
    assert session.json()["csrf_token"] == csrf
    assert session.headers["x-frame-options"] == "DENY"
    assert session.headers["cache-control"] == "no-store"

    assert client.post("/api/logout").status_code == 403
    assert client.post("/api/logout", headers={"X-CSRF-Token": csrf}).status_code == 200
    assert client.get("/api/session").status_code == 401


def test_ingest_timeline_media_export_and_verified_delete(tmp_path: Path) -> None:
    client = make_client(tmp_path)
    csrf = login(client)
    now = int(time.time())
    body = b"synthetic-mp4-test-payload"
    segment_id = ingest(client, started_at=now - 60, ended_at=now, body=body)

    timeline = client.get("/api/segments").json()["segments"]
    assert [item["id"] for item in timeline] == [segment_id]
    assert timeline[0]["sha256"] == hashlib.sha256(body).hexdigest()
    assert client.get(f"/api/segments/{segment_id}/media").content == body
    assert client.get(f"/api/segments/{segment_id}/thumbnail").status_code == 404
    export = client.get(f"/api/segments/{segment_id}/export")
    assert export.content == body
    assert "attachment" in export.headers["content-disposition"]

    assert client.delete(f"/api/segments/{segment_id}").status_code == 403
    deleted = client.delete(f"/api/segments/{segment_id}", headers={"X-CSRF-Token": csrf})
    assert deleted.status_code == 200
    assert client.get(f"/api/segments/{segment_id}/media").status_code == 404
    assert client.get("/api/segments").json()["segments"] == []
    assert list((tmp_path / "private-camera" / "archive").iterdir()) == []


def test_timeline_exposes_optional_motion_metadata(tmp_path: Path) -> None:
    client = make_client(tmp_path)
    now = int(time.time())
    response = client.post(
        "/api/ingest/segment",
        content=b"motion",
        headers={
            "X-Ingest-Token": INGEST_TOKEN,
            "X-Segment-Started-At": str(now - 60),
            "X-Segment-Ended-At": str(now),
            "X-Segment-Extension": ".mp4",
            "X-Segment-Motion-Score": "0.125",
            "X-Segment-Motion-Detected": "true",
        },
    )
    assert response.status_code == 200
    login(client)
    segment = client.get("/api/segments").json()["segments"][0]
    assert segment["motion_score"] == 0.125
    assert segment["motion_detected"] == 1


def test_event_ingest_is_idempotent_and_authenticated_for_readback(tmp_path: Path) -> None:
    client = make_client(tmp_path)
    now = int(time.time())
    payload = {
        "event_id": "evt-1",
        "occurred_at": now - 10,
        "track_id": 3,
        "label": "car",
        "confidence": 0.91,
        "zone": "driveway",
        "count": 1,
        "direction": "a-to-b",
        "thumbnail_path": "events/evt-1.jpg",
        "clip_start": now - 15,
        "clip_end": now,
    }
    missing_token = client.post("/api/ingest/event", json=payload)
    assert missing_token.status_code == 401
    headers = {"X-Ingest-Token": INGEST_TOKEN}
    first = client.post("/api/ingest/event", json=payload, headers=headers)
    second = client.post("/api/ingest/event", json=payload, headers=headers)
    assert first.status_code == second.status_code == 200
    assert first.json()["result"] == "created"
    assert second.json()["result"] == "already-present"
    login(client)
    events = client.get("/api/events").json()["events"]
    assert events[0]["label"] == "car"
    assert events[0]["direction"] == "a-to-b"
    assert client.get("/api/events/evt-1/thumbnail").status_code == 404


def test_event_ingest_rejects_invalid_metadata(tmp_path: Path) -> None:
    client = make_client(tmp_path)
    response = client.post(
        "/api/ingest/event",
        json={
            "event_id": "bad",
            "occurred_at": int(time.time()),
            "track_id": 1,
            "label": "person",
            "confidence": 1.5,
            "zone": "yard",
            "count": 1,
        },
        headers={"X-Ingest-Token": INGEST_TOKEN},
    )
    assert response.status_code == 422


def test_authenticated_range_export_is_local_zip(tmp_path: Path) -> None:
    client = make_client(tmp_path)
    now = int(time.time())
    first_id = ingest(client, started_at=now - 180, ended_at=now - 120, body=b"first")
    second_id = ingest(client, started_at=now - 120, ended_at=now - 60, body=b"second")
    assert client.get(f"/api/segments/export?since={now - 200}&until={now}").status_code == 401
    login(client)
    exported = client.get(f"/api/segments/export?since={now - 200}&until={now}")
    assert exported.status_code == 200
    assert exported.headers["content-type"].startswith("application/zip")
    with zipfile.ZipFile(BytesIO(exported.content)) as bundle:
        names = bundle.namelist()
        assert "manifest.json" in names
        manifest = bundle.read("manifest.json").decode()
        assert first_id in manifest and second_id in manifest
        assert len([name for name in names if name.endswith(".mp4")]) == 2


def test_segment_ingest_is_idempotent_and_verifies_digest(tmp_path: Path) -> None:
    client = make_client(tmp_path)
    now = int(time.time())
    body = b"idempotent synthetic segment"
    headers = {
        "X-Ingest-Token": INGEST_TOKEN,
        "X-Segment-Started-At": str(now - 60),
        "X-Segment-Ended-At": str(now),
        "X-Segment-Extension": ".mp4",
        "X-Segment-Sha256": hashlib.sha256(body).hexdigest(),
    }
    first = client.post("/api/ingest/segment", content=body, headers=headers)
    second = client.post("/api/ingest/segment", content=body, headers=headers)
    assert first.status_code == second.status_code == 200
    assert first.json()["segment_id"] == second.json()["segment_id"]
    assert first.json()["result"] == "created"
    assert second.json()["result"] == "already-present"

    headers["X-Segment-Sha256"] = "0" * 64
    assert (
        client.post("/api/ingest/segment", content=b"different", headers=headers).status_code == 422
    )


def test_timeline_tolerates_small_clock_skew_and_rejects_large_future_time(tmp_path: Path) -> None:
    client = make_client(tmp_path)
    now = int(time.time())
    near_future = ingest(client, started_at=now + 240, ended_at=now + 300)
    login(client)
    assert near_future in [segment["id"] for segment in client.get("/api/segments").json()["segments"]]
    response = client.post(
        "/api/ingest/segment",
        content=b"far-future",
        headers={
            "X-Ingest-Token": INGEST_TOKEN,
            "X-Segment-Started-At": str(now + 301),
            "X-Segment-Ended-At": str(now + 361),
            "X-Segment-Extension": ".mp4",
        },
    )
    assert response.status_code == 422
    assert "synchronize the Pi clock" in response.json()["detail"]


def test_retention_removes_expired_media_and_index(tmp_path: Path) -> None:
    client = make_client(tmp_path)
    csrf = login(client)
    now = int(time.time())
    expired_id = ingest(client, started_at=now - 90000, ended_at=now - 89900)
    current_id = ingest(client, started_at=now - 120, ended_at=now - 60)

    result = client.post("/api/retention/run", headers={"X-CSRF-Token": csrf})
    assert result.status_code == 200
    assert result.json()["expired_segment_ids"] == [expired_id]
    assert client.get(f"/api/segments/{expired_id}/media").status_code == 404
    assert client.get(f"/api/segments/{current_id}/media").status_code == 200


def test_startup_retention_removes_only_expired_recordings(tmp_path: Path) -> None:
    config = CameraServerConfig(
        data_dir=tmp_path / "private-camera",
        secure_cookies=False,
        ingest_token=INGEST_TOKEN,
        retention_interval_minutes=60,
    )
    app = create_app(config)
    set_admin(app.state.database, "admin", PASSWORD)
    with TestClient(app) as client:
        now = int(time.time())
        expired_id = ingest(client, started_at=now - 90000, ended_at=now - 89900)
        current_id = ingest(client, started_at=now - 120, ended_at=now - 60)
        # The next clean service start enforces the retention window; the
        # current segment remains available and no user action is required.
    with TestClient(app) as restarted:
        assert restarted.get(f"/api/segments/{expired_id}/media").status_code == 401
        csrf = login(restarted)
        assert restarted.get(f"/api/segments/{expired_id}/media").status_code == 404
        assert restarted.get(f"/api/segments/{current_id}/media").status_code == 200
        assert csrf


def test_ingest_auth_validation_and_storage_high_water(tmp_path: Path) -> None:
    client = make_client(tmp_path, max_archive_bytes=8)
    now = int(time.time())
    headers = {
        "X-Segment-Started-At": str(now - 1),
        "X-Segment-Ended-At": str(now),
        "X-Segment-Extension": ".mp4",
    }
    assert client.post("/api/ingest/segment", content=b"1234", headers=headers).status_code == 401
    headers["X-Ingest-Token"] = INGEST_TOKEN
    assert (
        client.post("/api/ingest/segment", content=b"123456789", headers=headers).status_code == 507
    )
    headers["X-Segment-Extension"] = ".exe"
    assert client.post("/api/ingest/segment", content=b"1", headers=headers).status_code == 422


def test_logout_all_revokes_every_session(tmp_path: Path) -> None:
    first = make_client(tmp_path)
    csrf_first = login(first)
    second = TestClient(first.app)
    login(second)
    assert second.get("/api/session").status_code == 200

    response = first.post("/api/logout-all", headers={"X-CSRF-Token": csrf_first})
    assert response.status_code == 200
    assert first.get("/api/session").status_code == 401
    assert second.get("/api/session").status_code == 401
