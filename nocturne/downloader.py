"""Download manager: resolves YouTube links with yt-dlp and downloads audio in parallel."""

from __future__ import annotations

import logging
import threading
import time
import urllib.request
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from PySide6.QtCore import Property, QCoreApplication, QObject, QTimer, Signal, Slot
from PySide6.QtGui import QImage

from nocturne import links, paths
from nocturne.db import Database
from nocturne.models import DownloadListModel
from nocturne.settings import SettingsType

log = logging.getLogger(__name__)

MAX_RETRIES = 3
JS_RUNTIMES: dict[str, dict[str, Any]] = {"deno": {}, "node": {}, "bun": {}}

FORMATS = {
    "best": "bestaudio[ext=m4a]/bestaudio[acodec=opus]/bestaudio",
    "medium": "bestaudio[ext=m4a][abr<=140]/bestaudio[acodec=opus][abr<=140]/"
    "bestaudio[ext=m4a]/bestaudio[acodec=opus]/bestaudio",
    "low": "worstaudio[ext=m4a]/worstaudio[acodec=opus]/worstaudio/bestaudio",
}

# States shared with QML
QUEUED, ACTIVE, DONE, FAILED, PAUSED, SKIPPED = "queued", "active", "done", "failed", "paused", "skipped"


def _t(text: str) -> str:
    return QCoreApplication.translate("Downloads", text)


class _Cancelled(Exception):
    """Raised from the yt-dlp progress hook to abort a download (pause / cancel)."""


@dataclass
class Batch:
    id: str
    kind: str  # "video" | "playlist"
    title: str
    source_id: str
    playlist_local_id: int | None
    keys: list[str] = field(default_factory=list)
    notified: bool = False


@dataclass
class Task:
    key: str
    video_id: str
    url: str
    title: str
    artist: str
    duration: float
    batch_id: str
    state: str = QUEUED
    progress: float = 0.0
    downloaded: float = 0.0
    total: float = 0.0
    speed: float = 0.0
    error: str = ""
    attempt: int = 0
    cancel: threading.Event = field(default_factory=threading.Event)
    last_emit: float = 0.0


def _ydl_logger() -> Any:
    class _Logger:
        def debug(self, msg: str) -> None:
            if not msg.startswith("[debug] "):
                log.debug("yt-dlp: %s", msg)

        def info(self, msg: str) -> None:
            log.debug("yt-dlp: %s", msg)

        def warning(self, msg: str) -> None:
            log.info("yt-dlp warning: %s", msg)

        def error(self, msg: str) -> None:
            log.warning("yt-dlp error: %s", msg)

    return _Logger()


def _clean_artist(info: dict[str, Any]) -> str:
    artist = info.get("artist") or info.get("creator") or info.get("channel") or info.get("uploader") or ""
    if isinstance(artist, list):
        artist = ", ".join(str(a) for a in artist)
    artist = str(artist)
    if artist.endswith(" - Topic"):
        artist = artist[: -len(" - Topic")]
    return artist.strip()


def _save_square_thumbnail(video_id: str, candidates: list[str]) -> str:
    """Download the best thumbnail and store a centered 512×512 JPEG crop."""
    target = paths.thumbs_dir() / f"{video_id}.jpg"
    if target.exists():
        return str(target)
    urls = [
        f"https://i.ytimg.com/vi/{video_id}/maxresdefault.jpg",
        f"https://i.ytimg.com/vi/{video_id}/hq720.jpg",
        *candidates,
        f"https://i.ytimg.com/vi/{video_id}/mqdefault.jpg",
    ]
    for url in urls:
        if not url:
            continue
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 Nocturne"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = resp.read()
        except Exception:  # noqa: BLE001 - try the next candidate
            continue
        image = QImage()
        if not image.loadFromData(data) or image.width() < 120:
            continue
        side = min(image.width(), image.height())
        x = (image.width() - side) // 2
        y = (image.height() - side) // 2
        square = image.copy(x, y, side, side).scaled(512, 512)
        if square.save(str(target), "JPG", 90):
            return str(target)
    return ""


