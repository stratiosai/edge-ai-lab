#!/bin/sh
# One-time switch from the detached controlled-test pipeline to durable user services.
set -eu

repo_root=${EDGE_CAMERA_REPO_ROOT:-"$HOME/edge-ai-lab"}
unit_dir="$HOME/.config/systemd/user"
service_dir="$repo_root/projects/private-ring-camera/infra/systemd-user"

if [ ! -d "$service_dir" ]; then
  echo "missing staged service templates: $service_dir" >&2
  exit 1
fi

echo "Enabling user lingering; this needs the Pi administrator password."
sudo loginctl enable-linger "$USER"
if [ "$(loginctl show-user "$USER" -p Linger --value)" != "yes" ]; then
  echo "user lingering was not enabled; leaving detached capture untouched" >&2
  exit 1
fi

mkdir -p "$unit_dir" "$HOME/edge-camera-logs"
chmod 700 "$HOME/edge-camera-logs"
install -m 644 "$service_dir"/edge-camera-*.service "$unit_dir"/
systemctl --user daemon-reload

# Stop the detached processes only after the persistence prerequisite passed.
capture_pid=$(pgrep -f "^/bin/sh $repo_root/projects/private-ring-camera/pi/capture/run_capture.sh$" || true)
if [ -n "$capture_pid" ]; then
  capture_group=$(ps -o pgid= -p "$capture_pid" | tr -d ' ')
  kill -TERM -- "-$capture_group" || true
fi
for pattern in \
  "^/usr/bin/python3 -m stratios_edge_ai.private_camera.pi_live" \
  "^/usr/bin/python3 -m stratios_edge_ai.private_camera.pi_agent"; do
  for pid in $(pgrep -f "$pattern" || true); do
    kill -TERM "$pid" || true
  done
done
sleep 3

systemctl --user enable edge-camera-capture.service edge-camera-live.service edge-camera-agent.service
systemctl --user start edge-camera-live.service
sleep 1
systemctl --user start edge-camera-capture.service
sleep 2
systemctl --user start edge-camera-agent.service
systemctl --user --no-pager --full status \
  edge-camera-capture.service edge-camera-live.service edge-camera-agent.service
