# Raspberry Pi Edge Vision Project and Capability Roadmap

This is a progressive checklist for learning computer vision and building complete edge systems with a Raspberry Pi. Begin with the Pi and camera already available. A HAT is optional until a measured limitation or new physical capability justifies one.

## How to use this roadmap

- Complete Stage 0 and Stage 1 first.
- Pick one application track rather than building every idea.
- Build with recorded media before depending on a live camera.
- Give every project an acceptance test, performance measurements, and documented limits.
- Treat `unknown` or `review required` as valid outputs. Never convert weak evidence into a pass.
- Training may run on a desktop or cloud GPU; deployment and end-to-end operation run on the Pi.

Capability labels:

- **A:** current Pi plus camera
- **B:** inexpensive peripheral such as light, button, USB microphone, or speaker
- **C:** specialized camera or sensor
- **D:** compatible HAT/AI accelerator
- **E:** desktop, home server, NAS, or cloud companion

## Stage 0 — device, Linux, and engineering foundation

- [ ] **P000 Hardware inventory `[A]`** — identify Pi model/RAM, OS, architecture, camera, storage, power, cooling, and network.
- [ ] **P001 Device report `[A]`** — run `scripts/device_report.py`; record temperature and camera commands.
- [ ] **P002 Python environment `[A]`** — virtual environment, package installation, linting, tests, config, and logging.
- [ ] **P003 Git workflow `[A]`** — issue, branch, small commit, test evidence, and model/data license notes.
- [ ] **P004 Linux service `[A]`** — run a harmless test app with `systemd`, restart on failure, and inspect logs.
- [ ] **P005 Edge telemetry `[A]`** — capture FPS, median/p95 latency, RAM, CPU, temperature, disk, and errors.
- [ ] **P006 Replay harness `[A]`** — process saved images/video identically to the live pipeline.
- [ ] **P007 Privacy baseline `[A]`** — retention limit, exclusion zones, recording indicator, and explicit upload action.

**Stage gate:** the Pi runs reliably for 30 minutes, reboots cleanly, and repeats a recorded test deterministically.

## Stage 1 — camera and classical computer vision

- [ ] **P010 Camera bring-up `[A]`** — preview, still, video, resolutions, frame rates, exposure, focus, and white balance.
- [ ] **P011 Picamera2 capture `[A]`** — low-resolution analysis stream plus high-resolution evidence capture.
- [ ] **P012 Image operations `[A]`** — color spaces, crop, resize, rotate, normalize, blur, sharpen, and histograms.
- [ ] **P013 Threshold/contours `[A]`** — binary/HSV thresholds, morphology, connected components, and contours.
- [ ] **P014 Edge/line detection `[A]`** — edges, line segments, circles, corners, and shape matching.
- [ ] **P015 Camera calibration `[A]`** — intrinsics, distortion correction, and reprojection error.
- [ ] **P016 Perspective mapping `[A]`** — map a fixed work surface into calibrated coordinates.
- [ ] **P017 Motion zones `[A]`** — background subtraction/frame differencing within allowed polygons.
- [ ] **P018 Camera health `[A]`** — detect darkness, glare, blur, blockage, frozen frames, and camera movement.
- [ ] **P019 Smart time-lapse `[A]`** — capture only meaningful change and build a daily summary.

**Stage gate:** create a tested motion event with a timestamp, region, confidence, thumbnail, and bounded storage.

## Stage 2 — basic machine vision inference

- [ ] **P020 Image classification `[A]`** — one label for the entire image.
- [ ] **P021 Multi-label classification `[A]`** — several properties such as gloves, helmet, and vest.
- [ ] **P022 Object detection `[A]`** — class, confidence, and bounding box.
- [ ] **P023 Custom detector `[A/E]`** — label and train for your parts, tools, products, or defects.
- [ ] **P024 Object tracking `[A]`** — maintain temporary track IDs across frames.
- [ ] **P025 Line crossing `[A]`** — count direction-specific crossings without double counting.
- [ ] **P026 Dwell/loiter event `[A]`** — require a track to remain inside a zone for a duration.
- [ ] **P027 Direction/speed estimate `[A]`** — use scene calibration and report uncertainty.
- [ ] **P028 Semantic segmentation `[A/E]`** — classify pixels as floor, road, wall, vegetation, or defect.
- [ ] **P029 Instance segmentation `[A/E]`** — separate the pixels of individual objects.
- [ ] **P030 Oriented detection `[A/E]`** — locate rotated parts with angled boxes.
- [ ] **P031 Keypoint detection `[A/E]`** — locate fasteners, landmarks, joints, or reference points.
- [ ] **P032 Optical flow `[A]`** — estimate motion without object identity.
- [ ] **P033 Visual embeddings `[A/E]`** — find similar objects/images by vector distance.
- [ ] **P034 Open-vocabulary query `[E]`** — use a companion model for classes outside a fixed detector.

