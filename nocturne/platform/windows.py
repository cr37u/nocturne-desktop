"""Windows integration: SMTC (media flyout, lock screen, media keys), taskbar thumbnail
toolbar + progress (ITaskbarList3), toast notifications and autostart."""

from __future__ import annotations

import asyncio
import concurrent.futures
import ctypes
import logging
import threading
import winreg
from ctypes import POINTER, Structure, c_int, c_ulonglong, c_void_p, c_wchar, wintypes
from datetime import timedelta
from pathlib import Path
from typing import Any, Callable, Coroutine
from xml.sax.saxutils import escape

from PySide6.QtCore import QAbstractNativeEventFilter, QCoreApplication, Signal
from PySide6.QtGui import QGuiApplication, QWindow

from nocturne import APP_NAME, icons, paths
from nocturne.platform.base import MediaInfo, PlatformIntegration

log = logging.getLogger(__name__)

AUMID = "Nocturne.MusicPlayer"
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
STARTUP_TASK_ID = "NocturneStartup"

WM_COMMAND = 0x0111
THBN_CLICKED = 0x1800
THB_ICON, THB_TOOLTIP, THB_FLAGS = 0x2, 0x4, 0x8
THBF_ENABLED, THBF_DISABLED = 0x0, 0x1
TBPF_NOPROGRESS, TBPF_NORMAL, TBPF_PAUSED = 0x0, 0x2, 0x8
BTN_PREV, BTN_PLAY, BTN_NEXT = 1, 2, 3


def _t(text: str) -> str:
    return QCoreApplication.translate("Windows", text)


# --------------------------------------------------------------------------- WinRT
class _WinRTWorker:
    """Runs every WinRT call on one MTA thread with its own asyncio loop.

    The Qt GUI thread is an STA (OLE), so WinRT is kept off it entirely.
    """

    def __init__(self) -> None:
        self._loop: asyncio.AbstractEventLoop | None = None
        self._ready = threading.Event()
        self._thread = threading.Thread(target=self._run, name="winrt", daemon=True)
        self._thread.start()
        self._ready.wait(5)

    def _run(self) -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        self._loop = loop
        self._ready.set()
        loop.run_forever()

    def submit(self, fn: Callable[[], Coroutine[Any, Any, Any]]) -> concurrent.futures.Future[Any]:
        assert self._loop is not None
        fut = asyncio.run_coroutine_threadsafe(fn(), self._loop)

        def _log(f: concurrent.futures.Future[Any]) -> None:
            if not f.cancelled() and f.exception() is not None:
                log.error("WinRT call failed: %r", f.exception())

        fut.add_done_callback(_log)
        return fut

    def stop(self) -> None:
        if self._loop is not None:
            self._loop.call_soon_threadsafe(self._loop.stop)


