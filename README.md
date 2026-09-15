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
├── .env.example                # Variable names only; never secrets
└── pyproject.toml
```

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

## Near-term definition of done

The first milestone is complete when the Pi captures one image, saves it under `data/captures/`, records device information, and can repeat the process from a documented command. No HAT, cloud service, or paid API is required.

