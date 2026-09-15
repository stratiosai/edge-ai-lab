# StratiosAI Edge AI Lab

A Raspberry Pi learning lab for computer vision, voice, local language models, and multimodal AI.

This repository is deliberately a **monorepo**: each experiment is small and independent, while camera, audio, model-client, and device utilities are shared. Start with the hardware you already own—a Raspberry Pi and camera. A HAT is not required for the first projects.

## What you can build without a HAT

- Camera preview, still-image capture, and time-lapse photography
- Motion detection and object detection
- Image descriptions using a cloud or LAN-hosted multimodal model
- Push-to-talk voice commands using a USB microphone or Bluetooth headset later
- Text-to-speech through HDMI, USB audio, Bluetooth, or the Pi audio output (model-dependent)
- A multimodal assistant that sees a frame, accepts a question, and speaks or prints an answer
- GPIO experiments using individual sensors later (with safe wiring), without committing to a HAT

A HAT is an expansion board, not a prerequisite. It becomes useful only when a project needs specialized microphones, motor control, power management, sensors, or accelerators.

## Capability roadmap

The full checklist is in [project-capability-roadmap.md](project-capability-roadmap.md). It covers:

- Camera and OpenCV fundamentals
- Motion, classification, detection, tracking, and segmentation
- Position, pose, facial embeddings, and consent-based recognition
- Ring-style private home cameras with a server, phone app, and VPN
- Industrial inspection and sequential logic such as `grease -> screw -> tool -> complete`
- OCR, anomaly detection, quality inspection, robotics, voice, LLMs, and multimodal systems
- Data collection, fine-tuning, quantization, neural-network pruning, decision-tree pruning, distillation, and edge deployment
- Optional camera, sensor, audio, motor, and AI HAT upgrades

## Recommended learning path

1. **Camera bring-up** — prove the camera works and save an image.
2. **Motion detection** — learn frames, thresholds, events, and logging.
3. **Object detection** — run a small model and measure speed on your Pi.
4. **Vision-language description** — send a selected image to a multimodal model; do not stream everything.
5. **Voice input/output** — add a USB microphone and speaker only when ready.
6. **Multimodal assistant** — combine camera, speech-to-text, an LLM/VLM, and text-to-speech.

See [docs/LEARNING_PATH.md](docs/LEARNING_PATH.md) for project gates and [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the system layout.

## Repository layout

```text
.
├── apps/                       # Runnable end-to-end experiments
│   ├── camera_check/
│   ├── motion_detector/
│   ├── object_detector/
│   ├── scene_describer/
│   └── multimodal_assistant/
├── src/stratios_edge_ai/       # Reusable Python package
│   ├── camera/
│   ├── audio/
│   ├── inference/
│   └── telemetry/
├── configs/                    # Safe, committed example configuration
├── data/                       # Local inputs/outputs; contents ignored
├── docs/                       # Architecture, hardware, setup, privacy
├── scripts/                    # Device setup and diagnostics
├── tests/
├── project-capability-roadmap.md
├── .env.example                # Variable names only; never secrets
└── pyproject.toml
```

As projects become real deployments, give each one a self-contained folder:

```text
projects/<project-id>/
├── README.md                   # Goal, hardware, setup, limits, acceptance test
├── app/                        # Project-specific Python/service code
├── configs/                    # Safe examples, thresholds, regions, recipes
├── tests/                      # Unit, replay, integration, acceptance tests
├── samples/                    # Small synthetic/non-private test inputs
├── models/                     # Manifests and download scripts, not large binaries
├── containers/
│   ├── Dockerfile.pi           # ARM64 edge image
│   ├── Dockerfile.server       # Optional home/LAN server
│   └── compose.yaml            # Pi, API, database, UI, monitoring as needed
├── infra/
│   ├── ansible/                # Repeatable Pi/server configuration
│   ├── systemd/                # Native Pi service definitions
│   ├── terraform/              # Optional remote infrastructure
│   └── vpn/                    # Documentation/config templates; never keys
├── web/                        # Phone-friendly PWA or operator console
└── docs/                       # Architecture, threat model, runbook, results
```

Shared camera, audio, inference, tracking, telemetry, and event components stay under `src/stratios_edge_ai/`. Project folders compose them instead of copying them.

## First setup

Use Raspberry Pi OS 64-bit. Camera setup depends on the Pi and camera model, so record both in `docs/HARDWARE.md` before installing project-specific packages.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'
python scripts/device_report.py
```

On the Pi, first verify the camera with the Raspberry Pi camera tools available in your OS image (commonly `rpicam-hello` and `rpicam-still`). Then implement `apps/camera_check` using Picamera2.

## Design rules

- Each app must have one clear input, output, and success check.
- Keep model providers behind interfaces in `src/stratios_edge_ai/inference`.
- Store secrets only in an untracked `.env` or secret manager.
- Keep captured media local by default. Upload only a user-selected frame.
- Log performance data, not private image/audio content.
- Prefer small models on the Pi; use a desktop or cloud API for large multimodal models.
- Measure latency, memory, CPU temperature, and accuracy before buying accelerators.
- Separate perception from decisions: “screw detected” is an observation, not proof that the assembly passed.
- Use state machines for ordered processes and retain an `unknown/review` outcome.
- Train large models elsewhere when necessary; optimize and deploy the inference artifact to the Pi.
- Keep safety-critical actuation outside experimental vision code.

## Near-term definition of done

The first milestone is complete when the Pi captures one image, saves it under `data/captures/`, records device information, and can repeat the process from a documented command. No HAT, cloud service, or paid API is required.