**Stage gate:** benchmark at least two models on the actual Pi and camera, then explain the speed/accuracy tradeoff.

## Stage 3 — useful standalone projects without a HAT

### Home, property, nature, and monitoring

- [ ] **P040 Private Ring-style camera `[A/B/E]`** — motion/person event, clips, local API, phone PWA, authentication, home VPN, retention, and network-loss recovery.
- [ ] **P041 Package arrival/removal `[A]`** — detect package state changes in a porch zone.
- [ ] **P042 Garage-door state `[A]`** — open, closed, moving, and unknown states.
- [ ] **P043 Driveway/parking occupancy `[A]`** — arrival/departure and occupied/empty events.
- [ ] **P044 Pet door monitor `[A]`** — distinguish entry, exit, and lingering.
- [ ] **P045 Bird feeder counter `[A]`** — count visits rather than frames.
- [ ] **P046 Wildlife camera `[A]`** — motion-triggered clips and species classification.
- [ ] **P047 Plant growth monitor `[A]`** — aligned daily images and leaf/growth measurements.
- [ ] **P048 Anonymous room count `[A]`** — entry/exit tracking without identity storage.
- [ ] **P049 Local event search `[A/E]`** — filter events by time, zone, object, and confidence.

### Documents and instruments

- [ ] **P050 Document scanner `[A]`** — page detection, perspective correction, cleanup, and OCR.
- [ ] **P051 Barcode/QR workflow `[A]`** — load the correct part, recipe, or inventory record.
- [ ] **P052 Serial/label verification `[A]`** — OCR plus expected-pattern and checksum rules.
- [ ] **P053 Seven-segment display reader `[A]`** — read a device screen and reject impossible values.
- [ ] **P054 Analog gauge reader `[A]`** — detect dial/needle and convert angle to calibrated value.
- [ ] **P055 Before/after change report `[A/E]`** — align images and summarize meaningful changes.

**Stage gate:** deploy one project as a service with a replay test, bounded retention, health endpoint, and recovery procedure.

## Stage 4 — geometry, pose, faces, and spatial reasoning

- [ ] **P060 ArUco/AprilTag pose `[A]`** — marker ID, position, rotation, and approximate distance.
- [ ] **P061 Part alignment `[A]`** — shifted/rotated placement relative to a fixture.
- [ ] **P062 Dimension estimate `[A]`** — planar measurement using a calibrated reference.
- [ ] **P063 Fill-level estimate `[A]`** — percentage full with lighting/visibility quality checks.
- [ ] **P064 Gap-and-flush inspection `[A/C]`** — calibrated surface alignment measurement.
- [ ] **P065 Hand landmarks `[A/E]`** — finger keypoints and deliberate gesture controls.
- [ ] **P066 Body pose `[A/E]`** — joint positions for exercise or ergonomic feedback.
- [ ] **P067 Head orientation `[A/E]`** — coarse direction without claiming attention or intent.
- [ ] **P068 Face detection `[A]`** — locate and optionally blur faces without identity.
- [ ] **P069 Face landmarks/alignment `[A/E]`** — normalize consented faces for comparison.
- [ ] **P070 Facial embedding `[A/E]`** — create an encrypted biometric vector from a consented enrollment.
- [ ] **P071 1:1 face verification `[A/E]`** — claimed identity versus one enrolled template.
- [ ] **P072 1:N face recognition `[A/E]`** — gallery search with a required `unknown` result.
- [ ] **P073 Liveness experiment `[A/C/E]`** — measure photo/screen replay weaknesses; never claim security from a basic detector.
- [ ] **P074 Temporary person re-identification `[E]`** — privacy-limited cross-camera experiment without names.

**Biometric requirements:** informed consent, encrypted templates, deletion/export, audited enrollment, a non-biometric alternative, and measured false-accept/false-reject rates. Embeddings are sensitive biometric data.

## Stage 5 — industrial inspection and sequential logic

