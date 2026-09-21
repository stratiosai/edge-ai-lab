# Phase 5 — Person and vehicle intelligence

Phase 5 begins only after the continuous recording path is stable. The first
goal is an auditable **event suggestion** pipeline, not an alarm system:

1. Sample the live/analysis stream inside configured motion zones.
2. Run a small detector only when motion is present.
3. Track a detected object for a short lifetime so one car is not counted in
   every frame.
4. Emit an event with class, confidence, zone, direction, and timestamps.
5. Keep the original H.264 recording unchanged; boxes belong in the UI and
   event thumbnails only.

## Current hardware boundary

The Pi 5 currently has no computer-vision Python runtime installed. Do not
install a large training stack on the Pi. Export or convert models on the Mac,
copy only the runtime model and labels to the Pi, and benchmark there.

The first benchmark candidates are two small COCO detectors:

- `yolo26n` — the speed/latency baseline.
- `yolo26s` — the accuracy/CPU trade-off candidate.

For the Pi, compare CPU LiteRT/NCNN inference at 320px and 416px input sizes.
Ultralytics documents Raspberry Pi deployment and notes that LiteRT export is
performed on macOS or x86_64 Linux, then the exported model is copied to the
Pi. Keep the exact model checksum and export settings beside every benchmark.

## Acceptance measurements

Record, for each candidate and input size:

- median and p95 inference latency;
- sustained frames per second over a five-minute run;
- CPU, memory, temperature, and throttling state;
- person/car/truck/bus/motorcycle precision and recall on a small labeled test
  set from the controlled camera area;
- duplicate-count rate when one object remains in view;
- false alerts from shadows, glare, rain, darkness, and partial occlusion.

Do not enable notifications or automatic actions until these measurements are
reviewed. Preserve an `unknown` result when confidence is weak.

## Mac model baseline (2026-09-21)

The existing Mac virtualenv ran both candidate models against one representative
640×360 frame extracted from the private archive (the frame and model files are
outside Git). At 320px input and CPU inference, `yolo26n` measured 7.53 ms
median / 8.07 ms p95 over 10 iterations; `yolo26s` measured 12.06 ms median /
12.52 ms p95. These are tooling sanity checks, not Pi acceptance evidence:
both models still require a real Pi benchmark with thermal and throttling
measurements before any detector is deployed.

The first real Pi CPU benchmark completed on 2026-09-21 using a user-owned
virtualenv with ONNX Runtime and a frame decoded from an active Pi camera
segment. At 320px input, `yolo26n` measured 64.0 ms median / 103.2 ms p95
(about 14.2 FPS); `yolo26s` measured 274.3 ms median / 307.1 ms p95 (about
3.6 FPS). The Pi reached 65.6°C with `throttled=0x0`. These are latency
baselines only: the scene contained a person and no vehicles, so they do not
establish counting accuracy.

The repeatable runner is [`benchmark_onnx.py`](benchmark_onnx.py). Keep its
JSON output and all model files in the private camera data directory, not Git.

A five-minute sustained CPU run of `yolo26n` completed on the Pi on 2026-09-21
(4,700 iterations): 14.1 FPS average, 63.8 ms median / 120.3 ms p95, 70.5°C
reported at both endpoints, and `throttled=0x0`. The Pi capture, live, and
archive-agent services remained active and its bounded buffer remained at two
files. This validates a sustained speed/thermal baseline, not event accuracy.

## Controlled indoor accuracy baseline (2026-09-21)

The private labeling sample contains 12 manually reviewed frames from one
controlled indoor segment. It has 14 labeled person instances. At the
`yolo26n` model and 0.45 confidence threshold, the evaluator measured 14 true
positive matches, 0 false positives, 0 false negatives, and 0 duplicate
predictions. The duplicate metric was corrected to allow multiple labeled
objects of the same class in one frame. Precision and recall are therefore
1.00 for this sample, but the single indoor condition is not an acceptance gate;
day/night/weather/occlusion coverage and temporal duplicate-count evaluation
remain required before enabling unattended detection.

## Real-Pi guarded canary (2026-09-21)

The Phase 5 dependencies were copied to the Pi with matching SHA-256 hashes,
then one closed segment was copied to a temporary file and replayed locally
with `yolo26n` at 1 FPS and a 0.45 confidence threshold. The no-upload run
produced two `person` event suggestions at 0.567 and 0.491 confidence in the
`controlled-test-area` zone. The source segment and the active systemd
services were left untouched; the normal archive agent still does not pass
`--enable-detector`.

## Tracking primitive

[`tracking.py`](../../../src/stratios_edge_ai/private_camera/tracking.py)
contains the first deterministic tracking primitive. It matches detections of
the same class by greedy highest intersection-over-union (IoU), confirms a
track after `min_hits`, ages it through short detector gaps, and emits one
counting candidate when a track first becomes confirmed. Expired tracks can be
counted again when a genuinely new object enters. The implementation is
camera-local and has no notification or actuator side effects; crossing-line
direction and live-service integration are the next steps.

[`crossing.py`](../../../src/stratios_edge_ai/private_camera/crossing.py) adds
the next deterministic primitive: a normalized directed line, configurable
jitter deadband, and one `a-to-b`/`b-to-a` event per track. State can be reset
when the IoU tracker expires a track, so a later re-entry is countable. This
is event logic only; it is not yet connected to the live detector or UI.

[`events.py`](../../../src/stratios_edge_ai/private_camera/events.py) defines
the review metadata contract used by the eventual authenticated event view:
class, confidence, zone, count, optional direction, source segment, thumbnail,
and a bounded clip window. Pixel crops are clamped to the source frame and
invalid confidence or clip ranges are rejected. Persistence, clip extraction,
and UI display still require live detector wiring and measured accuracy.

