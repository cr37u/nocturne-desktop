"""Keep yt-dlp current without reinstalling Nocturne.

YouTube changes often and old yt-dlp versions stop working. The official yt-dlp release
ships a zipapp (``yt-dlp``) that Python can import directly; we download it to the user
data directory and put it at the front of ``sys.path`` on the next start.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import sys
import urllib.request
import zipfile
from pathlib import Path

log = logging.getLogger(__name__)

RELEASE_API = "https://api.github.com/repos/yt-dlp/yt-dlp/releases/latest"
ZIPAPP_NAME = "yt-dlp"
SUMS_NAME = "SHA2-256SUMS"
USER_AGENT = "Nocturne-yt-dlp-updater"


def _update_dir() -> Path:
    from nocturne import paths

    path = paths.app_data_dir() / "yt-dlp"
    path.mkdir(parents=True, exist_ok=True)
    return path


def updated_zip() -> Path:
    return _update_dir() / "yt-dlp.pyz"


def _parse_version(text: str) -> tuple[int, ...]:
    return tuple(int(x) for x in re.findall(r"\d+", text)[:4])


def zip_version(path: Path) -> str | None:
    try:
        with zipfile.ZipFile(path) as zf:
            source = zf.read("yt_dlp/version.py").decode("utf-8")
        match = re.search(r"__version__\s*=\s*['\"]([^'\"]+)['\"]", source)
        return match.group(1) if match else None
    except (OSError, KeyError, zipfile.BadZipFile):
        return None


def bundled_version() -> str:
    """Version of the yt-dlp that would be imported without the update zip."""
    for entry in sys.path:
        candidate = Path(entry) / "yt_dlp" / "version.py"
        if candidate.is_file():
            match = re.search(r"__version__\s*=\s*['\"]([^'\"]+)['\"]", candidate.read_text("utf-8"))
            if match:
                return match.group(1)
    try:
        from importlib.metadata import version

        return version("yt-dlp")
    except Exception:  # noqa: BLE001
        return "0"


class _ZipFirstFinder:
    """Meta-path finder that serves ``yt_dlp`` from the downloaded zipapp.

    Needed because in a PyInstaller build the frozen importer would otherwise win over
    anything placed on ``sys.path``.
    """

    def __init__(self, zip_path: str) -> None:
        self._zip = zip_path

    def find_spec(self, fullname: str, path: object = None, target: object = None) -> object:
        if fullname != "yt_dlp" and not fullname.startswith("yt_dlp."):
            return None
        from importlib.machinery import PathFinder

        search = [self._zip] if fullname == "yt_dlp" else path
        return PathFinder.find_spec(fullname, search)  # type: ignore[arg-type]


def activate_updated_ytdlp() -> None:
    """Called before anything imports yt_dlp."""
    try:
        path = updated_zip()
        if not path.is_file():
            return
        new = zip_version(path)
        if new and _parse_version(new) > _parse_version(bundled_version()):
            sys.path.insert(0, str(path))
            sys.meta_path.insert(0, _ZipFirstFinder(str(path)))  # type: ignore[arg-type]
    except Exception:  # noqa: BLE001 - never block start-up
        pass


def current_version() -> str:
    try:
        from yt_dlp.version import __version__

        return str(__version__)
    except Exception:  # noqa: BLE001
        return "?"


def latest_release() -> tuple[str, str, str]:
    """Return (version, zipapp url, sums url) of the latest yt-dlp release."""
    req = urllib.request.Request(RELEASE_API, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    assets = {a["name"]: a["browser_download_url"] for a in data.get("assets", [])}
    if ZIPAPP_NAME not in assets:
        raise RuntimeError("Release has no zipapp asset")
    return str(data.get("tag_name", "")), assets[ZIPAPP_NAME], assets.get(SUMS_NAME, "")


def is_newer(candidate: str, current: str) -> bool:
    return _parse_version(candidate) > _parse_version(current)


def download_update(url: str, sums_url: str) -> str:
    """Download and verify the zipapp; returns the installed version."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=120) as resp:
        payload = resp.read()
    if sums_url:
        req = urllib.request.Request(sums_url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=20) as resp:
            sums = resp.read().decode("utf-8")
        expected = next(
            (line.split()[0] for line in sums.splitlines() if line.strip().endswith(" " + ZIPAPP_NAME)), None
        )
        actual = hashlib.sha256(payload).hexdigest()
        if expected and expected.lower() != actual:
            raise RuntimeError("Checksum mismatch for the downloaded yt-dlp")
    tmp = updated_zip().with_suffix(".tmp")
    tmp.write_bytes(payload)
    version = zip_version(tmp)
    if not version:
        tmp.unlink(missing_ok=True)
        raise RuntimeError("Downloaded file is not a valid yt-dlp zipapp")
    tmp.replace(updated_zip())
    log.info("yt-dlp %s downloaded", version)
    return version
