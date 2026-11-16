"""Linux integration: MPRIS2 (media widgets, lock screen, media keys), desktop
notifications (org.freedesktop.Notifications) and XDG autostart.

D-Bus is spoken through *jeepney* (pure Python). MPRIS requires strict D-Bus types
(``x`` for 64-bit positions, ``a{sv}`` metadata, ``o`` object paths) which PySide6's
QtDBus cannot reliably express from Python, so a tiny typed implementation is used.
"""

from __future__ import annotations

import logging
import os
import queue
import shlex
import shutil
import subprocess
import threading
from pathlib import Path
from typing import Any

from PySide6.QtCore import Signal

from nocturne import APP_ID, APP_NAME, paths
from nocturne.platform.base import MediaInfo, PlatformIntegration

log = logging.getLogger(__name__)

BUS_NAME = "org.mpris.MediaPlayer2.nocturne"
OBJ_PATH = "/org/mpris/MediaPlayer2"
ROOT_IFACE = "org.mpris.MediaPlayer2"
PLAYER_IFACE = "org.mpris.MediaPlayer2.Player"
PROPS_IFACE = "org.freedesktop.DBus.Properties"
INTROSPECT_IFACE = "org.freedesktop.DBus.Introspectable"
NO_TRACK = "/org/mpris/MediaPlayer2/TrackList/NoTrack"

INTROSPECTION = """<!DOCTYPE node PUBLIC "-//freedesktop//DTD D-BUS Object Introspection 1.0//EN"
 "http://www.freedesktop.org/standards/dbus/1.0/introspect.dtd">
<node>
  <interface name="org.freedesktop.DBus.Introspectable">
    <method name="Introspect"><arg direction="out" type="s"/></method>
  </interface>
  <interface name="org.freedesktop.DBus.Properties">
    <method name="Get"><arg direction="in" type="s"/><arg direction="in" type="s"/><arg direction="out" type="v"/></method>
    <method name="GetAll"><arg direction="in" type="s"/><arg direction="out" type="a{sv}"/></method>
    <method name="Set"><arg direction="in" type="s"/><arg direction="in" type="s"/><arg direction="in" type="v"/></method>
    <signal name="PropertiesChanged"><arg type="s"/><arg type="a{sv}"/><arg type="as"/></signal>
  </interface>
  <interface name="org.mpris.MediaPlayer2">
    <method name="Raise"/><method name="Quit"/>
    <property name="CanQuit" type="b" access="read"/>
    <property name="CanRaise" type="b" access="read"/>
    <property name="HasTrackList" type="b" access="read"/>
    <property name="Identity" type="s" access="read"/>
    <property name="DesktopEntry" type="s" access="read"/>
    <property name="SupportedUriSchemes" type="as" access="read"/>
    <property name="SupportedMimeTypes" type="as" access="read"/>
  </interface>
  <interface name="org.mpris.MediaPlayer2.Player">
    <method name="Next"/><method name="Previous"/><method name="Pause"/><method name="PlayPause"/>
    <method name="Stop"/><method name="Play"/>
    <method name="Seek"><arg direction="in" type="x"/></method>
    <method name="SetPosition"><arg direction="in" type="o"/><arg direction="in" type="x"/></method>
    <method name="OpenUri"><arg direction="in" type="s"/></method>
    <signal name="Seeked"><arg type="x"/></signal>
    <property name="PlaybackStatus" type="s" access="read"/>
    <property name="LoopStatus" type="s" access="readwrite"/>
    <property name="Rate" type="d" access="readwrite"/>
    <property name="Shuffle" type="b" access="readwrite"/>
    <property name="Metadata" type="a{sv}" access="read"/>
    <property name="Volume" type="d" access="readwrite"/>
    <property name="Position" type="x" access="read"/>
    <property name="MinimumRate" type="d" access="read"/>
    <property name="MaximumRate" type="d" access="read"/>
    <property name="CanGoNext" type="b" access="read"/>
    <property name="CanGoPrevious" type="b" access="read"/>
    <property name="CanPlay" type="b" access="read"/>
    <property name="CanPause" type="b" access="read"/>
    <property name="CanSeek" type="b" access="read"/>
    <property name="CanControl" type="b" access="read"/>
  </interface>
</node>"""

LOOP_TO_MPRIS = {0: "None", 1: "Playlist", 2: "Track"}
MPRIS_TO_LOOP = {v: k for k, v in LOOP_TO_MPRIS.items()}


