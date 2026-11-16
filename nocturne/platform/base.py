"""Common interface for OS integration (media controls, taskbar, notifications, autostart)."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QWindow

log = logging.getLogger(__name__)


@dataclass(slots=True)
class MediaInfo:
    track_id: int
    title: str
    artist: str
    album: str
    artwork_path: str
    duration_ms: int


class PlatformIntegration(QObject):
    """Default no-op implementation; subclasses override what their OS supports.

    ``command`` is emitted (always on the GUI thread) with one of:
    ``play``, ``pause``, ``play_pause``, ``next``, ``previous``, ``stop``,
    ``seek`` (ms), ``seek_relative`` (ms), ``volume`` (0..1), ``shuffle`` (bool),
    ``repeat`` (0/1/2), ``raise``, ``quit``, ``open_add_link``.
    """

    command = Signal(str, object)

    name = "generic"

    def start(self) -> None:
        """Initialise integrations that do not need a window."""

    def attach_window(self, window: QWindow) -> None:
        """Called once the main window has a native handle."""

    def update_media(self, info: MediaInfo | None) -> None:
        """Current track changed (``None`` = nothing loaded)."""

    def update_playback(self, playing: bool, position_ms: int, duration_ms: int) -> None:
        """Play state / position changed (called on state change and on seek)."""

    def update_options(self, shuffle: bool, repeat: int, volume: float, can_next: bool, can_prev: bool) -> None:
        """Shuffle / repeat / volume / navigation availability changed."""

    def update_language(self) -> None:
        """Re-translate any OS-visible labels (thumbnail button tooltips, …)."""

    def set_progress(self, fraction: float | None, paused: bool = False) -> None:
        """Download progress on the taskbar / dock (``None`` hides it)."""

    def notify(self, title: str, body: str, image_path: str = "") -> bool:
        """Show a native notification. Returns False when unsupported."""
        return False

    def autostart_supported(self) -> bool:
        return False

    def autostart_enabled(self) -> bool:
        return False

    def set_autostart(self, enabled: bool) -> bool:
        return False

    def capabilities(self) -> dict[str, Any]:
        return {}

    def shutdown(self) -> None:
        """Release native resources."""
