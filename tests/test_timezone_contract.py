from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from pathlib import Path

from test_private_camera import ingest, login, make_client

ROOT = Path(__file__).parents[1]
TIME_UTILS = ROOT / "src/stratios_edge_ai/private_camera/web/time-utils.js"


def test_browser_time_helpers_preserve_dst_boundaries_across_timezones() -> None:
    node = shutil.which("node")
    if node is None:
        raise AssertionError("Node.js is required for the browser time contract test")
    script = f"""
const t = require({json.dumps(str(TIME_UTILS))});
const cases = [
  [Date.parse('2026-11-01T05:30:00Z') / 1000, 'Sun, Nov 1'],
  [Date.parse('2026-11-01T06:30:00Z') / 1000, 'Sun, Nov 1'],
];
for (const [epoch, day] of cases) {{
  if (!t.localDay(epoch).startsWith(process.env.EXPECTED_DAY)) throw new Error(t.localDay(epoch));
  const input = t.localInputValue(epoch);
  if (!input.startsWith(process.env.EXPECTED_DATE)) throw new Error(input);
  if (t.epochForInput(input, epoch) !== epoch) throw new Error('ambiguous input was not preserved');
}}
"""
    expected = {
        "America/New_York": ("Sun, Nov 1", "2026-11-01T"),
        "America/Los_Angeles": ("Sat, Oct 31", "2026-10-31T"),
    }
    for timezone, (expected_day, expected_date) in expected.items():
        env = {**os.environ, "TZ": timezone, "EXPECTED_DAY": expected_day, "EXPECTED_DATE": expected_date}
        result = subprocess.run([node, "-e", script], check=False, env=env, capture_output=True, text=True)
        assert result.returncode == 0, f"{timezone}: {result.stderr}"


def test_archive_index_and_playback_keep_epoch_seconds_at_day_boundary(tmp_path: Path) -> None:
    client = make_client(tmp_path)
    login(client)
    first = int(time.time()) - 120
    second = int(time.time()) - 60
    first_id = ingest(client, started_at=first, ended_at=first + 60, body=b"before-fallback")
    second_id = ingest(client, started_at=second, ended_at=second + 60, body=b"after-fallback")
    rows = {row["id"]: row for row in client.get("/api/segments").json()["segments"]}
    assert rows[first_id]["started_at"] == first
    assert rows[second_id]["started_at"] == second
    assert client.get(f"/api/segments/{first_id}/media").content == b"before-fallback"
    assert client.get(f"/api/segments/{second_id}/media").content == b"after-fallback"
