"""Private, local-first Raspberry Pi camera server components."""

from typing import Any

from .config import CameraServerConfig


def create_app(*args: Any, **kwargs: Any) -> Any:
    """Lazily import the Mac web server so Pi-only tools have no web dependency."""
    from .app import create_app as implementation

    return implementation(*args, **kwargs)


__all__ = ["CameraServerConfig", "create_app"]
