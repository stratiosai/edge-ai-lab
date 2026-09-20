# Pi user-service deployment

These units keep all camera secrets in `~/edge-camera-secrets`, outside Git.
They are usable without changing the Pi system directories. Install the three
units in `~/.config/systemd/user/` and create a mode-600
`~/edge-camera-secrets/pi-agent.env` containing only:

```ini
EDGE_CAMERA_BUFFER_DIR=/home/stratiosai/edge-camera-buffer
EDGE_CAMERA_LIVE_FIFO=/home/stratiosai/edge-camera-live/live.mjpg.fifo
EDGE_CAMERA_SERVER_URL=https://your-mac-hostname.local:8443
```

Run `systemctl --user daemon-reload`, then enable all three units. For restart
persistence after logout and Pi reboot, an administrator must run
`loginctl enable-linger stratiosai` once. Do not put tokens or private keys in
this file; each unit references the private token and certificate files by path.
The services write private operational logs to `~/edge-camera-logs/`; no media
frames or tokens are logged.
