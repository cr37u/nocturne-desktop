"""Qt item models exposed to QML (library, playlists, queue, downloads)."""

from __future__ import annotations

from typing import Any, Iterable, Sequence

from PySide6.QtCore import (
    Property,
    QAbstractListModel,
    QByteArray,
    QModelIndex,
    QObject,
    QPersistentModelIndex,
    Qt,
    QUrl,
    Signal,
    Slot,
)

from nocturne.db import Playlist, Track

_Index = QModelIndex | QPersistentModelIndex


def artwork_url(path: str) -> str:
    return QUrl.fromLocalFile(path).toString() if path else ""


def track_to_dict(track: Track | None) -> dict[str, Any]:
    if track is None:
        return {}
    return {
        "trackId": track.id,
        "videoId": track.video_id,
        "title": track.title,
        "artist": track.artist,
        "duration": track.duration,
        "playlistName": track.playlist_name,
        "addedAt": track.added_at,
        "favorite": track.favorite,
        "artwork": artwork_url(track.thumb_path) if track.thumb_path else "",
        "artworkPath": track.thumb_path,
        "filePath": track.file_path,
        "fileSize": track.file_size,
        "colorSeed": track.id % 8,
    }


class DictListModel(QAbstractListModel):
    """List model of dicts; every key in ``ROLES`` becomes a QML role."""

    ROLES: Sequence[str] = ()
    countChanged = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._items: list[dict[str, Any]] = []
        self._role_ids = {name: Qt.ItemDataRole.UserRole + 1 + i for i, name in enumerate(self.ROLES)}
        self._role_names = {v: k for k, v in self._role_ids.items()}

    def roleNames(self) -> dict[int, QByteArray]:  # noqa: N802
        return {rid: QByteArray(name.encode()) for name, rid in self._role_ids.items()}

    def rowCount(self, parent: _Index = QModelIndex()) -> int:  # noqa: N802, B008
        return 0 if parent.isValid() else len(self._items)

    def data(self, index: _Index, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid() or not 0 <= index.row() < len(self._items):
            return None
        name = self._role_names.get(role)
        return self._items[index.row()].get(name) if name else None

    def _get_count(self) -> int:
        return len(self._items)

    count = Property(int, _get_count, notify=countChanged)

    def items(self) -> list[dict[str, Any]]:
        return self._items

    def reset(self, items: Iterable[dict[str, Any]]) -> None:
        self.beginResetModel()
        self._items = list(items)
        self.endResetModel()
        self.countChanged.emit()

    def update_row(self, row: int, values: dict[str, Any]) -> None:
        if not 0 <= row < len(self._items):
            return
        item = self._items[row]
        changed = [self._role_ids[k] for k, v in values.items() if k in self._role_ids and item.get(k) != v]
        if not changed:
            return
        item.update(values)
        idx = self.index(row, 0)
        self.dataChanged.emit(idx, idx, changed)

    def append(self, item: dict[str, Any]) -> None:
        row = len(self._items)
        self.beginInsertRows(QModelIndex(), row, row)
        self._items.append(item)
        self.endInsertRows()
        self.countChanged.emit()

    def remove_row(self, row: int) -> None:
        if not 0 <= row < len(self._items):
            return
        self.beginRemoveRows(QModelIndex(), row, row)
        del self._items[row]
        self.endRemoveRows()
        self.countChanged.emit()

    @Slot(int, result="QVariantMap")
    def get(self, row: int) -> dict[str, Any]:
        return dict(self._items[row]) if 0 <= row < len(self._items) else {}


class TrackListModel(DictListModel):
    ROLES = (
        "trackId",
        "videoId",
        "title",
        "artist",
        "duration",
        "playlistName",
        "addedAt",
        "favorite",
        "artwork",
        "artworkPath",
        "filePath",
        "fileSize",
        "colorSeed",
        "isCurrent",
        "number",
    )

    totalDurationChanged = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._current_id = -1
        self._total = 0.0

    def set_tracks(self, tracks: Iterable[Track]) -> None:
        items = []
        total = 0.0
        for n, t in enumerate(tracks, start=1):
            d = track_to_dict(t)
            d["isCurrent"] = t.id == self._current_id
            d["number"] = n
            total += t.duration
            items.append(d)
        self._total = total
        self.reset(items)
        self.totalDurationChanged.emit()

    def set_current(self, track_id: int) -> None:
        old = self._current_id
        self._current_id = track_id
        for row, item in enumerate(self._items):
            if item["trackId"] in (old, track_id):
                self.update_row(row, {"isCurrent": item["trackId"] == track_id})

    def set_favorite(self, track_id: int, favorite: bool) -> None:
        for row, item in enumerate(self._items):
            if item["trackId"] == track_id:
                self.update_row(row, {"favorite": favorite})

    def _get_total(self) -> float:
        return self._total

    totalDuration = Property(float, _get_total, notify=totalDurationChanged)

    @Slot(result="QVariantList")
    def trackIds(self) -> list[int]:  # noqa: N802
        return [item["trackId"] for item in self._items]


class PlaylistListModel(DictListModel):
    ROLES = ("playlistId", "name", "colorIndex", "trackCount", "duration")

    def set_playlists(self, playlists: Iterable[Playlist]) -> None:
        self.reset(
            {
                "playlistId": p.id,
                "name": p.name,
                "colorIndex": p.color_index,
                "trackCount": p.track_count,
                "duration": p.duration,
            }
            for p in playlists
        )


class QueueModel(DictListModel):
    """Upcoming tracks ("Urmează"): ``queueIndex`` is the absolute position in the play order."""

    ROLES = ("trackId", "title", "artist", "duration", "artwork", "colorSeed", "queueIndex")


class DownloadListModel(DictListModel):
    ROLES = (
        "key",
        "videoId",
        "title",
        "artist",
        "state",
        "progress",
        "downloaded",
        "total",
        "speed",
        "error",
        "attempt",
    )

    def row_of(self, key: str) -> int:
        for row, item in enumerate(self._items):
            if item["key"] == key:
                return row
        return -1