class _Smtc:
    """SystemMediaTransportControls obtained from a muted WinRT MediaPlayer.

    A Windows.Media.Playback.MediaPlayer created in a desktop process owns an SMTC instance
    bound to the process, which is the supported way for unpackaged apps to use it.
    """

    def __init__(self, worker: _WinRTWorker, on_command: Callable[[str, object], None]) -> None:
        self._worker = worker
        self._on_command = on_command
        self._mp: Any = None
        self._smtc: Any = None
        self._artwork = ""
        self._worker.submit(self._init).result(10)

    async def _init(self) -> None:
        from winrt.windows.media import MediaPlaybackType, SystemMediaTransportControlsButton
        from winrt.windows.media.playback import MediaPlayer

        self._buttons = SystemMediaTransportControlsButton
        self._mp = MediaPlayer()
        self._mp.command_manager.is_enabled = False
        smtc = self._mp.system_media_transport_controls
        smtc.is_enabled = True
        smtc.is_play_enabled = True
        smtc.is_pause_enabled = True
        smtc.is_stop_enabled = True
        smtc.is_next_enabled = True
        smtc.is_previous_enabled = True
        smtc.add_button_pressed(self._button_pressed)
        smtc.add_playback_position_change_requested(self._position_requested)
        smtc.display_updater.type = MediaPlaybackType.MUSIC
        self._smtc = smtc

    def _button_pressed(self, _sender: Any, args: Any) -> None:
        b = self._buttons
        mapping = {
            b.PLAY: "play",
            b.PAUSE: "pause",
            b.NEXT: "next",
            b.PREVIOUS: "previous",
            b.STOP: "stop",
        }
        cmd = mapping.get(args.button)
        if cmd:
            self._on_command(cmd, None)

    def _position_requested(self, _sender: Any, args: Any) -> None:
        pos = args.requested_playback_position
        ms = int(pos.total_seconds() * 1000) if isinstance(pos, timedelta) else int(pos) // 10_000
        self._on_command("seek", ms)

    def update_media(self, info: MediaInfo | None) -> None:
        async def job() -> None:
            from winrt.windows.media import MediaPlaybackStatus
            from winrt.windows.storage import StorageFile
            from winrt.windows.storage.streams import RandomAccessStreamReference

            du = self._smtc.display_updater
            if info is None:
                du.clear_all()
                du.update()
                self._smtc.playback_status = MediaPlaybackStatus.CLOSED
                return
            from winrt.windows.media import MediaPlaybackType

            du.type = MediaPlaybackType.MUSIC
            props = du.music_properties
            props.title = info.title
            props.artist = info.artist
            props.album_title = info.album
            du.thumbnail = None
            if info.artwork_path and Path(info.artwork_path).is_file():
                try:
                    file = await StorageFile.get_file_from_path_async(str(Path(info.artwork_path).resolve()))
                    du.thumbnail = RandomAccessStreamReference.create_from_file(file)
                except Exception:  # noqa: BLE001
                    log.debug("SMTC artwork failed", exc_info=True)
            du.update()

        self._worker.submit(job)

    def update_playback(self, playing: bool, position_ms: int, duration_ms: int) -> None:
        async def job() -> None:
            from winrt.windows.media import MediaPlaybackStatus, SystemMediaTransportControlsTimelineProperties

            self._smtc.playback_status = MediaPlaybackStatus.PLAYING if playing else MediaPlaybackStatus.PAUSED
            tl = SystemMediaTransportControlsTimelineProperties()
            end = timedelta(milliseconds=max(0, duration_ms))
            tl.start_time = timedelta(0)
            tl.min_seek_time = timedelta(0)
            tl.end_time = end
            tl.max_seek_time = end
            tl.position = timedelta(milliseconds=max(0, min(position_ms, duration_ms or position_ms)))
            self._smtc.update_timeline_properties(tl)

        self._worker.submit(job)

    def update_options(self, shuffle: bool, repeat: int, can_next: bool, can_prev: bool) -> None:
        async def job() -> None:
            from winrt.windows.media import MediaPlaybackAutoRepeatMode

            self._smtc.is_next_enabled = can_next
            self._smtc.is_previous_enabled = can_prev
            try:
                self._smtc.shuffle_enabled = shuffle
                self._smtc.auto_repeat_mode = {
                    0: MediaPlaybackAutoRepeatMode.NONE,
                    1: MediaPlaybackAutoRepeatMode.LIST,
                    2: MediaPlaybackAutoRepeatMode.TRACK,
                }[repeat]
            except Exception:  # noqa: BLE001 - optional properties
                pass

        self._worker.submit(job)


# --------------------------------------------------------------------------- Taskbar
class THUMBBUTTON(Structure):
    _fields_ = [
        ("dwMask", wintypes.DWORD),
        ("iId", wintypes.UINT),
        ("iBitmap", wintypes.UINT),
        ("hIcon", wintypes.HICON),
        ("szTip", c_wchar * 260),
        ("dwFlags", wintypes.DWORD),
    ]


