# Private Ring-Style Camera

This project implements the `P040` initiative defined in [plans.md](plans.md). It is a local-first Raspberry Pi camera with an authenticated phone/laptop web application and a rolling 24-hour Mac archive.

## Verified hardware baseline

- Raspberry Pi 5 Model B, 4 GB
- Raspberry Pi OS Lite 64-bit
- Raspberry Pi Camera Module 3 / Sony IMX708 on CAM0
- Wi-Fi and SSH working independently of the direct Ethernet recovery link
- Camera enumerated as `imx708 [4608x2592 10-bit RGGB]`
- 1920×1080 still capture validated
- 1920×1080, 15 FPS MJPEG test stream captured and fully decoded
- H.264 is not currently available in the installed `rpicam-apps` build (`libav:0`); the encoder toolchain remains a Phase 1 prerequisite

Private Phase 0 media remains on the Pi under `~/edge-camera-phase0/` and is not committed.

Re-run the non-private Phase 0 capture check on the Pi:

```bash
rpicam-hello --list-cameras
mkdir -p "$HOME/edge-camera-phase0"
rpicam-still -n --immediate --width 1920 --height 1080 \
  -o "$HOME/edge-camera-phase0/phase0-still.jpg"
rpicam-vid -n -t 3000 --width 1920 --height 1080 --framerate 15 \
  --codec mjpeg -o "$HOME/edge-camera-phase0/phase0-video.mjpeg"
```

MJPEG is only the verified bring-up format. It is not the selected 24-hour archive format.

## Mac server development

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev,private-camera]'
```

Use a private data directory outside Git and iCloud. The default is:

```text
~/Library/Application Support/StratiosAI/edge-ai-camera/
```

Set an administrator password locally; it must contain at least 12 characters:

```bash
edge-camera-admin admin
```

For HTTP-only local development, explicitly disable secure cookies. This is not an approved household deployment configuration:

```bash
EDGE_CAMERA_SECURE_COOKIES=false \
EDGE_CAMERA_INGEST_TOKEN='replace-with-a-local-secret' \
edge-camera-server
```

The household deployment must put the service behind LAN/VPN HTTPS and leave secure cookies enabled.

## Implemented server boundaries

- Argon2 password verification
- Opaque, hashed server-side sessions with seven-day default expiry
- Strict, HTTP-only session cookie and CSRF protection
- Login throttling
- Log out and log out all devices
- Authenticated live-stream proxy boundary
- Authenticated timeline, media playback, and explicit export
- Confirmed deletion that removes media and metadata
- Raw authenticated Pi segment ingestion with SHA-256 integrity metadata
- Rolling retention operation and archive high-water protection
- Private filesystem permissions and no-store/security response headers

## Test

```bash
.venv/bin/ruff check .
.venv/bin/pytest
```

Synthetic bytes are used for API and retention tests. Real household media is never added to the test suite or Git.
