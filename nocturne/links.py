"""Recognise and normalise YouTube links (videos, shorts, music, playlists)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import parse_qs, urlparse

_VIDEO_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")
_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "music.youtube.com",
    "youtu.be",
    "www.youtu.be",
    "youtube-nocookie.com",
    "www.youtube-nocookie.com",
}
# Auto-generated mixes/radios: when a video id is present we treat these as a single video.
_AUTO_LIST_PREFIXES = ("RD", "UL", "LL", "WL")


@dataclass(frozen=True, slots=True)
class YouTubeLink:
    kind: str  # "video" | "playlist"
    id: str
    url: str


def parse(text: str) -> YouTubeLink | None:
    """Return the YouTube link contained in ``text`` or ``None``."""
    if not text:
        return None
    candidate = text.strip().split()[0] if text.strip() else ""
    if not candidate:
        return None
    if "://" not in candidate:
        candidate = "https://" + candidate
    try:
        url = urlparse(candidate)
    except ValueError:
        return None
    host = (url.hostname or "").lower()
    if host not in _HOSTS:
        return None

    query = parse_qs(url.query)
    video_id: str | None = None
    if host.endswith("youtu.be"):
        video_id = url.path.strip("/").split("/")[0] or None
    elif url.path == "/watch":
        video_id = (query.get("v") or [None])[0]
    else:
        parts = [p for p in url.path.split("/") if p]
        if len(parts) >= 2 and parts[0] in ("shorts", "embed", "live", "v"):
            video_id = parts[1]

    list_id = (query.get("list") or [None])[0]
    if list_id and not (video_id and list_id.startswith(_AUTO_LIST_PREFIXES)):
        return YouTubeLink("playlist", list_id, f"https://www.youtube.com/playlist?list={list_id}")
    if video_id and _VIDEO_ID.match(video_id):
        return YouTubeLink("video", video_id, f"https://www.youtube.com/watch?v={video_id}")
    return None


def video_url(video_id: str) -> str:
    return f"https://www.youtube.com/watch?v={video_id}"