def _taskbar_interfaces() -> Any:
    from comtypes import COMMETHOD, GUID, HRESULT, IUnknown

    class ITaskbarList(IUnknown):
        _iid_ = GUID("{56FDF342-FD6D-11d0-958A-006097C9A090}")
        _methods_ = [
            COMMETHOD([], HRESULT, "HrInit"),
            COMMETHOD([], HRESULT, "AddTab", (["in"], wintypes.HWND, "hwnd")),
            COMMETHOD([], HRESULT, "DeleteTab", (["in"], wintypes.HWND, "hwnd")),
            COMMETHOD([], HRESULT, "ActivateTab", (["in"], wintypes.HWND, "hwnd")),
            COMMETHOD([], HRESULT, "SetActiveAlt", (["in"], wintypes.HWND, "hwnd")),
        ]

    class ITaskbarList2(ITaskbarList):
        _iid_ = GUID("{602D4995-B13A-429b-A66E-1935E44F4317}")
        _methods_ = [
            COMMETHOD(
                [], HRESULT, "MarkFullscreenWindow", (["in"], wintypes.HWND, "hwnd"), (["in"], wintypes.BOOL, "f")
            ),
        ]

    class ITaskbarList3(ITaskbarList2):
        _iid_ = GUID("{ea1afb91-9e28-4b86-90e9-9e9f8a5eefaf}")
        _methods_ = [
            COMMETHOD(
                [],
                HRESULT,
                "SetProgressValue",
                (["in"], wintypes.HWND, "hwnd"),
                (["in"], c_ulonglong, "done"),
                (["in"], c_ulonglong, "total"),
            ),
            COMMETHOD([], HRESULT, "SetProgressState", (["in"], wintypes.HWND, "hwnd"), (["in"], c_int, "flags")),
            COMMETHOD([], HRESULT, "RegisterTab", (["in"], wintypes.HWND, "tab"), (["in"], wintypes.HWND, "mdi")),
            COMMETHOD([], HRESULT, "UnregisterTab", (["in"], wintypes.HWND, "tab")),
            COMMETHOD([], HRESULT, "SetTabOrder", (["in"], wintypes.HWND, "tab"), (["in"], wintypes.HWND, "before")),
            COMMETHOD(
                [],
                HRESULT,
                "SetTabActive",
                (["in"], wintypes.HWND, "tab"),
                (["in"], wintypes.HWND, "mdi"),
                (["in"], wintypes.DWORD, "reserved"),
            ),
            COMMETHOD(
                [],
                HRESULT,
                "ThumbBarAddButtons",
                (["in"], wintypes.HWND, "hwnd"),
                (["in"], wintypes.UINT, "count"),
                (["in"], POINTER(THUMBBUTTON), "buttons"),
            ),
            COMMETHOD(
                [],
                HRESULT,
                "ThumbBarUpdateButtons",
                (["in"], wintypes.HWND, "hwnd"),
                (["in"], wintypes.UINT, "count"),
                (["in"], POINTER(THUMBBUTTON), "buttons"),
            ),
            COMMETHOD([], HRESULT, "ThumbBarSetImageList", (["in"], wintypes.HWND, "hwnd"), (["in"], c_void_p, "il")),
            COMMETHOD(
                [],
                HRESULT,
                "SetOverlayIcon",
                (["in"], wintypes.HWND, "hwnd"),
                (["in"], wintypes.HICON, "icon"),
                (["in"], wintypes.LPCWSTR, "desc"),
            ),
            COMMETHOD(
                [], HRESULT, "SetThumbnailTooltip", (["in"], wintypes.HWND, "hwnd"), (["in"], wintypes.LPCWSTR, "tip")
            ),
            COMMETHOD(
                [],
                HRESULT,
                "SetThumbnailClip",
                (["in"], wintypes.HWND, "hwnd"),
                (["in"], POINTER(wintypes.RECT), "clip"),
            ),
        ]

    return ITaskbarList3


def _hicon_from_png(data: bytes, size: int) -> int:
    user32 = ctypes.windll.user32
    user32.CreateIconFromResourceEx.restype = wintypes.HICON
    user32.CreateIconFromResourceEx.argtypes = [
        ctypes.c_char_p,
        wintypes.DWORD,
        wintypes.BOOL,
        wintypes.DWORD,
        c_int,
        c_int,
        wintypes.UINT,
    ]
    return user32.CreateIconFromResourceEx(data, len(data), True, 0x00030000, size, size, 0) or 0


