let csrfToken = null;

async function api(path, options = {}) {
  const headers = {...(options.headers || {})};
  if (csrfToken && !["GET", "HEAD"].includes((options.method || "GET").toUpperCase())) {
    headers["X-CSRF-Token"] = csrfToken;
  }
  const response = await fetch(path, {...options, headers});
  if (response.status === 401) showLogin();
  return response;
}

function showLogin() {
  document.querySelector("#login-card").hidden = false;
  document.querySelector("#dashboard").hidden = true;
  document.querySelector("#live-view").removeAttribute("src");
}

async function showDashboard(session) {
  csrfToken = session.csrf_token;
  document.querySelector("#login-card").hidden = true;
  document.querySelector("#dashboard").hidden = false;
  document.querySelector("#live-view").src = `/api/live?cache=${Date.now()}`;
  await Promise.all([loadHealth(), loadTimeline()]);
}

async function loadHealth() {
  const response = await api("/api/health");
  if (!response.ok) return;
  const health = await response.json();
  document.querySelector("#server-status").textContent = health.server;
  document.querySelector("#camera-status").textContent = health.camera?.camera || "Not connected";
  document.querySelector("#archive-size").textContent = `${(health.archive_bytes / 1073741824).toFixed(2)} GB`;
  const detail = document.querySelector("#health-detail");
  if (!health.camera) {
    detail.textContent = "Waiting for the Pi to report camera health.";
    return;
  }
  const reported = health.camera_updated_at ? new Date(health.camera_updated_at * 1000).toLocaleTimeString() : "unknown time";
  const temperature = health.camera.temperature ? ` · ${health.camera.temperature}` : "";
  const throttled = health.camera.throttled ? ` · ${health.camera.throttled}` : "";
  detail.textContent = `Pi health updated ${reported}${temperature}${throttled}`;
}

async function deleteSegment(id) {
  if (!confirm("Permanently delete this local recording segment?")) return;
  const response = await api(`/api/segments/${id}`, {method: "DELETE"});
  if (response.ok) await loadTimeline();
}

async function logoutAllDevices() {
  if (!confirm("Log out this administrator on every device?")) return;
  const response = await api("/api/logout-all", {method: "POST"});
  if (response.ok) {
    csrfToken = null;
    showLogin();
  }
}

async function loadTimeline() {
  const response = await api("/api/segments");
  if (!response.ok) return;
  const {segments} = await response.json();
  const timeline = document.querySelector("#timeline");
  timeline.replaceChildren();
  if (!segments.length) {
    timeline.textContent = "No recordings have arrived yet.";
    return;
  }
  for (const segment of segments) {
    const row = document.createElement("div");
    row.className = "segment";
    const label = document.createElement("div");
    label.textContent = new Date(segment.started_at * 1000).toLocaleString();
    const actions = document.createElement("div");
    actions.className = "segment-actions";
    const play = document.createElement("a"); play.href = `/api/segments/${segment.id}/media`; play.textContent = "Play";
    const download = document.createElement("a"); download.href = `/api/segments/${segment.id}/export`; download.textContent = "Export";
    const remove = document.createElement("button"); remove.className = "secondary"; remove.textContent = "Delete"; remove.addEventListener("click", () => deleteSegment(segment.id));
    actions.append(play, download, remove); row.append(label, actions); timeline.append(row);
  }
}

document.querySelector("#login-form").addEventListener("submit", async event => {
  event.preventDefault();
  const response = await api("/api/login", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({username:document.querySelector("#username").value,password:document.querySelector("#password").value})});
  if (!response.ok) { document.querySelector("#login-error").textContent = "Sign-in failed."; return; }
  const result = await response.json(); csrfToken = result.csrf_token;
  const session = await api("/api/session"); await showDashboard(await session.json());
});
document.querySelector("#logout").addEventListener("click", async () => { await api("/api/logout", {method:"POST"}); csrfToken = null; showLogin(); });
document.querySelector("#logout-all").addEventListener("click", logoutAllDevices);
document.querySelector("#refresh").addEventListener("click", () => Promise.all([loadHealth(), loadTimeline()]));

(async () => {
  const response = await api("/api/session");
  if (response.ok) await showDashboard(await response.json()); else showLogin();
})();
