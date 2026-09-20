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
- H.264 / FFmpeg toolchain installed and verified with a real 1920×1080, 15 FPS, ~2.51 Mbps recording

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

MJPEG is only used for the lower-resolution live view. The 24-hour archive uses H.264 MP4 segments.

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
- Token-protected Pi MJPEG relay, proxied through the authenticated Mac API
- Rolling retention operation and archive high-water protection
- Private filesystem permissions and no-store/security response headers

## Test

```bash
.venv/bin/ruff check .
.venv/bin/pytest
```

Synthetic bytes are used for API and retention tests. Real household media is never added to the test suite or Git.

## Soak monitoring

Use the frame-free monitor to collect service, buffer, temperature, and
throttling evidence during the two-hour acceptance test. Store its output in
the private camera data directory, not the repository:

```sh
projects/private-ring-camera/scripts/monitor_pi_soak.sh \
  "$HOME/.ssh/post_proof_pi_ed25519" stratiosai@192.168.0.65 7200 300 \
  "$HOME/Library/Application Support/StratiosAI/edge-ai-camera/soak/pi-$(date +%Y%m%d-%H%M%S).log"
```

## Deployment boundary

The Pi capture, live relay, and archive uploader run as user `systemd` services. Before enabling or changing them, confirm that the camera faces the agreed controlled indoor test area and excludes bedrooms, bathrooms, screens, private paperwork, and non-consenting people. The administrator command `loginctl enable-linger stratiosai` is still required once for service start after a Pi reboot without an interactive user login.

The deployment uses a device-only local TLS certificate: the Pi trusts the local CA for uploads, and each household phone must trust that CA before its browser can use the secure-cookie application. No port forwarding or public exposure is used. The reproducible service templates are under [infra](infra); credentials, generated certificates, media, and launchd copies remain outside Git.