class DownloadManager(QObject):
    """Owns all download tasks; thread-safe, never blocks the UI thread."""

    tasksChanged = Signal()
    statsChanged = Signal()
    analyzingChanged = Signal()
    detectedChanged = Signal()
    pausedChanged = Signal()

    trackAdded = Signal(int)  # track id
    playlistCreated = Signal(int)
    batchFinished = Signal(str, str, int, int)  # kind, title, ok, failed
    message = Signal(str, bool)  # text, is_error

    # internal cross-thread signals
    _taskUpdate = Signal(str)
    _analyzeDone = Signal(object, object, bool)  # payload, error, auto_start
    _taskFinished = Signal(str)

    def __init__(self, db: Database, settings: SettingsType, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._db = db
        self._settings = settings
        self._lock = threading.RLock()
        self._tasks: dict[str, Task] = {}
        self._order: list[str] = []
        self._batches: dict[str, Batch] = {}
        self._active = 0
        self._paused = False
        self._analyzing = 0
        self._detected: dict[str, Any] = {}
        self._detected_entries: list[dict[str, Any]] = []
        self.items_model = DownloadListModel(self)

        self._taskUpdate.connect(self._on_task_update)
        self._analyzeDone.connect(self._on_analyze_done)
        self._taskFinished.connect(self._on_task_finished)

        self._stats_timer = QTimer(self)
        self._stats_timer.setInterval(250)
        self._stats_timer.timeout.connect(self.statsChanged)
        self._stats_timer.start()

    # ------------------------------------------------------------------ props
    def _get_analyzing(self) -> bool:
        return self._analyzing > 0

    def _get_detected(self) -> dict[str, Any]:
        return self._detected

    def _get_paused(self) -> bool:
        return self._paused

    def _get_pending(self) -> int:
        with self._lock:
            return sum(1 for t in self._tasks.values() if t.state in (QUEUED, ACTIVE, PAUSED))

    def _get_total(self) -> int:
        with self._lock:
            return len(self._session_tasks())

    def _get_completed(self) -> int:
        with self._lock:
            return sum(1 for t in self._session_tasks() if t.state in (DONE, SKIPPED, FAILED))

    def _get_progress(self) -> float:
        with self._lock:
            tasks = self._session_tasks()
            if not tasks:
                return 0.0
            done = sum(1.0 if t.state in (DONE, SKIPPED, FAILED) else t.progress for t in tasks)
            return done / len(tasks)

    def _get_speed(self) -> float:
        with self._lock:
            return sum(t.speed for t in self._tasks.values() if t.state == ACTIVE)

    def _get_active_items(self) -> list[dict[str, Any]]:
        with self._lock:
            active = [t for t in self._tasks.values() if t.state == ACTIVE]
            active.sort(key=lambda t: -t.progress)
            return [{"title": t.title, "progress": t.progress} for t in active[:2]]

    def _get_busy(self) -> bool:
        with self._lock:
            return any(t.state in (QUEUED, ACTIVE) for t in self._tasks.values())

    analyzing = Property(bool, _get_analyzing, notify=analyzingChanged)
    detected = Property("QVariantMap", _get_detected, notify=detectedChanged)
    paused = Property(bool, _get_paused, notify=pausedChanged)
    pendingCount = Property(int, _get_pending, notify=statsChanged)
    totalCount = Property(int, _get_total, notify=statsChanged)
    completedCount = Property(int, _get_completed, notify=statsChanged)
    progress = Property(float, _get_progress, notify=statsChanged)
    speed = Property(float, _get_speed, notify=statsChanged)
    activeItems = Property("QVariantList", _get_active_items, notify=statsChanged)
    busy = Property(bool, _get_busy, notify=statsChanged)

    def _get_model(self) -> QObject:
        return self.items_model

    model = Property(QObject, _get_model, constant=True)

    def _session_tasks(self) -> list[Task]:
        """Tasks of the current "session": everything since the queue was last idle and cleared."""
        return [self._tasks[k] for k in self._order if k in self._tasks]

    # ------------------------------------------------------------- analysing
    @Slot(str, result=bool)
    def isValidLink(self, text: str) -> bool:  # noqa: N802
        return links.parse(text) is not None

    @Slot(str)
    def analyze(self, text: str) -> None:
        """Resolve a link and show the "detected" card (Downloads page)."""
        self._start_analyze(text, auto_start=False)

    @Slot(str, result=bool)
    def addLink(self, text: str) -> bool:  # noqa: N802
        """Resolve a link and immediately queue every new item."""
        return self._start_analyze(text, auto_start=True)

    def _start_analyze(self, text: str, auto_start: bool) -> bool:
        link = links.parse(text)
        if link is None:
            self.message.emit(_t("This is not a valid YouTube link."), True)
            return False
        self._analyzing += 1
        self.analyzingChanged.emit()
        threading.Thread(
            target=self._analyze_worker, args=(link, auto_start), name="yt-analyze", daemon=True
        ).start()
        return True

    def _analyze_worker(self, link: links.YouTubeLink, auto_start: bool) -> None:
        try:
            import yt_dlp

            opts = {
                "quiet": True,
                "no_warnings": True,
                "skip_download": True,
                "extract_flat": "in_playlist",
                "js_runtimes": JS_RUNTIMES,
                "logger": _ydl_logger(),
                "socket_timeout": 20,
            }
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(link.url, download=False, process=link.kind == "playlist")
            entries: list[dict[str, Any]] = []
            if link.kind == "playlist":
                for e in info.get("entries") or []:
                    if not e or not e.get("id") or len(str(e.get("id"))) != 11:
                        continue
                    if (e.get("title") or "") in ("[Private video]", "[Deleted video]"):
                        continue
                    entries.append(
                        {
                            "id": e["id"],
                            "title": e.get("title") or e["id"],
                            "artist": _clean_artist(e),
                            "duration": float(e.get("duration") or 0),
                        }
                    )
                title = info.get("title") or _t("Playlist")
            else:
                entries.append(
                    {
                        "id": info.get("id") or link.id,
                        "title": info.get("title") or link.id,
                        "artist": _clean_artist(info),
                        "duration": float(info.get("duration") or 0),
                    }
                )
                title = entries[0]["title"]
            existing = self._db.existing_video_ids(e["id"] for e in entries)
            with self._lock:
                queued = {t.video_id for t in self._tasks.values() if t.state in (QUEUED, ACTIVE, PAUSED)}
            payload = {
                "kind": link.kind,
                "sourceId": link.id,
                "title": title,
                "count": len(entries),
                "duration": sum(e["duration"] for e in entries),
                "existing": sum(1 for e in entries if e["id"] in existing),
                "newCount": sum(1 for e in entries if e["id"] not in existing and e["id"] not in queued),
                "entries": entries,
                "existingIds": sorted(existing),
            }
            self._analyzeDone.emit(payload, None, auto_start)
        except Exception as exc:  # noqa: BLE001
            log.exception("Analyse failed for %s", link.url)
            self._analyzeDone.emit(None, str(exc), auto_start)

    def _on_analyze_done(self, payload: dict[str, Any] | None, error: str | None, auto_start: bool) -> None:
        self._analyzing = max(0, self._analyzing - 1)
        self.analyzingChanged.emit()
        if payload is None:
            self.message.emit(_t("Could not read this link. Check your connection and try again."), True)
            return
        if not payload["entries"]:
            self.message.emit(_t("No playable videos were found at this link."), True)
            return
        if auto_start:
            self._enqueue(payload)
        else:
            self._detected_entries = payload["entries"]
            self._detected = {k: v for k, v in payload.items() if k != "entries"}
            self.detectedChanged.emit()

    @Slot()
    def downloadDetected(self) -> None:  # noqa: N802
        if not self._detected:
            return
        payload = dict(self._detected)
        payload["entries"] = self._detected_entries
        self._detected = {}
        self._detected_entries = []
        self.detectedChanged.emit()
        self._enqueue(payload)

    @Slot()
    def dismissDetected(self) -> None:  # noqa: N802
        self._detected = {}
        self._detected_entries = []
        self.detectedChanged.emit()

    # -------------------------------------------------------------- queueing
    def _enqueue(self, payload: dict[str, Any]) -> None:
        existing_ids = set(payload.get("existingIds") or [])
        playlist_local_id: int | None = None
        if payload["kind"] == "playlist":
            pl = self._db.playlist_by_source(payload["sourceId"])
            playlist_local_id = pl.id if pl else self._db.create_playlist(payload["title"], payload["sourceId"])
            if pl is None:
                self.playlistCreated.emit(playlist_local_id)
            # Tracks already in the library still join the playlist.
            if existing_ids:
                ids = [t.id for vid in existing_ids if (t := self._db.track_by_video_id(vid))]
                if ids and self._db.add_to_playlist(playlist_local_id, ids):
                    self.playlistCreated.emit(playlist_local_id)

        batch = Batch(
            id=uuid.uuid4().hex,
            kind=payload["kind"],
            title=payload["title"],
            source_id=payload["sourceId"],
            playlist_local_id=playlist_local_id,
        )
        added = 0
        with self._lock:
            if not any(t.state in (QUEUED, ACTIVE, PAUSED) for t in self._tasks.values()):
                # Previous session is complete: start counting from zero (keep the rows visible).
                self._order = []
            busy_ids = {t.video_id for t in self._tasks.values() if t.state in (QUEUED, ACTIVE, PAUSED)}
            for entry in payload["entries"]:
                vid = entry["id"]
                if vid in existing_ids or vid in busy_ids:
                    continue
                busy_ids.add(vid)
                key = uuid.uuid4().hex
                task = Task(
                    key=key,
                    video_id=vid,
                    url=links.video_url(vid),
                    title=entry["title"],
                    artist=entry["artist"],
                    duration=entry["duration"],
                    batch_id=batch.id,
                    state=PAUSED if self._paused else QUEUED,
                )
                self._tasks[key] = task
                self._order.append(key)
                batch.keys.append(key)
                self.items_model.append(self._task_dict(task))
                added += 1
            self._batches[batch.id] = batch
        if added == 0:
            self.message.emit(_t("Everything from this link is already in your library."), False)
        else:
            self.message.emit(
                QCoreApplication.translate("Downloads", "%n song(s) added to downloads.", None, added), False
            )
        self.tasksChanged.emit()
        self.statsChanged.emit()
        self._pump()

    def _task_dict(self, t: Task) -> dict[str, Any]:
        return {
            "key": t.key,
            "videoId": t.video_id,
            "title": t.title,
            "artist": t.artist,
            "state": t.state,
            "progress": t.progress,
            "downloaded": t.downloaded,
            "total": t.total,
            "speed": t.speed,
            "error": t.error,
            "attempt": t.attempt,
        }

    def _pump(self) -> None:
        limit = max(1, min(8, int(self._settings.value("parallelDownloads"))))
        with self._lock:
            if self._paused:
                return
            for key in list(self._order):
                if self._active >= limit:
                    break
                task = self._tasks.get(key)
                if task is None or task.state != QUEUED:
                    continue
                task.state = ACTIVE
                task.speed = 0.0
                task.cancel.clear()
                self._active += 1
                threading.Thread(target=self._download_worker, args=(task,), name="yt-download", daemon=True).start()
                self._taskUpdate.emit(key)

    # ------------------------------------------------------------- download
    def _download_dir(self) -> Path:
        configured = self._settings.value("downloadDir")
        path = Path(configured) if configured else paths.default_download_dir()
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _download_worker(self, task: Task) -> None:
        import yt_dlp

        quality = self._settings.value("audioQuality")
        out_dir = self._download_dir()

        def hook(d: dict[str, Any]) -> None:
            if task.cancel.is_set():
                raise _Cancelled()
            if d.get("status") == "downloading":
                total = float(d.get("total_bytes") or d.get("total_bytes_estimate") or 0)
                done = float(d.get("downloaded_bytes") or 0)
                task.downloaded = done
                task.total = total
                task.speed = float(d.get("speed") or 0)
                task.progress = min(0.99, done / total) if total else task.progress
                now = time.monotonic()
                if now - task.last_emit > 0.2:
                    task.last_emit = now
                    self._taskUpdate.emit(task.key)

        while True:
            task.attempt += 1
            opts = {
                "format": FORMATS.get(quality, FORMATS["best"]),
                "outtmpl": str(out_dir / "%(title).120B [%(id)s].%(ext)s"),
                "windowsfilenames": True,
                "quiet": True,
                "no_warnings": True,
                "noprogress": True,
                "noplaylist": True,
                "retries": 3,
                "fragment_retries": 3,
                "concurrent_fragment_downloads": 4,
                "continuedl": True,
                "overwrites": False,
                "socket_timeout": 20,
                "progress_hooks": [hook],
                "js_runtimes": JS_RUNTIMES,
                "logger": _ydl_logger(),
                "postprocessors": [],
            }
            try:
                with yt_dlp.YoutubeDL(opts) as ydl:
                    info = ydl.extract_info(task.url, download=True)
                requested = (info.get("requested_downloads") or [{}])[0]
                file_path = requested.get("filepath") or ydl.prepare_filename(info)
                if not file_path or not Path(file_path).is_file():
                    raise RuntimeError("Downloaded file is missing")
                thumb = _save_square_thumbnail(
                    task.video_id, [t.get("url", "") for t in reversed(info.get("thumbnails") or [])][:3]
                )
                title = info.get("track") or info.get("title") or task.title
                artist = _clean_artist(info) or task.artist
                track_id = self._db.add_track(
                    video_id=task.video_id,
                    title=str(title),
                    artist=artist,
                    duration=float(info.get("duration") or task.duration or 0),
                    file_path=str(Path(file_path).resolve()),
                    thumb_path=thumb,
                    file_size=Path(file_path).stat().st_size,
                    source_url=task.url,
                )
                batch = self._batches.get(task.batch_id)
                if batch and batch.playlist_local_id is not None:
                    self._db.add_to_playlist(batch.playlist_local_id, [track_id])
                task.title = str(title)
                task.artist = artist
                task.state = DONE
                task.progress = 1.0
                task.speed = 0.0
                task.error = ""
                self.trackAdded.emit(track_id)
                break
            except _Cancelled:
                task.state = PAUSED if self._paused else QUEUED
                task.speed = 0.0
                task.attempt = max(0, task.attempt - 1)
                break
            except Exception as exc:  # noqa: BLE001
                msg = str(exc).replace("ERROR: ", "").strip()
                log.warning("Download failed (%s attempt %s): %s", task.video_id, task.attempt, msg)
                if task.cancel.is_set():
                    task.state = PAUSED if self._paused else QUEUED
                    task.speed = 0.0
                    break
                if task.attempt > MAX_RETRIES:
                    task.state = FAILED
                    task.speed = 0.0
                    task.error = msg[:300]
                    break
                task.error = msg[:300]
                self._taskUpdate.emit(task.key)
                time.sleep(min(8.0, 1.5 * task.attempt))
        self._taskFinished.emit(task.key)

    # ------------------------------------------------------------ main thread
    def _on_task_update(self, key: str) -> None:
        task = self._tasks.get(key)
        row = self.items_model.row_of(key)
        if task is not None and row >= 0:
            self.items_model.update_row(row, self._task_dict(task))

    def _on_task_finished(self, key: str) -> None:
        with self._lock:
            self._active = max(0, self._active - 1)
        self._on_task_update(key)
        task = self._tasks.get(key)
        if task is not None:
            self._check_batch(task.batch_id)
        self.statsChanged.emit()
        self._pump()

    def _check_batch(self, batch_id: str) -> None:
        batch = self._batches.get(batch_id)
        if batch is None or batch.notified:
            return
        tasks = [self._tasks[k] for k in batch.keys if k in self._tasks]
        if any(t.state in (QUEUED, ACTIVE, PAUSED) for t in tasks):
            return
        batch.notified = True
        ok = sum(1 for t in tasks if t.state in (DONE, SKIPPED))
        failed = sum(1 for t in tasks if t.state == FAILED)
        self.batchFinished.emit(batch.kind, batch.title, ok, failed)

    # --------------------------------------------------------------- actions
    @Slot()
    def pauseAll(self) -> None:  # noqa: N802
        with self._lock:
            self._paused = True
            for t in self._tasks.values():
                if t.state == QUEUED:
                    t.state = PAUSED
                elif t.state == ACTIVE:
                    t.cancel.set()
            keys = list(self._tasks)
        for k in keys:
            self._on_task_update(k)
        self.pausedChanged.emit()
        self.statsChanged.emit()

    @Slot()
    def resumeAll(self) -> None:  # noqa: N802
        with self._lock:
            self._paused = False
            for t in self._tasks.values():
                if t.state == PAUSED:
                    t.state = QUEUED
            keys = list(self._tasks)
        for k in keys:
            self._on_task_update(k)
        self.pausedChanged.emit()
        self.statsChanged.emit()
        self._pump()

    @Slot(str)
    def retry(self, key: str) -> None:
        with self._lock:
            task = self._tasks.get(key)
            if task is None or task.state != FAILED:
                return
            task.state = PAUSED if self._paused else QUEUED
            task.attempt = 0
            task.error = ""
            task.progress = 0.0
            batch = self._batches.get(task.batch_id)
            if batch:
                batch.notified = False
            if key not in self._order:
                self._order.append(key)
        self._on_task_update(key)
        self.statsChanged.emit()
        self._pump()

    @Slot()
    def retryFailed(self) -> None:  # noqa: N802
        for key in [k for k, t in self._tasks.items() if t.state == FAILED]:
            self.retry(key)

    @Slot(str)
    def cancel(self, key: str) -> None:
        with self._lock:
            task = self._tasks.pop(key, None)
            if key in self._order:
                self._order.remove(key)
        if task is None:
            return
        task.cancel.set()
        row = self.items_model.row_of(key)
        self.items_model.remove_row(row)
        self._check_batch(task.batch_id)
        self.statsChanged.emit()

    @Slot()
    def clearFinished(self) -> None:  # noqa: N802
        with self._lock:
            finished = [k for k, t in self._tasks.items() if t.state in (DONE, SKIPPED)]
            for key in finished:
                self._tasks.pop(key, None)
                if key in self._order:
                    self._order.remove(key)
        for key in finished:
            self.items_model.remove_row(self.items_model.row_of(key))
        self.statsChanged.emit()

    def shutdown(self) -> None:
        with self._lock:
            for t in self._tasks.values():
                t.cancel.set()
