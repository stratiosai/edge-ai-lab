let csrfToken = null;
let allSegments = [];

function toLocalInputValue(epochSeconds) {
  const date = new Date(epochSeconds * 1000);
  const offset = date.getTimezoneOffset() * 60000;
  return new Date(date.getTime() - offset).toISOString().slice(0, 16);
}

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
  allSegments = segments;
  if (segments.length) {
    const starts = segments.map(segment => segment.started_at);
    const ends = segments.map(segment => segment.ended_at);
    document.querySelector("#export-start").value = toLocalInputValue(Math.min(...starts));
    document.querySelector("#export-end").value = toLocalInputValue(Math.max(...ends));
  }
  populateScrubber();
  document.querySelector("#recordings-summary").textContent = `${segments.length} recording${segments.length === 1 ? "" : "s"} available locally`;
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

function localDay(segment) {
  return new Date(segment.started_at * 1000).toLocaleDateString(undefined, {weekday: "short", month: "short", day: "numeric"});
}

function segmentsForSelectedDay() {
  const day = document.querySelector("#recording-day").value;
  return allSegments.filter(segment => localDay(segment) === day).sort((a, b) => a.started_at - b.started_at);
}

function renderScrubberSelection() {
  const slider = document.querySelector("#recording-slider");
  const selections = segmentsForSelectedDay();
  const segment = selections[Number(slider.value)];
  const image = document.querySelector("#scrubber-thumbnail");
  const empty = document.querySelector("#scrubber-empty");
  const time = document.querySelector("#scrubber-time");
  const position = document.querySelector("#scrubber-position");
  const play = document.querySelector("#scrubber-play");
  const previous = document.querySelector("#scrubber-previous");
  const next = document.querySelector("#scrubber-next");
  const rail = document.querySelector(".time-rail");
  if (!segment) {
    image.removeAttribute("src"); image.hidden = true; empty.hidden = false;
    time.textContent = "No recordings for this day"; position.textContent = ""; play.href = "#";
    previous.disabled = true; next.disabled = true;
    rail.style.setProperty("--thumb-position", "0");
    return;
  }
  const date = new Date(segment.started_at * 1000);
  time.textContent = date.toLocaleString(undefined, {weekday: "short", month: "short", day: "numeric", hour: "numeric", minute: "2-digit", second: "2-digit"});
  position.textContent = `Recording ${Number(slider.value) + 1} of ${selections.length}`;
  play.href = `/api/segments/${segment.id}/media`;
  previous.disabled = Number(slider.value) === 0;
  next.disabled = Number(slider.value) === selections.length - 1;
  rail.style.setProperty("--thumb-position", selections.length > 1 ? String((Number(slider.value) / (selections.length - 1)) * 100) : "0");
  image.hidden = false; empty.hidden = true;
  image.src = `/api/segments/${segment.id}/thumbnail?cache=${segment.id}`;
  image.onerror = () => { image.hidden = true; empty.hidden = false; };
}

function populateScrubber() {
  const daySelect = document.querySelector("#recording-day");
  const current = daySelect.value;
  const days = [...new Set(allSegments.map(localDay))];
  daySelect.replaceChildren(...days.map(day => new Option(day, day)));
  if (days.includes(current)) daySelect.value = current;
  const selections = segmentsForSelectedDay();
  const slider = document.querySelector("#recording-slider");
  slider.max = Math.max(0, selections.length - 1);
  slider.value = Math.min(Number(slider.value), Number(slider.max));
  const markers = document.querySelector("#segment-markers");
  markers.replaceChildren(...selections.map((_, index) => {
    const marker = document.createElement("span");
    marker.className = "segment-marker";
    if (index === Number(slider.value)) marker.classList.add("selected");
    return marker;
  }));
  renderScrubberSelection();
}

function stepScrubber(direction) {
  const slider = document.querySelector("#recording-slider");
  slider.value = Math.max(0, Math.min(Number(slider.max), Number(slider.value) + direction));
  renderScrubberSelection();
  document.querySelectorAll(".segment-marker").forEach((marker, index) => marker.classList.toggle("selected", index === Number(slider.value)));
}

function setRecordingView(view) {
  const isList = view === "list";
  document.querySelector("#list-view").hidden = !isList;
  document.querySelector("#scrubber-view").hidden = isList;
  for (const button of document.querySelectorAll(".view-tab")) {
    const selected = button.id === `${view}-view-button`;
    button.classList.toggle("active", selected); button.setAttribute("aria-selected", String(selected));
  }
  if (!isList) renderScrubberSelection();
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
document.querySelector("#list-view-button").addEventListener("click", () => setRecordingView("list"));
document.querySelector("#scrubber-view-button").addEventListener("click", () => setRecordingView("scrubber"));
document.querySelector("#recording-day").addEventListener("change", () => { document.querySelector("#recording-slider").value = 0; populateScrubber(); });
document.querySelector("#recording-slider").addEventListener("input", () => stepScrubber(0));
document.querySelector("#scrubber-previous").addEventListener("click", () => stepScrubber(-1));
document.querySelector("#scrubber-next").addEventListener("click", () => stepScrubber(1));
document.querySelector("#range-export").addEventListener("submit", event => {
  event.preventDefault();
  const start = new Date(document.querySelector("#export-start").value).getTime() / 1000;
  const end = new Date(document.querySelector("#export-end").value).getTime() / 1000;
  if (!Number.isFinite(start) || !Number.isFinite(end) || start >= end) {
    alert("Choose a valid start and end time.");
    return;
  }
  window.location.assign(`/api/segments/export?since=${Math.floor(start)}&until=${Math.ceil(end)}`);
});

(async () => {
  const response = await api("/api/session");
  if (response.ok) await showDashboard(await response.json()); else showLogin();
})();
