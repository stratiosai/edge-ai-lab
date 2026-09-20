#!/bin/sh
# Record bounded, frame-free health evidence for the Pi camera soak test.
set -eu

if [ "$#" -ne 5 ]; then
  echo "usage: $0 <ssh-key> <pi-user@host> <duration-seconds> <interval-seconds> <log-file>" >&2
  exit 64
fi

key_file=$1
pi_target=$2
duration_seconds=$3
interval_seconds=$4
log_file=$5
archive_db=${EDGE_CAMERA_DATABASE_PATH:-"$HOME/Library/Application Support/StratiosAI/edge-ai-camera/camera.sqlite3"}

case $duration_seconds:$interval_seconds in
  *[!0-9:]*|0:*|*:0) echo "duration and interval must be positive seconds" >&2; exit 64 ;;
esac

mkdir -p "$(dirname "$log_file")"
umask 077
deadline=$(( $(date +%s) + duration_seconds ))

while [ "$(date +%s)" -lt "$deadline" ]; do
  timestamp=$(date -u +%Y-%m-%dT%H:%M:%SZ)
  if snapshot=$(ssh -o BatchMode=yes -o ConnectTimeout=10 -o HostKeyAlias=edge-ai-pi-wifi -i "$key_file" "$pi_target" '
      systemd_state=$(systemctl --user is-active edge-camera-capture.service edge-camera-live.service edge-camera-agent.service 2>/dev/null | tr "\n" "," || true)
      printf "systemd=%s" "$systemd_state"
      printf " manual_processes="
      pgrep -f "stratios_edge_ai.private_camera.pi_live" >/dev/null && printf "live," || printf "live-missing,"
      pgrep -f "stratios_edge_ai.private_camera.pi_agent" >/dev/null && printf "agent," || printf "agent-missing,"
      pgrep -f "rpicam-vid" >/dev/null && printf "capture" || printf "capture-missing"
      printf " buffer_files="
      find /home/stratiosai/edge-camera-buffer -maxdepth 1 -type f -name "*.mp4" | wc -l
      vcgencmd get_throttled
      vcgencmd measure_temp
    ' 2>&1); then
    printf '%s %s\n' "$timestamp" "$snapshot" >> "$log_file"
  else
    printf '%s monitor_error=%s\n' "$timestamp" "$snapshot" >> "$log_file"
  fi
  if [ -r "$archive_db" ] && command -v sqlite3 >/dev/null 2>&1; then
    archive_snapshot=$(sqlite3 "$archive_db" 'select count(*), coalesce(max(started_at), 0) from segments;' 2>/dev/null || printf 'unavailable')
    printf '%s archive_segments=%s\n' "$timestamp" "$archive_snapshot" >> "$log_file"
  else
    printf '%s archive_segments=unavailable\n' "$timestamp" >> "$log_file"
  fi
  sleep "$interval_seconds"
done
