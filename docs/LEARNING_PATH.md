# Learning Path

## Project 00: device and camera check

Goal: identify the Pi, OS, Python version, memory, storage, temperature support, and camera availability.

Success evidence:

- `python scripts/device_report.py` completes.
- The camera preview works.
- One still image is saved locally.

## Project 01: motion detector

Goal: compare frames and save an event only when motion exceeds a configured threshold.

Learn: image arrays, frame rate, thresholds, false positives, event logs.

## Project 02: object detector

Goal: detect a small set of common objects using a lightweight model.

Learn: model formats, preprocessing, confidence thresholds, inference time, CPU load.

Gate before buying hardware: record frames per second, latency, memory, and temperature. Buy an accelerator only if those measurements show the Pi misses a real requirement.

## Project 03: scene describer

Goal: capture one user-requested frame and ask a multimodal model to describe it.

Learn: image resizing, API/LAN calls, structured prompts, privacy boundaries, cost controls.

## Project 04: voice assistant

Goal: capture a short spoken question, transcribe it, call an LLM, and speak or print the result.

Additional hardware: a USB microphone is the simplest starting point if your current setup has no audio input. Audio output can use HDMI, USB, or Bluetooth depending on your Pi.

## Project 05: multimodal assistant

Goal: ask a spoken question about a user-selected camera frame and receive an answer.

Keep the first version push-to-talk and push-to-see. Continuous recording and automatic uploads add privacy and reliability problems before they add learning value.

