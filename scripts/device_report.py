#!/usr/bin/env python3
"""Print a non-secret device report to guide Raspberry Pi setup decisions."""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
from pathlib import Path


def first_line(path: str) -> str:
    try:
        return Path(path).read_text(encoding="utf-8").strip().splitlines()[0]
    except (OSError, IndexError):
        return "unavailable"


def command_path(name: str) -> str:
    return shutil.which(name) or "not found"


def main() -> None:
    total, used, free = shutil.disk_usage(Path.cwd())
    print(f"system: {platform.system()} {platform.release()}")
    print(f"machine: {platform.machine()}")
    print(f"python: {platform.python_version()}")
    print(f"hostname: {platform.node()}")
    print(f"cpu model: {first_line('/proc/device-tree/model')}")
    print(f"memory info: {first_line('/proc/meminfo')}")
    print(f"working disk free GiB: {free / 1024**3:.1f}")
    print(f"rpicam-hello: {command_path('rpicam-hello')}")
    print(f"rpicam-still: {command_path('rpicam-still')}")
    print(f"libcamera-hello: {command_path('libcamera-hello')}")
    print(f"vcgencmd: {command_path('vcgencmd')}")
    print(f"running as root: {os.geteuid() == 0}")

    vcgencmd = shutil.which("vcgencmd")
    if vcgencmd:
        result = subprocess.run(
            [vcgencmd, "measure_temp"], capture_output=True, text=True, check=False
        )
        print(f"temperature: {result.stdout.strip() or 'unavailable'}")


if __name__ == "__main__":
    main()