class _Taskbar:
    def __init__(self, on_command: Callable[[str, object], None]) -> None:
        import comtypes.client

        self._on_command = on_command
        iface = _taskbar_interfaces()
        self._tb = comtypes.client.CreateObject("{56FDF344-FD6D-11d0-958A-006097C9A090}", interface=iface)
        self._tb.HrInit()
        self.hwnd = 0
        self._buttons_added = False
        self._playing = False
        self._icons: dict[str, int] = {}
        self._progress: tuple[float | None, bool] = (None, False)
        self.msg_button_created = ctypes.windll.user32.RegisterWindowMessageW("TaskbarButtonCreated")

    def _icon(self, name: str) -> int:
        if name not in self._icons:
            size = ctypes.windll.user32.GetSystemMetrics(49) or 16  # SM_CXSMICON (DPI-scaled)
            self._icons[name] = _hicon_from_png(icons.png_bytes(name, "#F1F1F7", size), size)
        return self._icons[name]

    def _make_buttons(self) -> Any:
        arr = (THUMBBUTTON * 3)()
        spec = [
            (BTN_PREV, "previous", _t("Previous")),
            (BTN_PLAY, "pause" if self._playing else "play", _t("Pause") if self._playing else _t("Play")),
            (BTN_NEXT, "next", _t("Next")),
        ]
        for i, (bid, icon, tip) in enumerate(spec):
            arr[i].dwMask = THB_ICON | THB_TOOLTIP | THB_FLAGS
            arr[i].iId = bid
            arr[i].hIcon = self._icon(icon)
            arr[i].szTip = tip[:259]
            arr[i].dwFlags = THBF_ENABLED
        return arr

    def on_button_created(self) -> None:
        if not self.hwnd:
            return
        try:
            self._tb.ThumbBarAddButtons(self.hwnd, 3, self._make_buttons())
            self._buttons_added = True
            self.set_progress(*self._progress)
        except Exception:  # noqa: BLE001
            log.exception("ThumbBarAddButtons failed")

    def refresh(self) -> None:
        if not (self.hwnd and self._buttons_added):
            return
        try:
            self._tb.ThumbBarUpdateButtons(self.hwnd, 3, self._make_buttons())
        except Exception:  # noqa: BLE001
            log.debug("ThumbBarUpdateButtons failed", exc_info=True)

    def set_playing(self, playing: bool) -> None:
        if playing != self._playing:
            self._playing = playing
            self.refresh()

    def set_progress(self, fraction: float | None, paused: bool) -> None:
        self._progress = (fraction, paused)
        if not self.hwnd:
            return
        try:
            if fraction is None:
                self._tb.SetProgressState(self.hwnd, TBPF_NOPROGRESS)
            else:
                self._tb.SetProgressState(self.hwnd, TBPF_PAUSED if paused else TBPF_NORMAL)
                self._tb.SetProgressValue(self.hwnd, int(max(0.0, min(1.0, fraction)) * 1000), 1000)
        except Exception:  # noqa: BLE001
            log.debug("Taskbar progress failed", exc_info=True)

    def handle_command(self, button_id: int) -> None:
        cmd = {BTN_PREV: "previous", BTN_PLAY: "play_pause", BTN_NEXT: "next"}.get(button_id)
        if cmd:
            self._on_command(cmd, None)

    def destroy(self) -> None:
        for h in self._icons.values():
            if h:
                ctypes.windll.user32.DestroyIcon(h)
        self._icons.clear()


class _NativeFilter(QAbstractNativeEventFilter):
    def __init__(self, taskbar: _Taskbar) -> None:
        super().__init__()
        self._taskbar = taskbar

    def nativeEventFilter(self, event_type: Any, message: Any) -> tuple[bool, int]:  # noqa: N802
        try:
            if bytes(event_type) != b"windows_generic_MSG":
                return False, 0
            msg = wintypes.MSG.from_address(int(message))
            tb = self._taskbar
            if not tb.hwnd or msg.hWnd != tb.hwnd:
                return False, 0
            if msg.message == tb.msg_button_created:
                tb.on_button_created()
            elif msg.message == WM_COMMAND and (msg.wParam >> 16) & 0xFFFF == THBN_CLICKED:
                tb.handle_command(msg.wParam & 0xFFFF)
                return True, 0
        except Exception:  # noqa: BLE001
            log.debug("native event filter error", exc_info=True)
        return False, 0


