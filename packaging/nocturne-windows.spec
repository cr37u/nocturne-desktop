# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec — Windows --onedir build, windowed, with version resource and icon.
#   pyinstaller --noconfirm --clean packaging/nocturne-windows.spec

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
    hiddenimports=common.hidden_imports(),
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
    name="Nocturne",
    icon=str(ROOT / "nocturne" / "assets" / "icons" / "nocturne.ico"),
    version=str(ROOT / "build" / "version_info.txt"),
    console=False,
    disable_windowed_traceback=False,
    upx=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="Nocturne",
)
