#!/usr/bin/env bash
# Build Nocturne for Linux: PyInstaller onedir -> AppImage (runs on any distribution).
#
# IMPORTANT: build on an OLD glibc base so the result runs everywhere (Fedora, Ubuntu, Debian,
# Arch, openSUSE, Mint, ...). The GitHub workflow uses the python:3.12-bullseye container
# (glibc 2.31, same as Ubuntu 20.04). Locally:
#
#   docker run --rm -v "$PWD":/src -w /src python:3.12-bullseye bash packaging/build_linux.sh
#
# Output: dist/Nocturne-<version>-x86_64.AppImage
# Runtime requirement: libfuse2 (or run the AppImage with --appimage-extract-and-run).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
PYTHON="${PYTHON:-python3.12}"
command -v "$PYTHON" >/dev/null 2>&1 || PYTHON=python3

if [ "$(id -u)" = "0" ] && command -v apt-get >/dev/null 2>&1; then
    echo "==> System libraries needed by Qt (bundled into the AppImage)"
    apt-get update -qq
    DEBIAN_FRONTEND=noninteractive apt-get install -y -qq --no-install-recommends \
        file wget ca-certificates binutils libfuse2 desktop-file-utils \
        libgl1 libegl1 libglib2.0-0 libfontconfig1 libfreetype6 libdbus-1-3 \
        libxkbcommon0 libxkbcommon-x11-0 libxcb1 libxcb-cursor0 libxcb-icccm4 libxcb-image0 \
        libxcb-keysyms1 libxcb-randr0 libxcb-render-util0 libxcb-shape0 libxcb-xfixes0 \
        libxcb-xinerama0 libxcb-xkb1 libxcb-sync1 libxcb-shm0 libxcb-util1 libx11-xcb1 libxrender1 libxi6 \
        libwayland-client0 libwayland-cursor0 libwayland-egl1 \
        libpulse0 libasound2 libpipewire-0.3-0 >/dev/null || true
fi

echo "==> Python environment"
if [ ! -x .venv-linux/bin/python ]; then
    "$PYTHON" -m venv .venv-linux
fi
PY="$ROOT/.venv-linux/bin/python"
"$PY" -m pip install --disable-pip-version-check -q --upgrade pip
"$PY" -m pip install --disable-pip-version-check -q -r requirements-build.txt

echo "==> Assets and translations"
QT_QPA_PLATFORM=offscreen "$PY" tools/make_assets.py
"$PY" tools/i18n_tool.py release
VERSION="$("$PY" -c 'import nocturne; print(nocturne.__version__)')"

echo "==> PyInstaller (Nocturne $VERSION)"
"$PY" -m PyInstaller --noconfirm --clean --distpath dist --workpath build/pyinstaller-linux packaging/nocturne-linux.spec

echo "==> AppDir"
APPDIR="$ROOT/build/AppDir"
rm -rf "$APPDIR"
mkdir -p "$APPDIR/usr/lib/nocturne" "$APPDIR/usr/bin" "$APPDIR/usr/share/applications" \
         "$APPDIR/usr/share/metainfo" "$APPDIR/usr/share/icons"
cp -a dist/nocturne/. "$APPDIR/usr/lib/nocturne/"
ln -s ../lib/nocturne/nocturne "$APPDIR/usr/bin/nocturne"
cp -a packaging/linux/icons/hicolor "$APPDIR/usr/share/icons/"
cp packaging/linux/io.github.nocturne.desktop "$APPDIR/usr/share/applications/"
cp packaging/linux/io.github.nocturne.desktop "$APPDIR/"
cp packaging/linux/io.github.nocturne.metainfo.xml "$APPDIR/usr/share/metainfo/"
cp packaging/linux/icons/hicolor/256x256/apps/io.github.nocturne.png "$APPDIR/io.github.nocturne.png"
ln -sf io.github.nocturne.png "$APPDIR/.DirIcon"
install -m 0755 packaging/linux/AppRun "$APPDIR/AppRun"
command -v desktop-file-validate >/dev/null 2>&1 && desktop-file-validate "$APPDIR/io.github.nocturne.desktop" || true

echo "==> appimagetool"
TOOL="$ROOT/build/appimagetool-x86_64.AppImage"
if [ ! -x "$TOOL" ]; then
    wget -q -O "$TOOL" "https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage"
    chmod +x "$TOOL"
fi
mkdir -p dist
OUT="dist/Nocturne-$VERSION-x86_64.AppImage"
ARCH=x86_64 "$TOOL" --appimage-extract-and-run --no-appstream "$APPDIR" "$OUT"
chmod +x "$OUT"

echo ""
echo "Done: $OUT"
echo "Run it with:  chmod +x $OUT && ./$OUT"
echo "(needs libfuse2; otherwise: ./$OUT --appimage-extract-and-run)"
