# Hardware Inventory

Verified on the live edge device on 2026-09-19. Unknown items remain explicit rather than inferred.

| Item | Current value |
|---|---|
| Raspberry Pi model | Raspberry Pi 5 Model B Rev 1.1 |
| RAM | 4 GB |
| Raspberry Pi OS version | Raspberry Pi OS Lite 64-bit; Debian 13 (Trixie) |
| Architecture (32/64-bit) | ARM64 / `aarch64` |
| Camera model | Raspberry Pi Camera Module 3 / Sony IMX708, 4608×2592, autofocus |
| Camera connector/cable | Pi 5 CAM/DISP0 (`cam0`); explicit `dtoverlay=imx708,cam0` required on this installation |
| Storage type and size | 32 GB boot media; approximately 26 GB free after initial setup |
| Power supply rating | Unknown |
| Cooling | Unknown |
| Microphone | No capture device detected; audio is excluded from private-camera V1 |
| Speaker/audio output | Unknown |
| Network connection | Home Wi-Fi at `192.168.0.65`; direct Ethernet retained as recovery path |

## Camera acceptance evidence

- `rpicam-hello --list-cameras` enumerated IMX708 after a reboot.
- A 1920×1080 JPEG still was captured and decoded successfully.
- A 1920×1080, 15 FPS MJPEG test stream captured 37 frames and decoded end to end.
- Temperature after capture was 48.3°C and `get_throttled=0x0`.
- The installed `rpicam-apps-lite` build reports `libav:0` and no H.264 encoder; the full official encoder toolchain is required for the planned H.264 profile.

Private acceptance media remains on the Pi under `~/edge-camera-phase0/` and is excluded from Git.

## Sensible next purchases—only when a project needs them

1. Correct official-quality power supply and basic cooling, if missing.
2. USB microphone for voice experiments.
3. Speaker or USB audio device if HDMI/Bluetooth audio is unsuitable.
4. Breadboard, jumper wires, LEDs, resistors, and buttons for basic GPIO learning.
5. Accelerator or HAT only after performance measurements identify a bottleneck.
