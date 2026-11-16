"""Platform-specific integrations behind one interface (see :mod:`nocturne.platform.base`)."""

from __future__ import annotations

import logging

from nocturne.platform.base import MediaInfo, PlatformIntegration

log = logging.getLogger(__name__)

__all__ = ["MediaInfo", "PlatformIntegration", "create_platform"]


def create_platform() -> PlatformIntegration:
    import sys

    try:
        if sys.platform == "win32":
            from nocturne.platform.windows import WindowsIntegration

            return WindowsIntegration()
        if sys.platform.startswith("linux"):
            from nocturne.platform.linux import LinuxIntegration

            return LinuxIntegration()
    except Exception:  # noqa: BLE001 - the app must run without OS integration
        log.exception("Platform integration unavailable; continuing without it")
    return PlatformIntegration()
