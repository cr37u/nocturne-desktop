"""Filesystem locations used by Nocturne (data dir, music dir, bundled resources)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from nocturne import APP_NAME

IS_WINDOWS = sys.platform == "win32"
IS_LINUX = sys.platform.startswith("linux")
IS_FROZEN = bool(getattr(sys, "frozen", False))


def package_dir() -> Path:
    """Directory that contains the ``nocturne`` package resources (qml, assets, i18n)."""
    if IS_FROZEN:
        base = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
        return base / "nocturne"
    return Path(__file__).resolve().parent


def resource(*parts: str) -> Path:
    return package_dir().joinpath(*parts)


def app_data_dir() -> Path:
    """Per-user data directory (database, logs, thumbnails)."""
    if IS_WINDOWS:
        base = Path(os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming")
        path = base / APP_NAME
    else:
        base = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share")
        path = base / "nocturne"
    path.mkdir(parents=True, exist_ok=True)
    return path


def logs_dir() -> Path:
    path = app_data_dir() / "logs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def thumbs_dir() -> Path:
    path = app_data_dir() / "thumbs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def database_path() -> Path:
    return app_data_dir() / "nocturne.db"


def _windows_music_dir() -> Path:
    """Resolve FOLDERID_Music through the shell (handles redirected/OneDrive folders)."""
    try:
        import ctypes
        from ctypes import wintypes
        import uuid

        class GUID(ctypes.Structure):
            _fields_ = [
                ("Data1", wintypes.DWORD),
                ("Data2", wintypes.WORD),
                ("Data3", wintypes.WORD),
                ("Data4", ctypes.c_ubyte * 8),
            ]

        raw = uuid.UUID("{4BD8D571-6D19-48D3-BE97-422220080E43}").bytes_le
        guid = GUID.from_buffer_copy(raw)
        out = ctypes.c_wchar_p()
        shell32 = ctypes.windll.shell32
        ole32 = ctypes.windll.ole32
        if shell32.SHGetKnownFolderPath(ctypes.byref(guid), 0, None, ctypes.byref(out)) == 0:
            value = out.value
            ole32.CoTaskMemFree(out)
            if value:
                return Path(value)
    except Exception:  # noqa: BLE001 - fall back to the conventional location
        pass
    return Path(os.environ.get("USERPROFILE") or Path.home()) / "Music"


def _xdg_music_dir() -> Path:
    config = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    user_dirs = config / "user-dirs.dirs"
    try:
        for line in user_dirs.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("XDG_MUSIC_DIR="):
                value = line.split("=", 1)[1].strip().strip('"')
                value = value.replace("$HOME", str(Path.home()))
                path = Path(os.path.expandvars(value))
                if str(path) and path != Path.home():
                    return path
    except OSError:
        pass
    return Path.home() / "Music"


def default_download_dir() -> Path:
    base = _windows_music_dir() if IS_WINDOWS else _xdg_music_dir()
    return base / APP_NAME


def is_msix_packaged() -> bool:
    """True when running inside an MSIX package (the "full" Windows edition)."""
    if not IS_WINDOWS:
        return False
    try:
        import ctypes

        length = ctypes.c_uint32(0)
        rc = ctypes.windll.kernel32.GetCurrentPackageFullName(ctypes.byref(length), None)
        return rc != 15700  # APPMODEL_ERROR_NO_PACKAGE
    except Exception:  # noqa: BLE001
        return False


def launch_command() -> list[str]:
    """Command line that starts Nocturne (used for autostart and protocol registration)."""
    appimage = os.environ.get("APPIMAGE")
    if appimage:
        return [appimage]
    if IS_FROZEN:
        return [sys.executable]
    exe = Path(sys.executable)
    if IS_WINDOWS:
        pythonw = exe.with_name("pythonw.exe")
        if pythonw.exists():
            exe = pythonw
    return [str(exe), "-m", "nocturne"]
