"""SQLite storage for tracks, playlists, the play queue and settings."""

from __future__ import annotations

import json
import logging
import sqlite3
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

log = logging.getLogger(__name__)

SCHEMA_VERSION = 1

_SCHEMA = """
CREATE TABLE IF NOT EXISTS tracks (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    video_id    TEXT NOT NULL UNIQUE,
    title       TEXT NOT NULL,
    artist      TEXT NOT NULL DEFAULT '',
    duration    REAL NOT NULL DEFAULT 0,
    file_path   TEXT NOT NULL,
    thumb_path  TEXT NOT NULL DEFAULT '',
    file_size   INTEGER NOT NULL DEFAULT 0,
    source_url  TEXT NOT NULL DEFAULT '',
    added_at    TEXT NOT NULL,
    favorite    INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_tracks_added ON tracks(added_at);

CREATE TABLE IF NOT EXISTS playlists (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    color_index INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT NOT NULL,
    source_id   TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS playlist_tracks (
    playlist_id INTEGER NOT NULL REFERENCES playlists(id) ON DELETE CASCADE,
    track_id    INTEGER NOT NULL REFERENCES tracks(id) ON DELETE CASCADE,
    position    INTEGER NOT NULL,
    PRIMARY KEY (playlist_id, track_id)
);
CREATE INDEX IF NOT EXISTS idx_pt_track ON playlist_tracks(track_id);

CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""

SORT_SQL = {
    "recent": "t.added_at DESC, t.id DESC",
    "title": "t.title COLLATE NOCASE ASC",
    "artist": "t.artist COLLATE NOCASE ASC, t.title COLLATE NOCASE ASC",
    "duration": "t.duration DESC",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass(slots=True)
class Track:
    id: int
    video_id: str
    title: str
    artist: str
    duration: float
    file_path: str
    thumb_path: str
    file_size: int
    source_url: str
    added_at: str
    favorite: bool
    playlist_name: str = ""
    playlist_ids: list[int] = field(default_factory=list)

    @property
    def exists(self) -> bool:
        return Path(self.file_path).is_file()


@dataclass(slots=True)
class Playlist:
    id: int
    name: str
    color_index: int
    created_at: str
    track_count: int = 0
    duration: float = 0.0
    source_id: str = ""


_TRACK_COLUMNS = (
    "t.id, t.video_id, t.title, t.artist, t.duration, t.file_path, t.thumb_path, t.file_size, "
    "t.source_url, t.added_at, t.favorite, "
    "COALESCE((SELECT p.name FROM playlist_tracks pt JOIN playlists p ON p.id = pt.playlist_id "
    "WHERE pt.track_id = t.id ORDER BY p.id LIMIT 1), '') AS playlist_name"
)


def _row_to_track(row: sqlite3.Row) -> Track:
    return Track(
        id=row["id"],
        video_id=row["video_id"],
        title=row["title"],
        artist=row["artist"],
        duration=float(row["duration"] or 0),
        file_path=row["file_path"],
        thumb_path=row["thumb_path"] or "",
        file_size=int(row["file_size"] or 0),
        source_url=row["source_url"] or "",
        added_at=row["added_at"],
        favorite=bool(row["favorite"]),
        playlist_name=row["playlist_name"] or "",
    )


class Database:
    """Thread-safe wrapper around a single SQLite connection."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(str(path), check_same_thread=False, isolation_level=None)
        self._conn.row_factory = sqlite3.Row
        with self._lock:
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA foreign_keys=ON")
            self._conn.executescript(_SCHEMA)
            self._conn.execute(f"PRAGMA user_version={SCHEMA_VERSION}")
        log.info("Database opened at %s", path)

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    # ------------------------------------------------------------------ helpers
    def _query(self, sql: str, params: Iterable[Any] = ()) -> list[sqlite3.Row]:
        with self._lock:
            return self._conn.execute(sql, tuple(params)).fetchall()

    def _exec(self, sql: str, params: Iterable[Any] = ()) -> sqlite3.Cursor:
        with self._lock:
            return self._conn.execute(sql, tuple(params))

    # ------------------------------------------------------------------ tracks
    def list_tracks(
        self,
        *,
        sort: str = "recent",
        search: str = "",
        favorites_only: bool = False,
        playlist_id: int | None = None,
    ) -> list[Track]:
        where: list[str] = []
        params: list[Any] = []
        join = ""
        order = SORT_SQL.get(sort, SORT_SQL["recent"])
        if playlist_id is not None:
            join = "JOIN playlist_tracks fpt ON fpt.track_id = t.id AND fpt.playlist_id = ?"
            params.append(playlist_id)
            if sort == "recent":
                order = "fpt.position ASC"
        if favorites_only:
            where.append("t.favorite = 1")
        if search.strip():
            like = f"%{search.strip()}%"
            where.append("(t.title LIKE ? OR t.artist LIKE ?)")
            params.extend([like, like])
        sql = f"SELECT {_TRACK_COLUMNS} FROM tracks t {join}"
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += f" ORDER BY {order}"
        return [_row_to_track(r) for r in self._query(sql, params)]

    def get_track(self, track_id: int) -> Track | None:
        rows = self._query(f"SELECT {_TRACK_COLUMNS} FROM tracks t WHERE t.id = ?", [track_id])
        return _row_to_track(rows[0]) if rows else None

    def get_tracks(self, ids: Iterable[int]) -> dict[int, Track]:
        ids = list(dict.fromkeys(int(i) for i in ids))
        result: dict[int, Track] = {}
        for start in range(0, len(ids), 500):
            chunk = ids[start : start + 500]
            marks = ",".join("?" * len(chunk))
            for row in self._query(f"SELECT {_TRACK_COLUMNS} FROM tracks t WHERE t.id IN ({marks})", chunk):
                track = _row_to_track(row)
                result[track.id] = track
        return result

    def track_by_video_id(self, video_id: str) -> Track | None:
        rows = self._query(f"SELECT {_TRACK_COLUMNS} FROM tracks t WHERE t.video_id = ?", [video_id])
        return _row_to_track(rows[0]) if rows else None

    def existing_video_ids(self, video_ids: Iterable[str]) -> set[str]:
        ids = list(video_ids)
        found: set[str] = set()
        for start in range(0, len(ids), 500):
            chunk = ids[start : start + 500]
            marks = ",".join("?" * len(chunk))
            for row in self._query(f"SELECT video_id FROM tracks WHERE video_id IN ({marks})", chunk):
                found.add(row["video_id"])
        return found

    def add_track(
        self,
        *,
        video_id: str,
        title: str,
        artist: str,
        duration: float,
        file_path: str,
        thumb_path: str,
        file_size: int,
        source_url: str,
    ) -> int:
        with self._lock:
            existing = self._conn.execute("SELECT id FROM tracks WHERE video_id = ?", (video_id,)).fetchone()
            if existing:
                self._conn.execute(
                    "UPDATE tracks SET title=?, artist=?, duration=?, file_path=?, thumb_path=?, file_size=?, "
                    "source_url=? WHERE id=?",
                    (title, artist, duration, file_path, thumb_path, file_size, source_url, existing["id"]),
                )
                return int(existing["id"])
            cur = self._conn.execute(
                "INSERT INTO tracks (video_id, title, artist, duration, file_path, thumb_path, file_size, "
                "source_url, added_at) VALUES (?,?,?,?,?,?,?,?,?)",
                (video_id, title, artist, duration, file_path, thumb_path, file_size, source_url, now_iso()),
            )
            return int(cur.lastrowid)

    def set_favorite(self, track_id: int, favorite: bool) -> None:
        self._exec("UPDATE tracks SET favorite = ? WHERE id = ?", [1 if favorite else 0, track_id])

    def delete_tracks(self, ids: Iterable[int]) -> list[Track]:
        tracks = list(self.get_tracks(ids).values())
        with self._lock:
            self._conn.execute("BEGIN")
            try:
                for t in tracks:
                    self._conn.execute("DELETE FROM tracks WHERE id = ?", (t.id,))
                self._conn.execute("COMMIT")
            except Exception:
                self._conn.execute("ROLLBACK")
                raise
        return tracks

    def library_stats(self) -> tuple[int, float, int]:
        row = self._query("SELECT COUNT(*) c, COALESCE(SUM(duration),0) d, COALESCE(SUM(file_size),0) s FROM tracks")[0]
        return int(row["c"]), float(row["d"]), int(row["s"])

    def recent_tracks(self, limit: int = 2) -> list[Track]:
        rows = self._query(f"SELECT {_TRACK_COLUMNS} FROM tracks t ORDER BY t.added_at DESC, t.id DESC LIMIT ?", [limit])
        return [_row_to_track(r) for r in rows]

    # --------------------------------------------------------------- playlists
    def list_playlists(self) -> list[Playlist]:
        rows = self._query(
            "SELECT p.id, p.name, p.color_index, p.created_at, p.source_id, COUNT(t.id) AS n, "
            "COALESCE(SUM(t.duration),0) AS d FROM playlists p "
            "LEFT JOIN playlist_tracks pt ON pt.playlist_id = p.id "
            "LEFT JOIN tracks t ON t.id = pt.track_id GROUP BY p.id ORDER BY p.id"
        )
        return [
            Playlist(
                id=r["id"],
                name=r["name"],
                color_index=r["color_index"],
                created_at=r["created_at"],
                track_count=int(r["n"]),
                duration=float(r["d"]),
                source_id=r["source_id"],
            )
            for r in rows
        ]

    def get_playlist(self, playlist_id: int) -> Playlist | None:
        return next((p for p in self.list_playlists() if p.id == playlist_id), None)

    def playlist_by_source(self, source_id: str) -> Playlist | None:
        if not source_id:
            return None
        return next((p for p in self.list_playlists() if p.source_id == source_id), None)

    def create_playlist(self, name: str, source_id: str = "") -> int:
        with self._lock:
            count = self._conn.execute("SELECT COUNT(*) FROM playlists").fetchone()[0]
            cur = self._conn.execute(
                "INSERT INTO playlists (name, color_index, created_at, source_id) VALUES (?,?,?,?)",
                (name.strip() or "Playlist", int(count) % 6, now_iso(), source_id),
            )
            return int(cur.lastrowid)

    def rename_playlist(self, playlist_id: int, name: str) -> None:
        if name.strip():
            self._exec("UPDATE playlists SET name = ? WHERE id = ?", [name.strip(), playlist_id])

    def delete_playlist(self, playlist_id: int) -> None:
        self._exec("DELETE FROM playlists WHERE id = ?", [playlist_id])

    def add_to_playlist(self, playlist_id: int, track_ids: Iterable[int]) -> int:
        added = 0
        with self._lock:
            pos = self._conn.execute(
                "SELECT COALESCE(MAX(position), -1) FROM playlist_tracks WHERE playlist_id = ?", (playlist_id,)
            ).fetchone()[0]
            for tid in track_ids:
                pos += 1
                cur = self._conn.execute(
                    "INSERT OR IGNORE INTO playlist_tracks (playlist_id, track_id, position) VALUES (?,?,?)",
                    (playlist_id, int(tid), pos),
                )
                added += cur.rowcount
        return added

    def remove_from_playlist(self, playlist_id: int, track_ids: Iterable[int]) -> None:
        with self._lock:
            for tid in track_ids:
                self._conn.execute(
                    "DELETE FROM playlist_tracks WHERE playlist_id = ? AND track_id = ?", (playlist_id, int(tid))
                )

    # ---------------------------------------------------------------- settings
    def get_setting(self, key: str, default: Any = None) -> Any:
        rows = self._query("SELECT value FROM settings WHERE key = ?", [key])
        if not rows:
            return default
        try:
            return json.loads(rows[0]["value"])
        except (ValueError, TypeError):
            return default

    def set_setting(self, key: str, value: Any) -> None:
        self._exec(
            "INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            [key, json.dumps(value)],
        )
