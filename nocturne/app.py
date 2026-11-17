"""Application bootstrap: Qt setup, services, QML engine, tray and OS integration."""

from __future__ import annotations

import logging
import os
import sys
import time
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from PySide6.QtCore import QCoreApplication, QObject, QRect, Qt, QTimer, QUrl
from PySide6.QtGui import QFont, QFontDatabase, QGuiApplication, QWindow
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle
from PySide6.QtWidgets import QApplication

from nocturne import APP_ID, APP_NAME, ORG_NAME, __version__, icons, paths
from nocturne.app_controller import AppController
from nocturne.db import Database
from nocturne.downloader import DownloadManager
from nocturne.i18n import Formatter, LanguageManager
from nocturne.log import setup_logging
from nocturne.platform import MediaInfo, PlatformIntegration, create_platform
from nocturne.player import PlayerController
from nocturne.settings import Settings, SettingsType
from nocturne.single_instance import SingleInstance
from nocturne.tray import TrayController

log = logging.getLogger("nocturne")


def _t(text: str, n: int = -1) -> str:
    return QCoreApplication.translate("Notifications", text, None, n)


class Nocturne(QObject):
    def __init__(self, app: QApplication, args: list[str]) -> None:
        super().__init__()
        self.app = app
        self.minimized = "--minimized" in args
        self.db = Database(paths.database_path())
        self.settings: SettingsType = Settings(self.db)

        # Language before any window exists (no flash of the wrong language).
        self.languages = LanguageManager(self.settings.value("language"), self)
        self.languages.languageChanged.connect(
            lambda: self.settings.set_value("language", self.languages.language)
        )
        self.fmt = Formatter(self.languages, self)

        self.platform: PlatformIntegration = create_platform()
        self.platform.start()

        self.player = PlayerController(self.db, self.settings, self)
        self.downloads = DownloadManager(self.db, self.settings, self)
        self.controller = AppController(self.db, self.settings, self.player, self.downloads, self.platform, self)
        self.controller.set_window_callbacks(self.show_main_window, self.hide_main_window, self.quit)

        self.widget_ipc: Any = None
        if paths.IS_WINDOWS:
            from nocturne.platform.widget_ipc import WidgetBridgeServer

            self.widget_ipc = WidgetBridgeServer(self)
            self.widget_ipc.commandReceived.connect(lambda cmd: self.on_platform_command(cmd, None))
            self.widget_ipc.start()

        self.tray = TrayController(
            self.player,
            self.languages,
            self.settings,
            self.show_main_window,
            self.controller.toggleDesktopWidget,
            self.controller.toggleMiniPlayer,
            self.quit,
            self,
        )
        self.controller.set_tray_available(self.tray.available)

        self.engine = QQmlApplicationEngine()
        self.languages.attach_engine(self.engine)
        self.engine.addImageProvider("icon", icons.IconProvider())
        self.engine.addImportPath(str(paths.resource("qml")))
        ctx = self.engine.rootContext()
        ctx.setContextProperty("App", self.controller)
        ctx.setContextProperty("Player", self.player)
        ctx.setContextProperty("Downloads", self.downloads)
        ctx.setContextProperty("AppSettings", self.settings)
        ctx.setContextProperty("Lang", self.languages)
        ctx.setContextProperty("Fmt", self.fmt)

        self.main_window = self._load_window("Main.qml")
        self.mini_window = self._load_window("MiniPlayer.qml")
        self.widget_window = self._load_window("DesktopWidget.qml")
        self.tray.show()

        self._wire_platform()
        self.player.restore_state()
        self._restore_geometry()
        self._quitting = False
        app.aboutToQuit.connect(self.shutdown)

    # ------------------------------------------------------------------ windows
    def _load_window(self, name: str) -> QWindow:
        before = len(self.engine.rootObjects())
        self.engine.load(QUrl.fromLocalFile(str(paths.resource("qml", "Nocturne", name))))
        roots = self.engine.rootObjects()
        if len(roots) <= before:
            raise RuntimeError(f"Failed to load {name}; see the log for QML errors")
        window = roots[-1]
        assert isinstance(window, QWindow)
        return window

    def _restore_geometry(self) -> None:
        s = self.settings
        w, h = max(1000, s.value("windowWidth")), max(640, s.value("windowHeight"))
        x, y = s.value("windowX"), s.value("windowY")
        screen = QGuiApplication.primaryScreen()
        if screen is not None:
            avail = screen.availableGeometry()
            # setGeometry() is the client area: leave room for the title bar and borders.
            frame_w, frame_h = 16, 48
            w = max(1000, min(w, avail.width() - frame_w))
            h = max(640, min(h, avail.height() - frame_h))
            on_screen = any(
                sc.availableGeometry().contains(QRect(x, y, w, h).center()) for sc in QGuiApplication.screens()
            )
            if x < -10000 or not on_screen:
                x = avail.x() + (avail.width() - w) // 2
                y = avail.y() + max(frame_h - 8, (avail.height() - h) // 2)
            # Never let the bottom (player bar) end up under the taskbar.
            if y + h > avail.y() + avail.height():
                y = max(avail.y() + frame_h - 8, avail.y() + avail.height() - h)
        self.main_window.setGeometry(x, y, w, h)

    def _save_geometry(self) -> None:
        win = self.main_window
        maximized = win.windowState() & Qt.WindowState.WindowMaximized
        self.settings.set_value("windowMaximized", bool(maximized))
        if not maximized and win.isVisible():
            g = win.geometry()
            self.settings.set_value("windowX", g.x())
            self.settings.set_value("windowY", g.y())
            self.settings.set_value("windowWidth", g.width())
            self.settings.set_value("windowHeight", g.height())

    def show_main_window(self) -> None:
        win = self.main_window
        if self.settings.value("windowMaximized"):
            win.showMaximized()
        elif win.windowState() & Qt.WindowState.WindowMinimized:
            win.showNormal()
        else:
            win.show()
        win.raise_()
        win.requestActivate()
        self.platform.attach_window(win)

    def hide_main_window(self) -> None:
        self._save_geometry()
        self.main_window.hide()

    def start(self, args: list[str]) -> None:
        if self.minimized and (self.tray.available or self.settings.value("keepRunningWithoutTray")):
            log.info("Started minimized")
        else:
            self.show_main_window()
        self._publish_all()
        QTimer.singleShot(400, lambda: self.handle_arguments(args))

    # ------------------------------------------------------------- arguments
    def handle_arguments(self, args: list[str]) -> None:
        handled_link = False
        for arg in args[1:]:
            if arg.startswith("nocturne:"):
                self._handle_uri(arg)
            elif not arg.startswith("-") and self.downloads.isValidLink(arg):
                self.controller.submitLink(arg)
                handled_link = True
        if handled_link:
            self.show_main_window()

    def on_second_instance(self, args: list[str]) -> None:
        log.info("Second instance: %s", args)
        if not any(a.startswith("nocturne:") for a in args[1:]):
            self.show_main_window()
        self.handle_arguments(args)

    def _handle_uri(self, uri: str) -> None:
        parsed = urlparse(uri)
        action = (parsed.netloc or parsed.path).strip("/").lower()
        if action in ("play_pause", "play", "pause", "next", "previous", "open_add_link", "show"):
            self.on_platform_command(action, None)
        elif action == "add":
            url = (parse_qs(parsed.query).get("url") or [""])[0]
            if url:
                self.controller.submitLink(url)
                self.show_main_window()

    # ------------------------------------------------------------- platform
    def _wire_platform(self) -> None:
        p = self.player
        p.currentTrackChanged.connect(self._on_track_changed)
        p.playingChanged.connect(self._on_playback_changed)
        p.durationChanged.connect(self._on_playback_changed)
        p.seeked.connect(lambda _ms: self._on_playback_changed())
        p.shuffleChanged.connect(self._on_options_changed)
        p.repeatModeChanged.connect(self._on_options_changed)
        p.volumeChanged.connect(self._on_options_changed)
        p.queueChanged.connect(self._on_options_changed)
        self.platform.command.connect(self.on_platform_command)
        self.downloads.statsChanged.connect(self._on_download_stats)
        self.downloads.batchFinished.connect(self._on_batch_finished)
        self.downloads.trackAdded.connect(lambda _id: self._publish_widget())
        self.languages.languageChanged.connect(self._on_language_changed)

        self._position_timer = QTimer(self)
        self._position_timer.setInterval(5000)
        self._position_timer.timeout.connect(self._on_position_tick)
        self._position_timer.start()
        self._last_progress: tuple[float | None, bool] | None = None

    def _publish_all(self) -> None:
        self._on_track_changed()
        self._on_options_changed()

    def _on_track_changed(self) -> None:
        t = self.player.current
        if t is None:
            self.platform.update_media(None)
        else:
            self.platform.update_media(
                MediaInfo(
                    track_id=t.id,
                    title=t.title,
                    artist=t.artist,
                    album=t.playlist_name or APP_NAME,
                    artwork_path=t.thumb_path,
                    duration_ms=int(t.duration * 1000),
                )
            )
        self._on_playback_changed()
        self._on_options_changed()

    def _on_playback_changed(self) -> None:
        self.platform.update_playback(self.player.playing, self.player.position, self.player.duration)
        self._publish_widget()

    def _on_position_tick(self) -> None:
        if self.player.playing:
            self.platform.update_playback(True, self.player.position, self.player.duration)
        report = getattr(self.platform, "report_position", None)
        if report is not None:
            report(self.player.position)

    def _on_options_changed(self) -> None:
        has_queue = self.player.queueLength > 0
        self.platform.update_options(
            self.player.shuffle, self.player.repeatMode, self.player.volume, has_queue, has_queue
        )

    def _on_language_changed(self) -> None:
        self.platform.update_language()
        self._publish_widget()

    def on_platform_command(self, cmd: str, arg: object) -> None:
        p = self.player
        if cmd == "play":
            p.play()
        elif cmd == "pause":
            p.pause()
        elif cmd == "play_pause":
            p.togglePlay()
        elif cmd == "next":
            p.next()
        elif cmd == "previous":
            p.previous()
        elif cmd == "stop":
            p.pause()
            p.seek(0)
        elif cmd == "seek" and arg is not None:
            p.seek(int(arg))  # type: ignore[call-overload]
        elif cmd == "seek_relative" and arg is not None:
            p.seek(max(0, p.position + int(arg)))  # type: ignore[call-overload]
        elif cmd == "volume" and arg is not None:
            p.setVolume(float(arg))  # type: ignore[arg-type]
        elif cmd == "shuffle" and arg is not None:
            if bool(arg) != p.shuffle:
                p.toggleShuffle()
        elif cmd == "repeat" and arg is not None:
            for _ in range(3):
                if p.repeatMode == int(arg):  # type: ignore[call-overload]
                    break
                p.cycleRepeat()
        elif cmd in ("raise", "show"):
            self.show_main_window()
        elif cmd == "quit":
            self.quit()
        elif cmd == "open_add_link":
            self.controller.openAddLink()

    def _on_download_stats(self) -> None:
        busy = self.downloads.busy or (self.downloads.paused and self.downloads.pendingCount > 0)
        state: tuple[float | None, bool] = (
            (round(self.downloads.progress, 3), self.downloads.paused) if busy else (None, False)
        )
        if state != self._last_progress:
            self._last_progress = state
            self.platform.set_progress(*state)

    def _on_batch_finished(self, kind: str, title: str, ok: int, failed: int) -> None:
        if kind not in ("playlist", "mix"):
            return
        heading = _t("Playlist downloaded")
        body = _t("“%1”: %n song(s) ready to play offline.", ok).replace("%1", title)
        if failed:
            body += " " + _t("%n failed.", failed)
        if not self.platform.notify(heading, body):
            self.tray.message(heading, body)

    def _publish_widget(self) -> None:
        if self.widget_ipc is None:
            return
        t = self.player.current
        recent = [
            {
                "title": r.title,
                "artist": r.artist,
                "duration": self.fmt.clock(r.duration),
                "artworkPath": r.thumb_path,
            }
            for r in self.db.recent_tracks(2)
        ]
        self.widget_ipc.publish(
            {
                "title": t.title if t else "",
                "artist": t.artist if t else "",
                "artworkPath": t.thumb_path if t else "",
                "isPlaying": self.player.playing,
                "position": round(self.player.position / 1000),
                "duration": round(self.player.duration / 1000),
                "recent": recent,
                "lang": self.languages.effectiveLanguage,
            }
        )

    # ---------------------------------------------------------------- quit
    def quit(self) -> None:
        if self._quitting:
            return
        self._quitting = True
        if self.main_window.isVisible():
            self._save_geometry()
        self.app.quit()

    def shutdown(self) -> None:
        log.info("Shutting down")
        try:
            self.player.save_state()
            self.player.stop()
        except Exception:  # noqa: BLE001
            log.exception("Saving player state failed")
        self.downloads.shutdown()
        self.tray.hide()
        if self.widget_ipc is not None:
            self.widget_ipc.stop()
        self.platform.shutdown()


def _load_fonts() -> None:
    font_dir = paths.resource("assets", "fonts")
    family = None
    for file in sorted(font_dir.glob("Manrope-*.ttf")):
        fid = QFontDatabase.addApplicationFont(str(file))
        if fid >= 0 and family is None:
            fams = QFontDatabase.applicationFontFamilies(fid)
            family = fams[0] if fams else None
    if family:
        font = QFont(family)
        font.setPixelSize(14)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        QGuiApplication.setFont(font)


def run(argv: list[str]) -> int:
    setup_logging(debug=bool(os.environ.get("NOCTURNE_DEBUG")))
    log.info("Nocturne %s starting (Python %s, %s)", __version__, sys.version.split()[0], sys.platform)

    os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")
    os.environ.setdefault("QT_MEDIA_BACKEND", "ffmpeg")
    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    QCoreApplication.setOrganizationName(ORG_NAME)
    QCoreApplication.setApplicationName(APP_NAME)
    QCoreApplication.setApplicationVersion(__version__)
    QGuiApplication.setDesktopFileName(APP_ID)
    QQuickStyle.setStyle("Basic")

    app = QApplication(argv)
    app.setQuitOnLastWindowClosed(False)
    app.setWindowIcon(icons.app_qicon())

    instance = SingleInstance()
    if os.environ.pop("NOCTURNE_RESTART", None):
        deadline = time.monotonic() + 10
        while instance.send_to_running(["--ping"]) and time.monotonic() < deadline:
            time.sleep(0.25)
    elif instance.send_to_running(argv):
        log.info("Nocturne is already running; forwarded arguments")
        return 0
    instance.listen()

    _load_fonts()
    try:
        nocturne = Nocturne(app, argv)
    except Exception:
        log.exception("Start-up failed")
        raise
    instance.messageReceived.connect(
        lambda args: None if args == ["--ping"] else nocturne.on_second_instance(args)
    )
    nocturne.start(argv)
    code = app.exec()
    # Tear down QML before the Python backends it binds to (avoids "null" binding noise on exit).
    from PySide6.QtCore import QEvent

    nocturne.engine.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    log.info("Exited with code %s", code)
    return int(code)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(run(sys.argv))