- [ ] **P080 Presence/absence inspection `[A]`** — verify every expected component location.
- [ ] **P081 Fastener inspection `[A/C]`** — absent, present, proud, flush, damaged, or uncertain.
- [ ] **P082 Surface defect inspection `[A/C/E]`** — scratch, crack, dent, chip, stain, or contamination.
- [ ] **P083 Color/finish verification `[A/B]`** — controlled lighting, reference target, and tolerance.
- [ ] **P084 Wrong-part prevention `[A]`** — detected part/label must match the active recipe.
- [ ] **P085 Tool-position verification `[A]`** — correct region and orientation before step advance.
- [ ] **P086 Ordered assembly `[A]`** — state machine proves steps in the allowed order.
- [ ] **P087 Grease-then-screw `[A/C]`** — observe visible grease application before screw/tool states.
- [ ] **P088 Screw-tool sequence `[A/C]`** — screw present, tool engaged, tool removed, visual completion.
- [ ] **P089 Multi-fastener coverage `[A]`** — all expected locations visited once or according to recipe.
- [ ] **P090 Pick-place confirmation `[A]`** — item leaves source and remains in the target fixture.
- [ ] **P091 Rework loop `[A]`** — failed step can return to a valid earlier state and be rechecked.
- [ ] **P092 Cycle-time analysis `[A]`** — per-step time, stalls, retries, and total cycle.
- [ ] **P093 Missing/out-of-order step `[A]`** — prevent completion when evidence is incomplete.
- [ ] **P094 Evidence bundle `[A/E]`** — decisive frames, event sequence, model/rule versions, and hashes.
- [ ] **P095 Sensor-fused verification `[B/C/D]`** — combine camera with torque, weight, pressure, PLC, or operator signal.

Example state machine:

```text
WAITING_FOR_PART
  -> PART_IDENTIFIED
  -> GREASE_OBSERVED
  -> SCREW_PRESENT
  -> TOOL_ENGAGED
  -> STEP_COMPLETE

low confidence | occlusion | wrong order | contradictory observation
  -> REVIEW_REQUIRED
```

A camera can observe grease-like appearance or tool engagement. It cannot prove hidden grease coverage, chemical composition, or exact torque. Use an appropriate sensor when the true requirement is not visually observable.

**Stage gate:** replay correct, missing-grease, missing-screw, wrong-order, occlusion, glare, rework, and camera-movement videos. Every known failure must fail or route to review—never pass.

## Stage 6 — anomaly detection and advanced quality

- [ ] **P100 Golden-image comparison `[A]`** — align a known-good image and calculate interpretable differences.
- [ ] **P101 One-class anomaly model `[A/E]`** — learn normal and flag unusual samples.
- [ ] **P102 Embedding-distance anomaly `[A/E]`** — compare parts to a normal reference distribution.
- [ ] **P103 Autoencoder anomaly map `[A/E]`** — train elsewhere and deploy reconstruction error.
- [ ] **P104 Patch-level localization `[A/E]`** — show which area caused the anomaly score.
- [ ] **P105 Process trend dashboard `[A/E]`** — defect type, score, size, location, and time trends.
- [ ] **P106 Camera/process drift separation `[A]`** — detect focus/lighting drift before blaming production.
- [ ] **P107 Human review queue `[A/E]`** — route uncertain samples for decisions and labels.
- [ ] **P108 Active-learning sampler `[A/E]`** — keep novel/diverse/low-confidence samples only.
- [ ] **P109 Model disagreement sampler `[E]`** — compare models/rules to find valuable examples.

## Stage 7 — model training, fine-tuning, and pruning

### Data and evaluation

- [ ] Define the operational requirement before selecting a model.
- [ ] Define labels, masks, keypoints, attributes, and `unknown/ambiguous` policy.
- [ ] Capture the real camera angle, lighting, distance, background, motion, occlusion, and failures.
- [ ] Include empty scenes, negatives, near misses, glare, blur, and rare conditions.
- [ ] Split train/validation/test by session, location, part, or person—not adjacent video frames.
- [ ] Version datasets and record ownership, consent, licenses, and retention.
- [ ] Report per-class precision/recall, confusion matrix, and operational false-pass/false-reject rates.

### Transfer learning and fine-tuning `[usually E]`

- [ ] Establish a pretrained baseline first.
- [ ] Train a new classification head while the backbone is frozen.
- [ ] Unfreeze selected later layers only if necessary.
- [ ] Fine-tune classification, detection, segmentation, pose, or embedding models.
- [ ] Use realistic augmentations; avoid transformations impossible in deployment.
- [ ] Track seed, dataset version, config, metrics, artifact hash, and license.
- [ ] Tune confidence/decision thresholds on validation data.
- [ ] Evaluate the untouched test set captured by the real Pi camera.

