# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec — Linux --onedir build (wrapped into an AppImage by build_linux.sh).
# Build on an OLD glibc base (Ubuntu 20.04 / manylinux_2_28) so the result runs on any distro.
#   pyinstaller --noconfirm --clean packaging/nocturne-linux.spec

import sys
from pathlib import Path

SPEC_DIR = Path(SPECPATH)
ROOT = SPEC_DIR.parent
sys.path.insert(0, str(SPEC_DIR))
sys.path.insert(0, str(ROOT))

import pyinstaller_common as common  # noqa: E402

a = Analysis(
    [str(ROOT / "packaging" / "launcher.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=common.datas(),
    hiddenimports=common.hidden_imports() + [
        # Platform plugins for X11 and Wayland are collected by the PySide6 hook;
        # these keep the DBus tray / theme integration available.
        "PySide6.QtDBus",
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=common.QT_EXCLUDE_MODULES,
    noarchive=False,
    optimize=1,
)
a.binaries = common.filter_toc(a.binaries)
a.datas = common.filter_toc(a.datas)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="nocturne",
    console=False,
    strip=False,
    upx=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="nocturne",
)
