"""Persistent application settings exposed to QML as ``AppSettings``."""

from __future__ import annotations

from typing import Any, Callable

from PySide6.QtCore import Property, QObject, Signal, Slot

from nocturne.db import Database

# name -> (python type, default)
SETTINGS_SPEC: dict[str, tuple[type, Any]] = {
    "language": (str, "ro"),              # "system" | "ro" | "en" | "ru"  (Română is the default)
    "downloadDir": (str, ""),             # empty = default Music/Nocturne
    "parallelDownloads": (int, 4),        # 1..8
    "audioQuality": (str, "best"),        # "best" | "medium" | "low"
    "startWithSystem": (bool, False),
    "keepRunningInTray": (bool, True),
    "keepRunningWithoutTray": (bool, False),  # GNOME without AppIndicator: closing quits by default
    "volume": (float, 0.8),
    "sortMode": (str, "recent"),
    "widgetVisible": (bool, False),
    "widgetCompact": (bool, False),
    "widgetOnTop": (bool, True),
    "widgetPinned": (bool, False),
    "widgetX": (int, -100000),
    "widgetY": (int, -100000),
    "miniX": (int, -100000),
    "miniY": (int, -100000),
    "windowX": (int, -100000),
    "windowY": (int, -100000),
    "windowWidth": (int, 1360),
    "windowHeight": (int, 860),
    "windowMaximized": (bool, False),
}


class _SettingsBase(QObject):
    changed = Signal(str)

    def __init__(self, db: Database, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._db = db
        self._values: dict[str, Any] = {}
        for key, (kind, default) in SETTINGS_SPEC.items():
            raw = db.get_setting(key, default)
            try:
                self._values[key] = kind(raw)
            except (TypeError, ValueError):
                self._values[key] = default

    def value(self, key: str) -> Any:
        return self._values[key]

    def set_value(self, key: str, value: Any) -> None:
        kind, _ = SETTINGS_SPEC[key]
        value = kind(value)
        if self._values.get(key) == value:
            return
        self._values[key] = value
        self._db.set_setting(key, value)
        getattr(self, f"{key}Changed").emit()
        self.changed.emit(key)

    @Slot(str, result="QVariant")
    def get(self, key: str) -> Any:
        return self._values.get(key)

    @Slot(str, "QVariant")
    def set(self, key: str, value: Any) -> None:
        if key in SETTINGS_SPEC:
            self.set_value(key, value)

    # Generic JSON blobs (player state, …) that QML never needs.
    def blob(self, key: str, default: Any = None) -> Any:
        return self._db.get_setting(key, default)

    def set_blob(self, key: str, value: Any) -> None:
        self._db.set_setting(key, value)


def _make_property(key: str, kind: type, signal: Signal) -> Property:
    def getter(self: _SettingsBase) -> Any:
        return self._values[key]

    def setter(self: _SettingsBase, value: Any) -> None:
        self.set_value(key, value)

    qt_type: Any = {str: str, int: int, float: float, bool: bool}[kind]
    return Property(qt_type, getter, setter, notify=signal)


def _build_settings_class() -> type[_SettingsBase]:
    attrs: dict[str, Any] = {}
    for key, (kind, _default) in SETTINGS_SPEC.items():
        sig = Signal()
        attrs[f"{key}Changed"] = sig
        attrs[key] = _make_property(key, kind, sig)
    return type("Settings", (_SettingsBase,), attrs)


Settings: Callable[..., _SettingsBase] = _build_settings_class()
SettingsType = _SettingsBase