class _Mpris:
    """MPRIS2 server running on its own thread."""

    def __init__(self, emit: Any) -> None:
        from jeepney import DBusAddress
        from jeepney.bus_messages import message_bus
        from jeepney.io.threading import open_dbus_router

        self._emit = emit
        self._lock = threading.Lock()
        self._state: dict[str, Any] = {
            "playing": False,
            "has_track": False,
            "position_us": 0,
            "metadata": {"mpris:trackid": ("o", NO_TRACK)},
            "shuffle": False,
            "repeat": 0,
            "volume": 1.0,
            "can_next": False,
            "can_prev": False,
        }
        self._router_cm = open_dbus_router(bus="SESSION")
        self._router = self._router_cm.__enter__()
        reply = self._router.send_and_get_reply(message_bus.RequestName(BUS_NAME, 4))  # DO_NOT_QUEUE
        log.info("MPRIS name request result: %s", reply.body)
        self._address = DBusAddress(OBJ_PATH, interface=PROPS_IFACE)
        self._player_address = DBusAddress(OBJ_PATH, interface=PLAYER_IFACE)
        self._queue: queue.Queue[Any] = queue.Queue()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._serve, name="mpris", daemon=True)
        self._thread.start()

    # ------------------------------------------------------------- properties
    def _player_props(self) -> dict[str, tuple[str, Any]]:
        s = self._state
        status = "Playing" if s["playing"] else ("Paused" if s["has_track"] else "Stopped")
        return {
            "PlaybackStatus": ("s", status),
            "LoopStatus": ("s", LOOP_TO_MPRIS[s["repeat"]]),
            "Rate": ("d", 1.0),
            "Shuffle": ("b", bool(s["shuffle"])),
            "Metadata": ("a{sv}", s["metadata"]),
            "Volume": ("d", float(s["volume"])),
            "Position": ("x", int(s["position_us"])),
            "MinimumRate": ("d", 1.0),
            "MaximumRate": ("d", 1.0),
            "CanGoNext": ("b", bool(s["can_next"])),
            "CanGoPrevious": ("b", bool(s["can_prev"])),
            "CanPlay": ("b", True),
            "CanPause": ("b", True),
            "CanSeek": ("b", bool(s["has_track"])),
            "CanControl": ("b", True),
        }

    @staticmethod
    def _root_props() -> dict[str, tuple[str, Any]]:
        return {
            "CanQuit": ("b", True),
            "CanRaise": ("b", True),
            "HasTrackList": ("b", False),
            "Identity": ("s", APP_NAME),
            "DesktopEntry": ("s", APP_ID),
            "SupportedUriSchemes": ("as", []),
            "SupportedMimeTypes": ("as", []),
        }

    def _props_for(self, iface: str) -> dict[str, tuple[str, Any]]:
        with self._lock:
            if iface == PLAYER_IFACE:
                return self._player_props()
            if iface == ROOT_IFACE:
                return self._root_props()
        return {}

    # ---------------------------------------------------------------- server
    def _serve(self) -> None:
        from jeepney import HeaderFields, MatchRule, MessageType, new_error, new_method_return

        rule = MatchRule(type="method_call")
        with self._router.filter(rule, queue=self._queue):
            while not self._stop.is_set():
                try:
                    msg = self._queue.get(timeout=0.5)
                except queue.Empty:
                    continue
                if msg.header.message_type != MessageType.method_call:
                    continue
                fields = msg.header.fields
                if fields.get(HeaderFields.path) != OBJ_PATH:
                    self._router.send(
                        new_error(msg, "org.freedesktop.DBus.Error.UnknownObject", "s", ("No such object",))
                    )
                    continue
                iface = fields.get(HeaderFields.interface, "")
                member = fields.get(HeaderFields.member, "")
                try:
                    reply = self._handle(msg, iface, member, new_method_return)
                except Exception as exc:  # noqa: BLE001
                    log.debug("MPRIS call %s.%s failed", iface, member, exc_info=True)
                    reply = new_error(msg, "org.freedesktop.DBus.Error.Failed", "s", (str(exc),))
                if reply is not None:
                    self._router.send(reply)

    def _handle(self, msg: Any, iface: str, member: str, ret: Any) -> Any:
        from jeepney import new_error

        body = msg.body
        if member == "Introspect":
            return ret(msg, "s", (INTROSPECTION,))
        if iface == PROPS_IFACE or member in ("Get", "GetAll", "Set") and not iface:
            if member == "Get":
                props = self._props_for(body[0])
                if body[1] not in props:
                    return new_error(msg, "org.freedesktop.DBus.Error.UnknownProperty", "s", (body[1],))
                return ret(msg, "v", (props[body[1]],))
            if member == "GetAll":
                return ret(msg, "a{sv}", (self._props_for(body[0]),))
            if member == "Set":
                _iface, name, (_sig, value) = body
                if name == "Volume":
                    self._emit("volume", max(0.0, min(1.0, float(value))))
                elif name == "Shuffle":
                    self._emit("shuffle", bool(value))
                elif name == "LoopStatus" and value in MPRIS_TO_LOOP:
                    self._emit("repeat", MPRIS_TO_LOOP[value])
                return ret(msg, "", ())
        simple = {
            "Next": "next",
            "Previous": "previous",
            "Pause": "pause",
            "PlayPause": "play_pause",
            "Stop": "stop",
            "Play": "play",
            "Raise": "raise",
            "Quit": "quit",
        }
        if member in simple:
            self._emit(simple[member], None)
            return ret(msg, "", ())
        if member == "Seek":
            self._emit("seek_relative", int(body[0]) // 1000)
            return ret(msg, "", ())
        if member == "SetPosition":
            track_path, pos_us = body
            with self._lock:
                current = self._state["metadata"].get("mpris:trackid", ("o", NO_TRACK))[1]
            if track_path == current:
                self._emit("seek", int(pos_us) // 1000)
            return ret(msg, "", ())
        if member == "OpenUri":
            return ret(msg, "", ())
        return new_error(msg, "org.freedesktop.DBus.Error.UnknownMethod", "s", (member,))

    # --------------------------------------------------------------- updates
    def _changed(self, names: list[str]) -> None:
        from jeepney import new_signal

        props = self._props_for(PLAYER_IFACE)
        changed = {n: props[n] for n in names if n in props}
        if not changed:
            return
        try:
            self._router.send(new_signal(self._address, "PropertiesChanged", "sa{sv}as", (PLAYER_IFACE, changed, [])))
        except Exception:  # noqa: BLE001
            log.debug("PropertiesChanged failed", exc_info=True)

    def update(self, names: list[str], **values: Any) -> None:
        with self._lock:
            self._state.update(values)
        self._changed(names)

    def seeked(self, position_us: int) -> None:
        from jeepney import new_signal

        with self._lock:
            self._state["position_us"] = position_us
        try:
            self._router.send(new_signal(self._player_address, "Seeked", "x", (int(position_us),)))
        except Exception:  # noqa: BLE001
            log.debug("Seeked signal failed", exc_info=True)

    def notify(self, title: str, body: str, icon: str) -> None:
        from jeepney import DBusAddress, new_method_call

        addr = DBusAddress(
            "/org/freedesktop/Notifications",
            bus_name="org.freedesktop.Notifications",
            interface="org.freedesktop.Notifications",
        )
        hints = {"desktop-entry": ("s", APP_ID)}
        msg = new_method_call(addr, "Notify", "susssasa{sv}i", (APP_NAME, 0, icon, title, body, [], hints, 6000))
        self._router.send(msg)

    def close(self) -> None:
        self._stop.set()
        try:
            self._router_cm.__exit__(None, None, None)
        except Exception:  # noqa: BLE001
            pass


class LinuxIntegration(PlatformIntegration):
    name = "linux"
    _command_from_thread = Signal(str, object)

    def __init__(self) -> None:
        super().__init__()
        self._command_from_thread.connect(self.command)
        self._mpris: _Mpris | None = None
        self._last_position_us = 0
        self._track_path = NO_TRACK

    def _emit(self, cmd: str, arg: object) -> None:
        self._command_from_thread.emit(cmd, arg)

    def capabilities(self) -> dict[str, Any]:
        desktop = os.environ.get("XDG_CURRENT_DESKTOP", "")
        return {
            "mpris": self._mpris is not None,
            "kde": "KDE" in desktop.upper(),
            "gnome": "GNOME" in desktop.upper(),
            "wayland": os.environ.get("XDG_SESSION_TYPE", "") == "wayland" or bool(os.environ.get("WAYLAND_DISPLAY")),
        }

    def start(self) -> None:
        try:
            self._mpris = _Mpris(self._emit)
            log.info("MPRIS ready as %s", BUS_NAME)
        except Exception:  # noqa: BLE001
            log.exception("MPRIS unavailable (no session bus?)")
            self._mpris = None

    def update_media(self, info: MediaInfo | None) -> None:
        if self._mpris is None:
            return
        if info is None:
            self._track_path = NO_TRACK
            metadata: dict[str, tuple[str, Any]] = {"mpris:trackid": ("o", NO_TRACK)}
            self._mpris.update(["Metadata", "PlaybackStatus", "CanSeek"], metadata=metadata, has_track=False)
            return
        self._track_path = f"/io/github/nocturne/track/{int(info.track_id)}"
        metadata = {
            "mpris:trackid": ("o", self._track_path),
            "mpris:length": ("x", int(info.duration_ms) * 1000),
            "xesam:title": ("s", info.title),
            "xesam:artist": ("as", [info.artist] if info.artist else []),
            "xesam:album": ("s", info.album or ""),
        }
        if info.artwork_path and Path(info.artwork_path).is_file():
            metadata["mpris:artUrl"] = ("s", Path(info.artwork_path).resolve().as_uri())
        self._mpris.update(["Metadata", "PlaybackStatus", "CanSeek"], metadata=metadata, has_track=True)

    def update_playback(self, playing: bool, position_ms: int, duration_ms: int) -> None:
        if self._mpris is None:
            return
        pos_us = int(position_ms) * 1000
        self._mpris.update(["PlaybackStatus"], playing=playing, position_us=pos_us)
        # Clients extrapolate the position; only signal real jumps.
        if abs(pos_us - self._last_position_us) > 1_500_000 or position_ms < 1000:
            self._mpris.seeked(pos_us)
        self._last_position_us = pos_us

    def report_position(self, position_ms: int) -> None:
        if self._mpris is not None:
            with self._mpris._lock:  # noqa: SLF001 - cheap position refresh for Get(Position)
                self._mpris._state["position_us"] = int(position_ms) * 1000  # noqa: SLF001
            self._last_position_us = int(position_ms) * 1000

    def update_options(self, shuffle: bool, repeat: int, volume: float, can_next: bool, can_prev: bool) -> None:
        if self._mpris is not None:
            self._mpris.update(
                ["Shuffle", "LoopStatus", "Volume", "CanGoNext", "CanGoPrevious"],
                shuffle=shuffle,
                repeat=repeat,
                volume=volume,
                can_next=can_next,
                can_prev=can_prev,
            )

    def notify(self, title: str, body: str, image_path: str = "") -> bool:
        icon = str(Path(image_path).resolve()) if image_path and Path(image_path).is_file() else APP_ID
        if self._mpris is not None:
            try:
                self._mpris.notify(title, body, icon)
                return True
            except Exception:  # noqa: BLE001
                log.debug("D-Bus notification failed", exc_info=True)
        if shutil.which("notify-send"):
            try:
                subprocess.Popen(["notify-send", "-a", APP_NAME, "-i", icon, title, body])  # noqa: S603,S607
                return True
            except OSError:
                pass
        return False

    # ---------------------------------------------------------------- autostart
    @staticmethod
    def _autostart_file() -> Path:
        config = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
        return config / "autostart" / f"{APP_ID}.desktop"

    def autostart_supported(self) -> bool:
        return True

    def autostart_enabled(self) -> bool:
        return self._autostart_file().is_file()

    def set_autostart(self, enabled: bool) -> bool:
        path = self._autostart_file()
        try:
            if not enabled:
                path.unlink(missing_ok=True)
                return True
            path.parent.mkdir(parents=True, exist_ok=True)
            exec_line = " ".join(shlex.quote(p) for p in paths.launch_command()) + " --minimized"
            path.write_text(
                "[Desktop Entry]\n"
                "Type=Application\n"
                f"Name={APP_NAME}\n"
                f"Exec={exec_line}\n"
                f"Icon={APP_ID}\n"
                "X-GNOME-Autostart-enabled=true\n"
                "NoDisplay=false\n"
                "Terminal=false\n",
                encoding="utf-8",
            )
            return True
        except OSError:
            log.exception("Autostart change failed")
            return False

    def shutdown(self) -> None:
        if self._mpris is not None:
            self._mpris.close()
            self._mpris = None


def install_kde_widget(source: Path) -> tuple[bool, str]:
    """Install/upgrade the Plasma 6 widget with kpackagetool6."""
    tool = shutil.which("kpackagetool6") or shutil.which("kpackagetool5")
    if tool is None:
        return False, "kpackagetool6 not found"
    for args in (["-t", "Plasma/Applet", "-u", str(source)], ["-t", "Plasma/Applet", "-i", str(source)]):
        result = subprocess.run([tool, *args], capture_output=True, text=True, check=False)  # noqa: S603
        if result.returncode == 0:
            return True, result.stdout.strip()
    return False, (result.stderr or result.stdout).strip()
