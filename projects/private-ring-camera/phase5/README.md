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