# --------------------------------------------------------------------------- Integration
class WindowsIntegration(PlatformIntegration):
    name = "windows"
    _command_from_thread = Signal(str, object)

    def __init__(self) -> None:
        super().__init__()
        self._packaged = paths.is_msix_packaged()
        self._command_from_thread.connect(self.command)
        self._worker: _WinRTWorker | None = None
        self._smtc: _Smtc | None = None
        self._taskbar: _Taskbar | None = None
        self._filter: _NativeFilter | None = None
        self._last_playing: bool | None = None
        if not self._packaged:
            try:
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(AUMID)
            except Exception:  # noqa: BLE001
                log.debug("AUMID not set", exc_info=True)

    def _emit(self, cmd: str, arg: object) -> None:
        # Called from WinRT/COM threads: hop to the GUI thread through a queued signal.
        self._command_from_thread.emit(cmd, arg)

    def capabilities(self) -> dict[str, Any]:
        return {"smtc": self._smtc is not None, "taskbar": self._taskbar is not None, "packaged": self._packaged}

    def start(self) -> None:
        if not self._packaged:
            self._register_aumid()
            self._register_protocol()
        try:
            self._worker = _WinRTWorker()
            self._smtc = _Smtc(self._worker, self._emit)
            log.info("SMTC ready")
        except Exception:  # noqa: BLE001
            log.exception("SMTC unavailable")
            self._smtc = None

    def attach_window(self, window: QWindow) -> None:
        if self._taskbar is not None:
            return
        try:
            self._taskbar = _Taskbar(self._emit)
            self._taskbar.hwnd = int(window.winId())
            self._filter = _NativeFilter(self._taskbar)
            app = QGuiApplication.instance()
            assert app is not None
            app.installNativeEventFilter(self._filter)
            # The window may already have its taskbar button: try immediately as well.
            self._taskbar.on_button_created()
            log.info("Taskbar integration ready")
        except Exception:  # noqa: BLE001
            log.exception("Taskbar integration unavailable")
            self._taskbar = None

    def update_media(self, info: MediaInfo | None) -> None:
        if self._smtc is not None:
            self._smtc.update_media(info)

    def update_playback(self, playing: bool, position_ms: int, duration_ms: int) -> None:
        if self._smtc is not None:
            self._smtc.update_playback(playing, position_ms, duration_ms)
        if self._taskbar is not None:
            self._taskbar.set_playing(playing)

    def update_options(self, shuffle: bool, repeat: int, volume: float, can_next: bool, can_prev: bool) -> None:
        if self._smtc is not None:
            self._smtc.update_options(shuffle, repeat, can_next, can_prev)

    def update_language(self) -> None:
        if self._taskbar is not None:
            self._taskbar.refresh()

    def set_progress(self, fraction: float | None, paused: bool = False) -> None:
        if self._taskbar is not None:
            self._taskbar.set_progress(fraction, paused)

    # ------------------------------------------------------------ notifications
    def notify(self, title: str, body: str, image_path: str = "") -> bool:
        if self._worker is None:
            return False
        image = ""
        if image_path and Path(image_path).is_file():
            image = (
                f'<image placement="appLogoOverride" hint-crop="circle" '
                f'src="{escape(Path(image_path).resolve().as_uri())}"/>'
            )
        xml = (
            '<toast activationType="protocol" launch="nocturne://show">'
            "<visual><binding template=\"ToastGeneric\">"
            f"<text>{escape(title)}</text><text>{escape(body)}</text>{image}"
            "</binding></visual></toast>"
        )

        async def job() -> None:
            from winrt.windows.data.xml.dom import XmlDocument
            from winrt.windows.ui.notifications import ToastNotification, ToastNotificationManager

            doc = XmlDocument()
            doc.load_xml(xml)
            if self._packaged:
                notifier = ToastNotificationManager.create_toast_notifier()
            else:
                notifier = ToastNotificationManager.create_toast_notifier(AUMID)
            notifier.show(ToastNotification(doc))

        self._worker.submit(job)
        return True

    def _register_aumid(self) -> None:
        """Lets toasts from an unpackaged process show the Nocturne name and icon."""
        try:
            icon_path = paths.app_data_dir() / "nocturne-icon.png"
            if not icon_path.exists():
                icons.app_icon_image(256).save(str(icon_path), "PNG")
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, rf"Software\Classes\AppUserModelId\{AUMID}") as key:
                winreg.SetValueEx(key, "DisplayName", 0, winreg.REG_SZ, APP_NAME)
                winreg.SetValueEx(key, "IconUri", 0, winreg.REG_SZ, str(icon_path))
                winreg.SetValueEx(key, "IconBackgroundColor", 0, winreg.REG_SZ, "FF1E40AF")
        except OSError:
            log.debug("AUMID registration failed", exc_info=True)

    def _register_protocol(self) -> None:
        """``nocturne://`` links (used by toasts and the Win+W widget bridge)."""
        try:
            cmd = paths.launch_command()
            command = " ".join(f'"{c}"' if " " in c or not c.startswith("-") else c for c in cmd) + ' "%1"'
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Classes\nocturne") as key:
                winreg.SetValueEx(key, "", 0, winreg.REG_SZ, "URL:Nocturne")
                winreg.SetValueEx(key, "URL Protocol", 0, winreg.REG_SZ, "")
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Classes\nocturne\shell\open\command") as key:
                winreg.SetValueEx(key, "", 0, winreg.REG_SZ, command)
        except OSError:
            log.debug("Protocol registration failed", exc_info=True)

    # ---------------------------------------------------------------- autostart
    def autostart_supported(self) -> bool:
        return True

    def _run_command(self) -> str:
        cmd = paths.launch_command()
        return " ".join(f'"{c}"' if not c.startswith("-") else c for c in cmd) + " --minimized"

    def autostart_enabled(self) -> bool:
        if self._packaged:
            return self._startup_task_state() is True
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
                winreg.QueryValueEx(key, APP_NAME)
                return True
        except OSError:
            return False

    def set_autostart(self, enabled: bool) -> bool:
        if self._packaged:
            return self._set_startup_task(enabled)
        try:
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
                if enabled:
                    winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, self._run_command())
                else:
                    try:
                        winreg.DeleteValue(key, APP_NAME)
                    except FileNotFoundError:
                        pass
            return True
        except OSError:
            log.exception("Autostart change failed")
            return False

    def _startup_task_state(self) -> bool | None:
        if self._worker is None:
            return None

        async def job() -> bool:
            from winrt.windows.applicationmodel import StartupTask, StartupTaskState

            task = await StartupTask.get_async(STARTUP_TASK_ID)
            return task.state in (StartupTaskState.ENABLED, StartupTaskState.ENABLED_BY_POLICY)

        try:
            return bool(self._worker.submit(job).result(5))
        except Exception:  # noqa: BLE001
            log.debug("StartupTask query failed", exc_info=True)
            return None

    def _set_startup_task(self, enabled: bool) -> bool:
        if self._worker is None:
            return False

        async def job() -> bool:
            from winrt.windows.applicationmodel import StartupTask, StartupTaskState

            task = await StartupTask.get_async(STARTUP_TASK_ID)
            if enabled:
                state = await task.request_enable_async()
                return state in (StartupTaskState.ENABLED, StartupTaskState.ENABLED_BY_POLICY)
            task.disable()
            return True

        try:
            return bool(self._worker.submit(job).result(15))
        except Exception:  # noqa: BLE001
            log.exception("StartupTask change failed")
            return False

    def shutdown(self) -> None:
        try:
            if self._smtc is not None:
                self._smtc.update_media(None)
        except Exception:  # noqa: BLE001
            pass
        if self._taskbar is not None:
            self._taskbar.set_progress(None, False)
            self._taskbar.destroy()
        if self._worker is not None:
            self._worker.stop()