### Edge optimization

- [ ] Measure the unoptimized Pi baseline.
- [ ] Reduce input resolution, crop to regions, or reduce inference frequency.
- [ ] Try a smaller backbone/model family.
- [ ] Apply supported post-training quantization.
- [ ] Try quantization-aware training if accuracy drops too much.
- [ ] Apply **structured neural pruning** to remove channels/filters that runtimes can accelerate.
- [ ] Experiment carefully with unstructured sparsity; a smaller file does not guarantee faster inference.
- [ ] Fine-tune after pruning and re-evaluate.
- [ ] Distill a large teacher into a small student.
- [ ] Export to a Pi-compatible runtime and verify preprocessing/post-processing parity.
- [ ] Benchmark warm-up, median/p95 latency, FPS, RAM, CPU, temperature, and power.

### Decision-tree pruning and hybrid reasoning

- [ ] Train a shallow decision tree using detection and event features.
- [ ] Control maximum depth/minimum samples or apply cost-complexity pruning.
- [ ] Compare the pruned tree with deterministic domain rules.
- [ ] Keep safety and quality invariants in explicit rules, not only a learned tree.
- [ ] Version and test every tree/rule branch.

**Stage gate:** deploy an optimized model whose test metrics and Pi benchmarks are both documented, reproducible, and acceptable for the project.

## Stage 8 — voice, LLM, and multimodal systems

- [ ] **P120 Push-to-see description `[A/E]`** — explicitly select one frame for a VLM.
- [ ] **P121 Visual question answering `[A/E]`** — ask a grounded question about one frame.
- [ ] **P122 USB-microphone capture `[B]`** — record, quality-check, and transcribe a short utterance.
- [ ] **P123 Push-to-talk assistant `[B/E]`** — speech-to-text, LLM, and text/speech response.
- [ ] **P124 Voice-controlled camera `[B]`** — deliberate command triggers capture or event search.
- [ ] **P125 Spoken inspection helper `[B/E]`** — report current step and cite visual/sensor evidence.
- [ ] **P126 Manual-assisted repair `[A/E]`** — retrieve manual sections and combine them with a selected image.
- [ ] **P127 Event summarizer `[A/E]`** — LLM summarizes structured events, not continuous private video.
- [ ] **P128 Visual inventory assistant `[A/E]`** — reconcile detections with a local inventory after approval.
- [ ] **P129 Natural-language rule draft `[E]`** — turn instructions into reviewable state-machine config, never direct uncontrolled actuation.
- [ ] **P130 Local-first multimodal assistant `[B/D/E]`** — local trigger and perception with LAN/cloud fallback.

## Stage 9 — specialized cameras, sensors, robotics, and HATs

- [ ] **P140 Low-light/NoIR vision `[C]`** — evaluate illumination, exposure, motion blur, and privacy.
- [ ] **P141 Global-shutter motion `[C]`** — fast objects, conveyors, wheels, and reduced rolling-shutter distortion.
- [ ] **P142 HQ macro/telephoto inspection `[C]`** — select lens, focus, working distance, depth of field, and lighting.
- [ ] **P143 Stereo/depth project `[C/E]`** — depth map, obstacle distance, or 3D measurement.
- [ ] **P144 Thermal fusion `[C/E]`** — align visible and thermal images and state limitations.
- [ ] **P145 Sensor-fusion event `[B/C/D]`** — camera plus PIR, ultrasonic, weight, temperature, or environmental sensor.
- [ ] **P146 Pan/tilt tracker `[B/D]`** — safe servo power, limits, manual stop, and loss-of-target behavior.
- [ ] **P147 Mobile robot perception `[B/C/D]`** — mapping/obstacle research with independent safety control.
- [ ] **P148 AI Camera deployment `[C]`** — supported on-sensor inference and Pi post-processing.
- [ ] **P149 AI accelerator deployment `[D]`** — convert a supported model and compare CPU versus NPU end-to-end performance.
- [ ] **P150 Pi-local generative AI `[D]`** — only with compatible hardware/runtime; compare with a LAN server.

## Production architecture checklists

### Private camera, server, phone app, and home VPN

