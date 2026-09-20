#!/bin/sh
set -eu

BUFFER_DIR="${EDGE_CAMERA_BUFFER_DIR:-$HOME/edge-camera-buffer}"
LIVE_FIFO="${EDGE_CAMERA_LIVE_FIFO:-$HOME/edge-camera-live/live.mjpg.fifo}"

mkdir -p "$BUFFER_DIR" "$(dirname "$LIVE_FIFO")"
chmod 700 "$BUFFER_DIR" "$(dirname "$LIVE_FIFO")"

if [ ! -p "$LIVE_FIFO" ]; then
  if [ -e "$LIVE_FIFO" ]; then
    echo "refusing to replace non-FIFO live path: $LIVE_FIFO" >&2
    exit 1
  fi
  mkfifo -m 600 "$LIVE_FIFO"
fi

command -v rpicam-vid >/dev/null
command -v ffmpeg >/dev/null

LIVE_VIDEO_FILTER="scale=1280:720:force_original_aspect_ratio=decrease"
if [ "${EDGE_CAMERA_LIVE_DEBUG_CLOCK:-0}" = "1" ]; then
  # This is an opt-in acceptance-test aid. It marks the low-resolution live
  # preview only; the authoritative 1080p archive remains unaltered.
  LIVE_VIDEO_FILTER="${LIVE_VIDEO_FILTER},drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf:text=%{localtime}:x=18:y=18:fontsize=38:fontcolor=white:box=1:boxcolor=black@0.65"
fi

# Capture once, then make two deliberately separate outputs: durable one-minute
# H.264 archive segments and a 720p MJPEG FIFO. The Pi live service reads that
# FIFO and exposes a token-protected multipart stream that the Mac proxies.
rpicam-vid \
  -n -t 0 \
  --width 1920 --height 1080 --framerate 15 \
  --codec yuv420 -o - \
| ffmpeg \
  -y \
  -hide_banner -loglevel warning \
  -f rawvideo -pixel_format yuv420p -video_size 1920x1080 -framerate 15 -i pipe:0 \
  -an -map 0:v:0 \
  -c:v libx264 -preset veryfast -tune zerolatency \
  -b:v 2500k -maxrate 3000k -bufsize 5000k \
  -g 30 -keyint_min 30 -sc_threshold 0 -flags +global_header \
  -f segment -segment_time 60 -reset_timestamps 1 -strftime 1 \
  -segment_format mp4 -segment_format_options movflags=+faststart \
  "${BUFFER_DIR}/%s.mp4" \
  -map 0:v:0 -vf "$LIVE_VIDEO_FILTER" -r 10 \
  -c:v mjpeg -q:v 6 -f mpjpeg "$LIVE_FIFO"
