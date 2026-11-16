"""Entry point: ``python -m nocturne``."""

from __future__ import annotations

import os
import sys


def _fix_packaged_dll_search() -> None:
    """MSIX packages do not search PATH for DLLs, which is how PyInstaller exposes Qt's DLLs in
    ``_internal/PySide6`` to Qt's plugin loader. Switch to the explicit search order and register
    the bundle folders so plugins (e.g. Qt Quick Controls) find their dependencies."""
    if sys.platform != "win32" or not getattr(sys, "frozen", False):
        return
    import ctypes

    kernel32 = ctypes.windll.kernel32
    length = ctypes.c_uint32(0)
    if kernel32.GetCurrentPackageFullName(ctypes.byref(length), None) == 15700:  # not packaged
        return
    load_library_search_default_dirs = 0x00001000
    kernel32.SetDefaultDllDirectories.argtypes = [ctypes.c_uint32]
    kernel32.AddDllDirectory.argtypes = [ctypes.c_wchar_p]
    kernel32.AddDllDirectory.restype = ctypes.c_void_p
    kernel32.SetDefaultDllDirectories(load_library_search_default_dirs)
    base = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    for folder in (base, os.path.join(base, "PySide6"), os.path.join(base, "shiboken6")):
        if os.path.isdir(folder):
            kernel32.AddDllDirectory(folder)


def main() -> int:
    _fix_packaged_dll_search()

    # Prefer an updated yt-dlp (downloaded from the Settings page) over the bundled one.
    from nocturne import ytdlp_update

    ytdlp_update.activate_updated_ytdlp()

    from nocturne.app import run

    return run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
