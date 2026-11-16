"""Application facade exposed to QML as ``App``: navigation, library actions, system options."""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any, Callable

from PySide6.QtCore import Property, QCoreApplication, QObject, QTimer, QUrl, Signal, Slot
from PySide6.QtGui import QDesktopServices, QGuiApplication

from nocturne import __version__, links, paths, ytdlp_update
from nocturne.db import Database
from nocturne.downloader import DownloadManager
from nocturne.models import PlaylistListModel, TrackListModel
from nocturne.platform import PlatformIntegration
from nocturne.player import PlayerController
from nocturne.settings import SettingsType

log = logging.getLogger(__name__)

PAGES = ("library", "favorites", "playlists", "playlist", "downloads", "settings")


def _t(text: str) -> str:
    return QCoreApplication.translate("App", text)


class AppController(QObject):
    pageChanged = Signal()
    searchChanged = Signal()
    libraryChanged = Signal()
    statsChanged = Signal()
    ytdlpChanged = Signal()
    miniPlayerVisibleChanged = Signal()
    startWithSystemChanged = Signal()
    trayChanged = Signal()

    toast = Signal(str, bool)
    focusSearch = Signal()
    focusAddLink = Signal()

    _ytdlpResult = Signal(str, str, bool, bool)  # status, version, busy, restart needed

    def __init__(
        self,
        db: Database,
        settings: SettingsType,
        player: PlayerController,
        downloads: DownloadManager,
        platform: PlatformIntegration,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._db = db
        self._settings = settings
        self._player = player
        self._downloads = downloads
        self._platform = platform
        self._page = "library"
        self._playlist_id = -1
        self._search = ""
        self._library_count = 0
        self._library_duration = 0.0
        self._storage_used = 0
        self._storage_fraction = 0.0
        self._mini_visible = False
        self._tray_available = False
        self._ytdlp_version = ytdlp_update.current_version()
        self._ytdlp_status = ""
        self._ytdlp_busy = False
        self._ytdlp_restart = False
        self._show_window_cb: Callable[[], None] | None = None
        self._hide_window_cb: Callable[[], None] | None = None
        self._quit_cb: Callable[[], None] | None = None

        self.libraryModel = TrackListModel(self)
        self.playlistsModel = PlaylistListModel(self)

        self._reload_timer = QTimer(self)
        self._reload_timer.setSingleShot(True)
        self._reload_timer.setInterval(250)
        self._reload_timer.timeout.connect(self.reload)

        player.currentTrackChanged.connect(self._on_current_changed)
        downloads.trackAdded.connect(lambda _id: self._reload_timer.start())
        downloads.playlistCreated.connect(lambda _id: self._reload_timer.start())
        downloads.message.connect(self.toast)
        player.message.connect(self.toast)
        self._ytdlpResult.connect(self._on_ytdlp_result)
        self.reload()

    def set_window_callbacks(
        self, show: Callable[[], None], hide: Callable[[], None], quit_app: Callable[[], None]
    ) -> None:
        self._show_window_cb = show
        self._hide_window_cb = hide
        self._quit_cb = quit_app

    def set_tray_available(self, available: bool) -> None:
        self._tray_available = available
        self.trayChanged.emit()

    # ------------------------------------------------------------- properties
    def _get_page(self) -> str:
        return self._page

    def _get_playlist_id(self) -> int:
        return self._playlist_id

    def _get_playlist_name(self) -> str:
        if self._page != "playlist":
            return ""
        pl = self._db.get_playlist(self._playlist_id)
        return pl.name if pl else ""

    def _get_search(self) -> str:
        return self._search

    def _get_library_model(self) -> QObject:
        return self.libraryModel

    def _get_playlists_model(self) -> QObject:
        return self.playlistsModel

    def _get_library_count(self) -> int:
        return self._library_count

    def _get_library_duration(self) -> float:
        return self._library_duration

    def _get_storage_used(self) -> float:
        return float(self._storage_used)

    def _get_storage_fraction(self) -> float:
        return self._storage_fraction

    def _get_version(self) -> str:
        return __version__

    def _get_ytdlp_version(self) -> str:
        return self._ytdlp_version

    def _get_ytdlp_status(self) -> str:
        return self._ytdlp_status

    def _get_ytdlp_busy(self) -> bool:
        return self._ytdlp_busy

    def _get_ytdlp_restart(self) -> bool:
        return self._ytdlp_restart

    def _get_download_dir_url(self) -> str:
        return QUrl.fromLocalFile(self._get_download_dir()).toString()

    def _get_mini_visible(self) -> bool:
        return self._mini_visible

    def _set_mini_visible(self, value: bool) -> None:
        if value != self._mini_visible:
            self._mini_visible = bool(value)
            self.miniPlayerVisibleChanged.emit()

    def _get_tray(self) -> bool:
        return self._tray_available

    def _get_os(self) -> str:
        if paths.IS_WINDOWS:
            return "windows"
        if paths.IS_LINUX:
            return "linux"
        return sys.platform

    def _get_caps(self) -> dict[str, Any]:
        return self._platform.capabilities()

    def _get_download_dir(self) -> str:
        return self._settings.value("downloadDir") or str(paths.default_download_dir())

    def _get_start_with_system(self) -> bool:
        return self._platform.autostart_enabled()

    def _get_autostart_supported(self) -> bool:
        return self._platform.autostart_supported()

    page = Property(str, _get_page, notify=pageChanged)
    playlistId = Property(int, _get_playlist_id, notify=pageChanged)
    playlistName = Property(str, _get_playlist_name, notify=libraryChanged)
    searchText = Property(str, _get_search, notify=searchChanged)
    library = Property(QObject, _get_library_model, constant=True)
    playlists = Property(QObject, _get_playlists_model, constant=True)
    libraryCount = Property(int, _get_library_count, notify=statsChanged)
    libraryDuration = Property(float, _get_library_duration, notify=statsChanged)
    storageUsed = Property(float, _get_storage_used, notify=statsChanged)
    storageFraction = Property(float, _get_storage_fraction, notify=statsChanged)
    version = Property(str, _get_version, constant=True)
    ytdlpVersion = Property(str, _get_ytdlp_version, notify=ytdlpChanged)
    ytdlpStatus = Property(str, _get_ytdlp_status, notify=ytdlpChanged)
    ytdlpBusy = Property(bool, _get_ytdlp_busy, notify=ytdlpChanged)
    ytdlpRestartNeeded = Property(bool, _get_ytdlp_restart, notify=ytdlpChanged)
    downloadDirUrl = Property(str, _get_download_dir_url, notify=libraryChanged)
    miniPlayerVisible = Property(bool, _get_mini_visible, _set_mini_visible, notify=miniPlayerVisibleChanged)
    trayAvailable = Property(bool, _get_tray, notify=trayChanged)
    os = Property(str, _get_os, constant=True)
    capabilities = Property("QVariantMap", _get_caps, notify=trayChanged)
    downloadDir = Property(str, _get_download_dir, notify=libraryChanged)
    startWithSystem = Property(bool, _get_start_with_system, notify=startWithSystemChanged)
    autostartSupported = Property(bool, _get_autostart_supported, constant=True)

    # ------------------------------------------------------------- navigation
    @Slot(str)
    def navigate(self, page: str) -> None:
        if page not in PAGES or page == "playlist":
            return
        if self._page == page:
            return
        self._page = page
        self._playlist_id = -1
        self.pageChanged.emit()
        self.reload()

    @Slot(int)
    def openPlaylist(self, playlist_id: int) -> None:  # noqa: N802
        self._page = "playlist"
        self._playlist_id = int(playlist_id)
        self.pageChanged.emit()
        self.reload()

    @Slot(str)
    def setSearch(self, text: str) -> None:  # noqa: N802
        if text == self._search:
            return
        self._search = text
        self.searchChanged.emit()
        if self._page not in ("library", "favorites", "playlist"):
            self._page = "library"
            self.pageChanged.emit()
        self._reload_timer.start()

    @Slot(str)
    def setSort(self, mode: str) -> None:  # noqa: N802
        self._settings.set_value("sortMode", mode)
        self.reload()

    @Slot()
    def reload(self) -> None:
        sort = self._settings.value("sortMode")
        if self._page == "favorites":
            tracks = self._db.list_tracks(sort=sort, search=self._search, favorites_only=True)
        elif self._page == "playlist" and self._playlist_id >= 0:
            tracks = self._db.list_tracks(sort=sort, search=self._search, playlist_id=self._playlist_id)
        else:
            tracks = self._db.list_tracks(sort=sort, search=self._search)
        current = self._player.current
        self.libraryModel.set_current(current.id if current else -1)
        self.libraryModel.set_tracks(tracks)
        self.playlistsModel.set_playlists(self._db.list_playlists())
        count, duration, size = self._db.library_stats()
        self._library_count = count
        self._library_duration = duration
        self._storage_used = size
        try:
            target = Path(self._get_download_dir())
            probe = target if target.exists() else target.anchor or Path.home()
            total = shutil.disk_usage(probe).total
            self._storage_fraction = min(1.0, max(0.02 if size else 0.0, size / total if total else 0.0))
        except OSError:
            self._storage_fraction = 0.0
        self.statsChanged.emit()
        self.libraryChanged.emit()

    def _on_current_changed(self) -> None:
        current = self._player.current
        self.libraryModel.set_current(current.id if current else -1)

    # ---------------------------------------------------------------- playback
    @Slot(int)
    def playFromView(self, track_id: int) -> None:  # noqa: N802
        self._player.playTrack(track_id, self.libraryModel.trackIds())

    @Slot()
    def playView(self) -> None:  # noqa: N802
        self._player.playAll(self.libraryModel.trackIds())

    @Slot()
    def shuffleView(self) -> None:  # noqa: N802
        self._player.shuffleAll(self.libraryModel.trackIds())

    @Slot(int)
    def playPlaylist(self, playlist_id: int) -> None:  # noqa: N802
        ids = [t.id for t in self._db.list_tracks(playlist_id=playlist_id)]
        if ids:
            self._player.playAll(ids)

    # ----------------------------------------------------------------- library
    @Slot(int)
    def toggleFavorite(self, track_id: int) -> None:  # noqa: N802
        track = self._db.get_track(track_id)
        if track is None:
            return
        self._db.set_favorite(track_id, not track.favorite)
        self._player.refresh_track(track_id)
        if self._page == "favorites":
            self.reload()
        else:
            self.libraryModel.set_favorite(track_id, not track.favorite)
        self.libraryChanged.emit()

    @Slot()
    def toggleFavoriteCurrent(self) -> None:  # noqa: N802
        if self._player.current is not None:
            self.toggleFavorite(self._player.current.id)

    @Slot("QVariantList")
    def deleteTracks(self, ids: list[Any]) -> None:  # noqa: N802
        id_list = [int(i) for i in ids or []]
        if not id_list:
            return
        self._player.remove_tracks(id_list)
        removed = self._db.delete_tracks(id_list)
        for track in removed:
            for path in (track.file_path, track.thumb_path):
                if path:
                    try:
                        Path(path).unlink(missing_ok=True)
                    except OSError:
                        log.warning("Could not delete %s", path)
        self.toast.emit(QCoreApplication.translate("App", "%n song(s) deleted.", None, len(removed)), False)
        self.reload()

    @Slot(int, int)
    def addToPlaylist(self, track_id: int, playlist_id: int) -> None:  # noqa: N802
        pl = self._db.get_playlist(playlist_id)
        if pl is None:
            return
        added = self._db.add_to_playlist(playlist_id, [track_id])
        if added:
            self.toast.emit(_t("Added to “%1”.").replace("%1", pl.name), False)
        else:
            self.toast.emit(_t("Already in “%1”.").replace("%1", pl.name), False)
        self.reload()
        self._player.refresh_track(track_id)

    @Slot(int)
    def removeFromCurrentPlaylist(self, track_id: int) -> None:  # noqa: N802
        if self._page == "playlist" and self._playlist_id >= 0:
            self._db.remove_from_playlist(self._playlist_id, [track_id])
            self.reload()
            self._player.refresh_track(track_id)

    @Slot(str, result=int)
    def createPlaylist(self, name: str) -> int:  # noqa: N802
        name = name.strip()
        if not name:
            return -1
        pid = self._db.create_playlist(name)
        self.reload()
        return pid

    @Slot(str, int)
    def createPlaylistWithTrack(self, name: str, track_id: int) -> None:  # noqa: N802
        pid = self.createPlaylist(name)
        if pid >= 0 and track_id >= 0:
            self.addToPlaylist(track_id, pid)

    @Slot(int, str)
    def renamePlaylist(self, playlist_id: int, name: str) -> None:  # noqa: N802
        self._db.rename_playlist(playlist_id, name)
        self.reload()
        self._player.refresh_all()

    @Slot(int)
    def deletePlaylist(self, playlist_id: int) -> None:  # noqa: N802
        self._db.delete_playlist(playlist_id)
        if self._page == "playlist" and self._playlist_id == playlist_id:
            self._page = "playlists"
            self._playlist_id = -1
            self.pageChanged.emit()
        self.reload()
        self._player.refresh_all()

    @Slot(int, result=str)
    def playlistNameOf(self, playlist_id: int) -> str:  # noqa: N802
        pl = self._db.get_playlist(playlist_id)
        return pl.name if pl else ""

    @Slot(int)
    def showInFolder(self, track_id: int) -> None:  # noqa: N802
        track = self._db.get_track(track_id)
        if track is None:
            return
        path = Path(track.file_path)
        try:
            if paths.IS_WINDOWS and path.exists():
                subprocess.Popen(["explorer", "/select,", str(path)])  # noqa: S603,S607
                return
            if paths.IS_LINUX and path.exists() and shutil.which("dbus-send"):
                subprocess.Popen(  # noqa: S603
                    [
                        "dbus-send",
                        "--session",
                        "--dest=org.freedesktop.FileManager1",
                        "--type=method_call",
                        "/org/freedesktop/FileManager1",
                        "org.freedesktop.FileManager1.ShowItems",
                        f"array:string:{path.as_uri()}",
                        "string:",
                    ]
                )
                return
        except OSError:
            pass
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path.parent)))

    # ------------------------------------------------------------------- links
    @Slot(str, result=bool)
    def submitLink(self, text: str) -> bool:  # noqa: N802
        return self._downloads.addLink(text)

    @Slot(result=bool)
    def pasteLink(self) -> bool:  # noqa: N802
        clipboard = QGuiApplication.clipboard()
        text = clipboard.text() if clipboard else ""
        if links.parse(text) is None:
            self.toast.emit(_t("The clipboard does not contain a YouTube link."), True)
            return False
        return self._downloads.addLink(text)

    @Slot()
    def openAddLink(self) -> None:  # noqa: N802
        self.showMainWindow()
        self.navigate("downloads")
        QTimer.singleShot(150, self.focusAddLink.emit)

    # ---------------------------------------------------------------- settings
    @Slot(str)
    def setDownloadDir(self, url_or_path: str) -> None:  # noqa: N802
        url = QUrl(url_or_path)
        path = url.toLocalFile() if url.isLocalFile() else url_or_path
        if path:
            self._settings.set_value("downloadDir", path)
            self.libraryChanged.emit()

    @Slot()
    def resetDownloadDir(self) -> None:  # noqa: N802
        self._settings.set_value("downloadDir", "")
        self.libraryChanged.emit()

    @Slot()
    def openDownloadDir(self) -> None:  # noqa: N802
        path = Path(self._get_download_dir())
        path.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

    @Slot()
    def openLogs(self) -> None:  # noqa: N802
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(paths.logs_dir())))

    @Slot(bool)
    def setStartWithSystem(self, enabled: bool) -> None:  # noqa: N802
        ok = self._platform.set_autostart(enabled)
        if not ok:
            self.toast.emit(_t("Could not change the start-up setting."), True)
        self._settings.set_value("startWithSystem", self._platform.autostart_enabled())
        self.startWithSystemChanged.emit()

    @Slot()
    def checkYtDlpUpdate(self) -> None:  # noqa: N802
        if self._ytdlp_busy:
            return
        self._ytdlp_busy = True
        self._ytdlp_status = _t("Checking for updates…")
        self.ytdlpChanged.emit()

        def work() -> None:
            try:
                latest, url, sums = ytdlp_update.latest_release()
                current = ytdlp_update.current_version()
                if not ytdlp_update.is_newer(latest, current):
                    self._ytdlpResult.emit(_t("yt-dlp is up to date."), current, False, False)
                    return
                self._ytdlpResult.emit(_t("Downloading yt-dlp %1…").replace("%1", latest), current, True, False)
                installed = ytdlp_update.download_update(url, sums)
                self._ytdlpResult.emit(
                    _t("yt-dlp %1 is ready. Restart Nocturne to use it.").replace("%1", installed), current, False, True
                )
            except Exception as exc:  # noqa: BLE001
                log.exception("yt-dlp update failed")
                self._ytdlpResult.emit(_t("Update failed: %1").replace("%1", str(exc)[:160]), "", False, False)

        threading.Thread(target=work, name="ytdlp-update", daemon=True).start()

    def _on_ytdlp_result(self, status: str, version: str, busy: bool, restart: bool) -> None:
        self._ytdlp_status = status
        self._ytdlp_restart = restart
        if version:
            self._ytdlp_version = version
        self._ytdlp_busy = busy
        self.ytdlpChanged.emit()

    @Slot()
    def restartApp(self) -> None:  # noqa: N802
        cmd = paths.launch_command()
        try:
            env = dict(os.environ)
            env["NOCTURNE_RESTART"] = "1"
            subprocess.Popen(cmd, env=env, close_fds=True)  # noqa: S603
        except OSError:
            log.exception("Restart failed")
            return
        self.quit()

    @Slot()
    def installKdeWidget(self) -> None:  # noqa: N802
        from nocturne.platform import linux

        candidates = [
            paths.resource("extras", "plasmoid", "io.github.nocturne.widget"),  # AppImage / PyInstaller
            Path("/app/share/nocturne/plasmoid/io.github.nocturne.widget"),  # Flatpak
            paths.package_dir().parent / "packaging" / "plasmoid" / "io.github.nocturne.widget",  # source
        ]
        source = next((c for c in candidates if c.exists()), candidates[-1])
        ok, detail = linux.install_kde_widget(source)
        if ok:
            self.toast.emit(_t("KDE widget installed. Add it from “Add Widgets…”."), False)
        else:
            log.warning("KDE widget install failed: %s", detail)
            self.toast.emit(_t("Could not install the KDE widget: %1").replace("%1", detail[:120]), True)

    # ------------------------------------------------------------------ window
    @Slot()
    def showMainWindow(self) -> None:  # noqa: N802
        if self._show_window_cb:
            self._show_window_cb()

    @Slot(result=bool)
    def handleCloseRequest(self) -> bool:  # noqa: N802
        """Returns True if the window may close (app quits); otherwise it is hidden."""
        keep = (
            self._settings.value("keepRunningInTray")
            if self._tray_available
            else self._settings.value("keepRunningWithoutTray")
        )
        if keep:
            if self._hide_window_cb:
                QTimer.singleShot(0, self._hide_window_cb)
            return False
        QTimer.singleShot(0, self.quit)
        return True

    @Slot()
    def toggleMiniPlayer(self) -> None:  # noqa: N802
        self._set_mini_visible(not self._mini_visible)

    @Slot()
    def toggleDesktopWidget(self) -> None:  # noqa: N802
        self._settings.set_value("widgetVisible", not self._settings.value("widgetVisible"))

    @Slot()
    def quit(self) -> None:
        if self._quit_cb:
            self._quit_cb()