The Mac archive now persists these suggestions in its private SQLite database.
The Pi-facing `POST /api/ingest/event` endpoint is ingest-token protected and
idempotent by event ID; the authenticated `GET /api/events` endpoint returns
only the configured retention window. This is metadata plumbing, not proof of
detection accuracy or a notification trigger.
When an event references a retained segment, the authenticated
`/api/events/{event_id}/thumbnail` route can extract a 480px review frame into
the owner-only event directory. Missing media or ffmpeg fails closed and never
changes the source recording.
The authenticated `/api/events/{event_id}/clip` route similarly extracts a
bounded MP4 review window from the referenced segment, clamped to that
segment's start/end times and written with owner-only permissions.
When a source segment is deleted or expires, its event rows and any derived
thumbnail/clip files are removed in the same archive operation; no orphaned
event metadata remains after retention.

[`detector.py`](../../../src/stratios_edge_ai/private_camera/detector.py) is
the Pi-safe ONNX Runtime adapter. It parses the exported NMS rows, normalizes
boxes, filters target classes/confidence, and applies enabled motion zones
before handing detections to the tracker. It has no default camera loop or
network side effect; deployment remains gated on labeled accuracy checks.
With `emit_unknown` enabled, weak or unmapped rows are retained as `unknown`
instead of being assigned a person/vehicle class; unknowns are excluded from
counts until reviewed.

[`metrics.py`](../../../src/stratios_edge_ai/private_camera/metrics.py) provides
the labeled-frame gate: same-class IoU matching, aggregate precision/recall,
and duplicate-prediction counts. Feed it annotations from the controlled test
area; synthetic unit tests do not prove camera accuracy.

[`overlay.py`](../../../src/stratios_edge_ai/private_camera/overlay.py) renders
counts, track IDs, confidence, and boxes onto a derived BGR frame. It copies
the input first, so the original recording/evidence frame is never modified;
connecting this renderer to a live analysis stream remains gated on accuracy.

[`pipeline.py`](../../../src/stratios_edge_ai/private_camera/pipeline.py)
composes the motion gate, detector adapter callback, tracker, optional crossing
line, and `EventSuggestion` output. Quiet frames skip detector inference;
confirmed tracks produce metadata only. It has no camera, network, or
notification side effects until explicitly wired into a service.

[`replay_segment.py`](replay_segment.py) is the safe first integration path:
it replays one selected archived MP4 through the pipeline and writes event JSON
to a caller-selected private directory. It does not modify recordings or send
events over the network, making it suitable for accuracy review before an
always-on Pi service. Pass the archive's `--segment-id` when available so the
resulting event records remain source-linked for later thumbnail/clip ingest.

The Pi archive agent now has a guarded live hook. It remains disabled unless
both `--enable-detector` and `--detector-model /path/to/model.onnx` are passed;
when enabled, it analyzes each closed segment after archival and submits only
source-linked review events. The normal systemd service does not pass either
flag, so this hook must not be enabled until the labeled accuracy and
environment checks below are accepted. It never sends notifications and never
rewrites the original recording.

The Pi MJPEG relay also has a separate live-only overlay gate. Passing
`--enable-overlay --overlay-model /path/to/model.onnx` draws sampled boxes,
track IDs, and counts on the browser stream while leaving archived MP4s
untouched. The normal `edge-camera-live` service does not pass these flags;
the CLI refuses to enable them without an explicit model. The default
`--overlay-motion-threshold 5.0` keeps inference motion-gated; a zero threshold
is reserved for a controlled renderer canary, not unattended deployment.

[`render_proof_video.py`](render_proof_video.py) creates a short H.264 review
clip from a selected private segment with detector boxes, confidence, stable
track IDs, counts, and zone text. The proof clip is generated outside Git;
the source segment is never overwritten.

[`create_label_manifest.py`](create_label_manifest.py) extracts evenly spaced
JPEG review frames and writes a private `labels.json` template. Fill in each
frame's condition and ground-truth `objects` before running the accuracy
evaluator; an empty template is intentionally not an accuracy result.

[`predict_manifest.py`](predict_manifest.py) writes a separate private
`predictions.json` sidecar with model suggestions and normalized boxes. It is
review assistance only; never copy its predictions into ground truth without
checking the frame.

Run [`evaluate_accuracy.py`](evaluate_accuracy.py) on a private manifest when
frames are labeled. Keep that manifest, frames, model binaries, and JSON
results outside Git. The command reports aggregate and per-frame counts so the
day/night/weather gate can be reviewed before enabling a detector service.

[`evaluate_environment.py`](evaluate_environment.py) is the acceptance wrapper:
it requires separate labeled manifests for daylight, darkness, rain, glare,
shadows, and occlusion, reports each condition independently, and exits with a
non-zero status unless every condition meets the configured precision, recall,
and duplicate limits. A controlled-indoor manifest alone is intentionally
rejected as incomplete. The wrapper was exercised against the current sample
on 2026-09-21 and exited with status 2, naming the missing darkness, rain,
glare, shadows, and occlusion manifests; it cannot silently promote a
single-condition sample to environmental acceptance.

## Reproducible run records

Each run should keep a text manifest outside Git containing:

```text
model_name=
model_sha256=
format=
input_size=
confidence_threshold=
zone_config_sha256=
git_revision=
started_at_utc=
duration_seconds=
median_latency_ms=
p95_latency_ms=
avg_fps=
temperature_start_c=
temperature_end_c=
throttled=
```

Never commit captured household frames, model binaries, credentials, or
biometric data.
