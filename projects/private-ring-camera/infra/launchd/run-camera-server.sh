#!/bin/sh
set -eu

# This file is copied beside the private server.env file, outside Git and iCloud.
# server.env is mode 600 and contains the device-only tokens and TLS paths.
. "$(dirname "$0")/server.env"
exec "$EDGE_CAMERA_SERVER_EXECUTABLE"
