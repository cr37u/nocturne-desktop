"""Playback engine: QMediaPlayer + queue, shuffle, repeat and state persistence."""

from __future__ import annotations

import logging
import random
from pathlib import Path
from typing import Any

from PySide6.QtCore import Property, QCoreApplication, QObject, QTimer, QUrl, Signal, Slot
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer

from nocturne.db import Database, Track
from nocturne.models import QueueModel, artwork_url, track_to_dict
from nocturne.settings import SettingsType

log = logging.getLogger(__name__)

REPEAT_OFF, REPEAT_ALL, REPEAT_ONE = 0, 1, 2
RESTART_THRESHOLD_MS = 3000


def _t(text: str) -> str:
    return QCoreApplication.translate("Player", text)


class PlayerController(QObject):
    currentTrackChanged = Signal()
    playingChanged = Signal()
    positionChanged = Signal()
    durationChanged = Signal()
    volumeChanged = Signal()
    mutedChanged = Signal()
    shuffleChanged = Signal()
    repeatModeChanged = Signal()
    queueChanged = Signal()
    seeked = Signal(int)
    message = Signal(str, bool)

    def __init__(self, db: Database, settings: SettingsType, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._db = db
        self._settings = settings
        self._audio = QAudioOutput(self)
        self._player = QMediaPlayer(self)
        self._player.setAudioOutput(self._audio)

        self._queue: list[int] = []
        self._original: list[int] = []
        self._index = -1
        self._tracks: dict[int, Track] = {}
        self._current: Track | None = None
        self._pending_position: int | None = None
        self._pending_play = False
        self._error_streak = 0
        self._shuffle = False
        self._repeat = REPEAT_OFF
        self._volume = float(settings.value("volume"))
        self._muted = False
        self._audio.setVolume(self._volume_curve(self._volume))

        self.queueModel = QueueModel(self)

        self._player.playbackStateChanged.connect(lambda _s: self.playingChanged.emit())
        self._player.positionChanged.connect(lambda _p: self.positionChanged.emit())
        self._player.durationChanged.connect(lambda _d: self.durationChanged.emit())
        self._player.mediaStatusChanged.connect(self._on_media_status)
        self._player.errorOccurred.connect(self._on_error)

        self._save_timer = QTimer(self)
        self._save_timer.setInterval(5000)
        self._save_timer.timeout.connect(self.save_state)
        self._save_timer.start()

    # ---------------------------------------------------------------- helpers
    @staticmethod
    def _volume_curve(v: float) -> float:
        v = max(0.0, min(1.0, v))
        return v * v  # perceptual (roughly logarithmic) loudness

    def _track(self, track_id: int) -> Track | None:
        track = self._tracks.get(track_id)
        if track is None:
            track = self._db.get_track(track_id)
            if track is not None:
                self._tracks[track_id] = track
        return track

    def _refresh_queue_model(self) -> None:
        upcoming = self._queue[self._index + 1 :] if self._index >= 0 else list(self._queue)
        offset = self._index + 1 if self._index >= 0 else 0
        missing = [tid for tid in upcoming if tid not in self._tracks]
        if missing:
            self._tracks.update(self._db.get_tracks(missing))
        items = []
        for i, tid in enumerate(upcoming):
            t = self._tracks.get(tid)
            if t is None:
                continue
            items.append(
                {
                    "trackId": t.id,
                    "title": t.title,
                    "artist": t.artist,
                    "duration": t.duration,
                    "artwork": artwork_url(t.thumb_path),
                    "colorSeed": t.id % 8,
                    "queueIndex": offset + i,
                }
            )
        self.queueModel.reset(items)
        self.queueChanged.emit()

    # ------------------------------------------------------------- properties
    def _get_current(self) -> dict[str, Any]:
        return track_to_dict(self._current)

    def _get_has_track(self) -> bool:
        return self._current is not None

    def _get_playing(self) -> bool:
        return self._player.playbackState() == QMediaPlayer.PlaybackState.PlayingState

    def _get_position(self) -> int:
        if self._pending_position is not None:
            return self._pending_position
        return int(self._player.position())

    def _get_duration(self) -> int:
        dur = int(self._player.duration())
        if dur <= 0 and self._current is not None:
            return int(self._current.duration * 1000)
        return dur

    def _get_volume(self) -> float:
        return self._volume

    def _set_volume(self, value: float) -> None:
        value = max(0.0, min(1.0, float(value)))
        if abs(value - self._volume) < 1e-4:
            return
        self._volume = value
        self._audio.setVolume(self._volume_curve(value))
        if value > 0 and self._muted:
            self._muted = False
            self._audio.setMuted(False)
            self.mutedChanged.emit()
        self._settings.set_value("volume", value)
        self.volumeChanged.emit()

    def _get_muted(self) -> bool:
        return self._muted

    def _get_shuffle(self) -> bool:
        return self._shuffle

    def _get_repeat(self) -> int:
        return self._repeat

    def _get_queue_model(self) -> QObject:
        return self.queueModel

    def _get_queue_length(self) -> int:
        return len(self._queue)

    currentTrack = Property("QVariantMap", _get_current, notify=currentTrackChanged)
    hasTrack = Property(bool, _get_has_track, notify=currentTrackChanged)
    playing = Property(bool, _get_playing, notify=playingChanged)
    position = Property(int, _get_position, notify=positionChanged)
    duration = Property(int, _get_duration, notify=durationChanged)
    volume = Property(float, _get_volume, _set_volume, notify=volumeChanged)
    muted = Property(bool, _get_muted, notify=mutedChanged)
    shuffle = Property(bool, _get_shuffle, notify=shuffleChanged)
    repeatMode = Property(int, _get_repeat, notify=repeatModeChanged)
    queue = Property(QObject, _get_queue_model, constant=True)
    queueLength = Property(int, _get_queue_length, notify=queueChanged)

    @property
    def current(self) -> Track | None:
        return self._current

    # ------------------------------------------------------------------ core
    def _load(self, index: int, play: bool, position: int | None = None) -> None:
        if not 0 <= index < len(self._queue):
            return
        self._index = index
        track = self._track(self._queue[index])
        if track is None or not Path(track.file_path).is_file():
            title = track.title if track else "?"
            log.warning("Missing file for track %s", title)
            self.message.emit(_t("File not found: %1").replace("%1", title), True)
            self._queue.pop(index)
            if self._queue:
                self._load(min(index, len(self._queue) - 1), play)
            else:
                self._stop_empty()
            return
        self._current = track
        self._pending_position = position if position else None
        self._pending_play = play
        self._player.setSource(QUrl.fromLocalFile(track.file_path))
        if play and self._pending_position is None:
            self._player.play()
        self.currentTrackChanged.emit()
        self.durationChanged.emit()
        self.positionChanged.emit()
        self._refresh_queue_model()
        self.save_state()

    def _stop_empty(self) -> None:
        self._player.stop()
        self._player.setSource(QUrl())
        self._current = None
        self._index = -1
        self.currentTrackChanged.emit()
        self._refresh_queue_model()

    def _on_media_status(self, status: QMediaPlayer.MediaStatus) -> None:
        if status in (QMediaPlayer.MediaStatus.LoadedMedia, QMediaPlayer.MediaStatus.BufferedMedia):
            self._error_streak = 0
            if self._pending_position is not None:
                pos = self._pending_position
                self._pending_position = None
                self._player.setPosition(pos)
                if self._pending_play:
                    self._player.play()
                self.positionChanged.emit()
            self.durationChanged.emit()
        elif status == QMediaPlayer.MediaStatus.EndOfMedia:
            self._on_end_of_media()

    def _on_end_of_media(self) -> None:
        if self._repeat == REPEAT_ONE:
            self._player.setPosition(0)
            self._player.play()
            self.seeked.emit(0)
            return
        if self._index + 1 < len(self._queue):
            self._load(self._index + 1, play=True)
        elif self._repeat == REPEAT_ALL and self._queue:
            if self._shuffle:
                self._reshuffle(keep_current=False)
            self._load(0, play=True)
        else:
            # End of queue: rewind the last track and stop.
            self._player.stop()
            self._player.setPosition(0)
            self.positionChanged.emit()

    def _on_error(self, error: QMediaPlayer.Error, text: str) -> None:
        if error == QMediaPlayer.Error.NoError:
            return
        log.error("Playback error %s: %s", error, text)
        self.message.emit(_t("Cannot play this file: %1").replace("%1", text or str(error)), True)
        self._error_streak += 1
        if self._error_streak < max(1, len(self._queue)) and self._index + 1 < len(self._queue):
            QTimer.singleShot(300, lambda: self._load(self._index + 1, play=True))

    def _reshuffle(self, keep_current: bool) -> None:
        current = self._queue[self._index] if keep_current and 0 <= self._index < len(self._queue) else None
        others = [t for t in self._original if t != current]
        random.shuffle(others)
        self._queue = ([current] if current is not None else []) + others
        self._index = 0 if current is not None else -1

    # ------------------------------------------------------------------ slots
    @Slot(int, "QVariantList")
    def playTrack(self, track_id: int, context: list[Any]) -> None:  # noqa: N802
        ids = [int(x) for x in (context or [])] or [track_id]
        if track_id not in ids:
            ids.insert(0, track_id)
        self._original = ids
        if self._shuffle:
            self._queue = list(ids)
            self._index = ids.index(track_id)
            self._reshuffle(keep_current=True)
        else:
            self._queue = list(ids)
            self._index = ids.index(track_id)
        self._load(self._index, play=True)

    @Slot("QVariantList")
    def playAll(self, ids: list[Any]) -> None:  # noqa: N802
        ids = [int(x) for x in ids or []]
        if not ids:
            return
        if self._shuffle:
            self.playTrack(random.choice(ids), ids)
        else:
            self.playTrack(ids[0], ids)

    @Slot("QVariantList")
    def shuffleAll(self, ids: list[Any]) -> None:  # noqa: N802
        ids = [int(x) for x in ids or []]
        if not ids:
            return
        if not self._shuffle:
            self._shuffle = True
            self.shuffleChanged.emit()
        self.playTrack(random.choice(ids), ids)

    @Slot()
    def togglePlay(self) -> None:  # noqa: N802
        if self._get_playing():
            self.pause()
        else:
            self.play()

    @Slot()
    def play(self) -> None:
        if self._current is None:
            if self._queue:
                self._load(max(0, self._index), play=True)
            else:
                ids = [t.id for t in self._db.list_tracks(sort=self._settings.value("sortMode"))]
                self.playAll(ids)
            return
        if self._pending_position is not None:
            self._pending_play = True
            return
        self._player.play()

    @Slot()
    def pause(self) -> None:
        self._pending_play = False
        self._player.pause()
        self.save_state()

    @Slot()
    def stop(self) -> None:
        self._player.stop()

    @Slot()
    def next(self) -> None:
        if not self._queue:
            return
        if self._index + 1 < len(self._queue):
            self._load(self._index + 1, play=True)
        else:
            if self._shuffle and self._repeat == REPEAT_ALL:
                self._reshuffle(keep_current=False)
            self._load(0, play=True)

    @Slot()
    def previous(self) -> None:
        if not self._queue:
            return
        if self._get_position() > RESTART_THRESHOLD_MS or self._index <= 0 and self._repeat != REPEAT_ALL:
            self.seek(0)
            if not self._get_playing():
                self.play()
            return
        target = self._index - 1 if self._index > 0 else len(self._queue) - 1
        self._load(target, play=True)

    @Slot(int)
    def seek(self, ms: int) -> None:
        ms = max(0, int(ms))
        if self._pending_position is not None:
            self._pending_position = ms
        else:
            self._player.setPosition(ms)
        self.positionChanged.emit()
        self.seeked.emit(ms)

    @Slot(float)
    def setVolume(self, value: float) -> None:  # noqa: N802
        self._set_volume(value)

    @Slot(float)
    def changeVolume(self, delta: float) -> None:  # noqa: N802
        self._set_volume(self._volume + delta)

    @Slot()
    def toggleMute(self) -> None:  # noqa: N802
        self._muted = not self._muted
        self._audio.setMuted(self._muted)
        self.mutedChanged.emit()

    @Slot()
    def toggleShuffle(self) -> None:  # noqa: N802
        self._shuffle = not self._shuffle
        if self._queue:
            current = self._queue[self._index] if 0 <= self._index < len(self._queue) else None
            if self._shuffle:
                self._reshuffle(keep_current=True)
            else:
                self._queue = list(self._original)
                self._index = self._queue.index(current) if current in self._queue else 0
            self._refresh_queue_model()
        self.shuffleChanged.emit()
        self.save_state()

    @Slot()
    def cycleRepeat(self) -> None:  # noqa: N802
        self._repeat = (self._repeat + 1) % 3
        self.repeatModeChanged.emit()
        self.save_state()

    @Slot(int)
    def playNext(self, track_id: int) -> None:  # noqa: N802
        if self._current is None:
            self.playTrack(track_id, [track_id])
            return
        self._remove_upcoming(track_id)
        self._queue.insert(self._index + 1, track_id)
        if track_id not in self._original:
            cur = self._original.index(self._current.id) if self._current.id in self._original else -1
            self._original.insert(cur + 1, track_id)
        self._refresh_queue_model()
        self.save_state()

    @Slot(int)
    def enqueue(self, track_id: int) -> None:
        if self._current is None:
            self.playTrack(track_id, [track_id])
            return
        self._remove_upcoming(track_id)
        self._queue.append(track_id)
        if track_id not in self._original:
            self._original.append(track_id)
        self._refresh_queue_model()
        self.save_state()

    def _remove_upcoming(self, track_id: int) -> None:
        for i in range(len(self._queue) - 1, self._index, -1):
            if self._queue[i] == track_id:
                self._queue.pop(i)

    @Slot(int)
    def playQueueIndex(self, queue_index: int) -> None:  # noqa: N802
        if 0 <= queue_index < len(self._queue):
            self._load(queue_index, play=True)

    @Slot(int)
    def removeFromQueue(self, queue_index: int) -> None:  # noqa: N802
        if not self._index < queue_index < len(self._queue):
            return
        tid = self._queue.pop(queue_index)
        if tid in self._original and tid not in self._queue:
            self._original.remove(tid)
        self._refresh_queue_model()
        self.save_state()

    @Slot(int, int)
    def moveInQueue(self, from_index: int, to_index: int) -> None:  # noqa: N802
        """Move an upcoming item (absolute queue indices, both after the current track)."""
        n = len(self._queue)
        if not (self._index < from_index < n and self._index < to_index < n) or from_index == to_index:
            self._refresh_queue_model()
            return
        tid = self._queue.pop(from_index)
        self._queue.insert(to_index, tid)
        if not self._shuffle:
            self._original = list(self._queue)
        self._refresh_queue_model()
        self.save_state()

    @Slot()
    def clearQueue(self) -> None:  # noqa: N802
        if self._current is None:
            self._queue, self._original, self._index = [], [], -1
        else:
            self._queue = [self._current.id]
            self._original = [self._current.id]
            self._index = 0
        self._refresh_queue_model()
        self.save_state()

    # ------------------------------------------------------- library events
    def refresh_track(self, track_id: int) -> None:
        track = self._db.get_track(track_id)
        if track is None:
            return
        self._tracks[track_id] = track
        if self._current is not None and self._current.id == track_id:
            self._current = track
            self.currentTrackChanged.emit()
        self._refresh_queue_model()

    def refresh_all(self) -> None:
        self._tracks.clear()
        if self._current is not None:
            self._current = self._db.get_track(self._current.id) or self._current
            self.currentTrackChanged.emit()
        self._refresh_queue_model()

    def remove_tracks(self, ids: list[int]) -> None:
        removed = set(ids)
        current_removed = self._current is not None and self._current.id in removed
        was_playing = self._get_playing()
        current_id = self._current.id if self._current else None
        for tid in removed:
            self._tracks.pop(tid, None)
        self._original = [t for t in self._original if t not in removed]
        if current_removed:
            later = [t for t in self._queue[self._index + 1 :] if t not in removed]
            earlier = [t for t in self._queue[: self._index] if t not in removed]
            self._queue = earlier + later
            self._player.stop()
            self._player.setSource(QUrl())
            self._current = None
            if self._queue:
                self._load(min(len(earlier), len(self._queue) - 1), play=was_playing)
            else:
                self._stop_empty()
        else:
            self._queue = [t for t in self._queue if t not in removed]
            self._index = self._queue.index(current_id) if current_id in self._queue else -1
            self._refresh_queue_model()
        self.save_state()

    # ------------------------------------------------------------ persistence
    @Slot()
    def save_state(self) -> None:
        self._settings.set_blob(
            "player_state",
            {
                "queue": self._queue,
                "original": self._original,
                "index": self._index,
                "position": self._get_position(),
                "shuffle": self._shuffle,
                "repeat": self._repeat,
            },
        )

    def restore_state(self) -> None:
        state = self._settings.blob("player_state", None)
        if not isinstance(state, dict):
            return
        self._shuffle = bool(state.get("shuffle", False))
        self._repeat = int(state.get("repeat", REPEAT_OFF)) % 3
        self.shuffleChanged.emit()
        self.repeatModeChanged.emit()
        queue = [int(x) for x in state.get("queue") or []]
        known = self._db.get_tracks(queue)
        self._tracks.update(known)
        index = int(state.get("index", -1))
        current_id = queue[index] if 0 <= index < len(queue) else None
        self._queue = [t for t in queue if t in known]
        self._original = [int(x) for x in state.get("original") or [] if int(x) in known] or list(self._queue)
        if current_id is None or current_id not in self._queue:
            self._refresh_queue_model()
            return
        self._load(self._queue.index(current_id), play=False, position=int(state.get("position", 0)))