- [ ] Pi captures an analysis stream and circular pre-event buffer.
- [ ] Motion/person logic opens and closes an event.
- [ ] Short clips and thumbnails are encrypted or access-controlled locally.
- [ ] Local API exposes live view, events, health, and retention controls.
- [ ] Responsive PWA works on a phone without an app-store deployment.
- [ ] Authentication is required even on the home LAN.
- [ ] Remote access uses a home VPN; camera ports are not exposed directly to the internet.
- [ ] Notification metadata is minimal and links to the VPN-protected app.
- [ ] Privacy zones, recording indicator, quiet hours, export, and verified deletion work.
- [ ] Network loss preserves local capture; disk limits prevent storage exhaustion.
- [ ] Two-way audio is added only after microphone, speaker, and echo tests.

**Acceptance:** over the VPN, use the phone to view live video, open a real event, play its clip, delete it, and verify removal from storage.

### Sequential assembly inspector

- [ ] Define bill of process, expected parts, locations, order, tolerances, and evidence.
- [ ] Fix camera, lens, focus, lighting, distance, and fixture position.
- [ ] Use a recipe per component variant.
- [ ] Separate detectors from temporal state-machine rules.
- [ ] Debounce observations across frames and handle occlusion explicitly.
- [ ] Preserve pass, fail, and review-required results.
- [ ] Save decisive evidence with model/rule versions.
- [ ] Fuse torque/PLC/sensor evidence when vision cannot prove the requirement.
- [ ] Measure false passes independently from false rejects.

## Hardware upgrade decision table

| Measured need | Try first | Upgrade only if still needed |
|---|---|---|
| Dark/noisy image | Controlled lighting and exposure | NoIR/IR or better camera/lens |
| Blurry fast motion | More light and shorter exposure | Global Shutter Camera |
| Tiny details | Fixed mount, closer view, crop | HQ camera and suitable lens |
| Depth/distance | Calibration and reference markers | Depth/stereo/ranging sensor |
| CPU inference slow | Smaller model, crop, lower FPS, quantize | Compatible AI HAT/accelerator |
| Large LLM/VLM slow | Use a LAN workstation/server | Compatible generative-AI accelerator |
| No audio input | USB microphone | Microphone array/audio HAT |
| Camera must move | Fixed camera/digital crop | Servo driver or motor HAT |
| Need extra context | Single GPIO/I2C sensor | Sensor HAT |

Verify exact Pi compatibility, power, cooling, model operators, conversion workflow, memory, and measured end-to-end performance before buying a HAT.

## Project folder template

Create one folder per deployable system:

```text
projects/<project-id>/
├── README.md
├── app/
├── configs/
├── tests/
│   ├── unit/
│   ├── replay/
│   └── acceptance/
├── samples/
├── models/
│   ├── manifest.yaml
│   └── download_model.sh
├── containers/
│   ├── Dockerfile.pi
│   ├── Dockerfile.server
│   └── compose.yaml
├── infra/
│   ├── ansible/
│   ├── systemd/
│   ├── terraform/
│   └── vpn/
├── web/
└── docs/
    ├── architecture.md
    ├── privacy-and-threat-model.md
    ├── runbook.md
    └── results.md
```

Do not commit model binaries, private captures, biometric data, VPN keys, certificates, credentials, or generated databases. Commit manifests, checksums, licenses, synthetic samples, and repeatable download/build instructions.

## Recommended first ten builds

- [ ] 1. P000 hardware inventory
- [ ] 2. P010 camera bring-up
- [ ] 3. P018 camera health
- [ ] 4. P017 motion zones
- [ ] 5. P022 general object detection
- [ ] 6. P024 tracking plus P025 line crossing
- [ ] 7. P060 marker position/orientation
- [ ] 8. P080 part presence/absence
- [ ] 9. P086 two-step ordered state machine using replay video
- [ ] 10. P121 visual question answering on one selected frame

Then specialize in private home cameras, industrial inspection, facial/pose systems, nature, robotics, or multimodal assistants.

## Current official references

- [Raspberry Pi camera software and rpicam applications](https://www.raspberrypi.com/documentation/computers/camera_software.html)
- [Picamera2 manual](https://datasheets.raspberrypi.com/camera/picamera2-manual.pdf)
- [Raspberry Pi AI software](https://www.raspberrypi.com/documentation/computers/ai.html)
- [Raspberry Pi AI HATs](https://www.raspberrypi.com/documentation/accessories/ai-hat-plus.html)
- [Raspberry Pi AI Camera](https://www.raspberrypi.com/documentation/accessories/ai-camera.html)
- [TensorFlow Model Optimization pruning](https://www.tensorflow.org/model_optimization/guide/pruning)
- [TensorFlow Model Optimization quantization-aware training](https://www.tensorflow.org/model_optimization/guide/quantization/training)
