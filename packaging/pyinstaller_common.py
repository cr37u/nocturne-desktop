"""Shared PyInstaller configuration for the Windows and Linux specs."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PKG = ROOT / "nocturne"

# Qt modules Nocturne never uses: keep them out of the bundle (size + start-up time).
QT_EXCLUDE_MODULES = [
    "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets", "PySide6.QtWebEngineQuick", "PySide6.QtWebChannel",
    "PySide6.QtWebSockets", "PySide6.QtWebView", "PySide6.Qt3DCore", "PySide6.Qt3DRender", "PySide6.Qt3DInput",
    "PySide6.Qt3DLogic", "PySide6.Qt3DExtras", "PySide6.Qt3DAnimation", "PySide6.QtCharts",
    "PySide6.QtDataVisualization", "PySide6.QtGraphs", "PySide6.QtQuick3D", "PySide6.QtPdf", "PySide6.QtPdfWidgets",
    "PySide6.QtLocation", "PySide6.QtPositioning", "PySide6.QtSensors", "PySide6.QtSerialPort", "PySide6.QtSerialBus",
    "PySide6.QtBluetooth", "PySide6.QtNfc", "PySide6.QtRemoteObjects", "PySide6.QtScxml", "PySide6.QtStateMachine",
    "PySide6.QtSql", "PySide6.QtTest", "PySide6.QtDesigner", "PySide6.QtHelp", "PySide6.QtUiTools",
    "PySide6.QtTextToSpeech", "PySide6.QtSpatialAudio", "PySide6.QtHttpServer", "PySide6.QtCanvasPainter",
    "PySide6.QtOpenGLWidgets", "PySide6.QtPrintSupport", "PySide6.QtXml", "PySide6.QtConcurrent",
    "tkinter", "unittest", "pydoc_data", "matplotlib", "numpy",
]

# Path fragments of collected Qt files to drop (QML modules, plugins, translations we do not use).
QT_DROP_FRAGMENTS = [
    "WebEngine", "QtWebView", "Qt3D", "Quick3D", "QtQuick3D", "Qt6Pdf", "QtPdf", "Charts", "DataVisualization",
    "Graphs", "Location", "Positioning", "Sensors", "SerialPort", "SerialBus", "Bluetooth", "Nfc", "RemoteObjects",
    "Scxml", "StateMachine", "Designer", "VirtualKeyboard", "TextToSpeech", "SpatialAudio", "HttpServer",
    "QtQuick/Timeline", "QtQuick/Particles", "QtQuick/Scene2D", "QtQuick/Scene3D", "QtQuick/VectorImage",
    "QtQuick/Controls/Fusion", "QtQuick/Controls/Imagine", "QtQuick/Controls/Material", "QtQuick/Controls/Universal",
    "QtQuick/Controls/FluentWinUI3", "QtQuick/Controls/Windows", "QtQuick/Controls/macOS", "QtQuick/Controls/iOS",
    "QtQuick/NativeStyle", "QtQuick/Pdf", "QtTest", "QtWebSockets", "QtWebChannel", "QtCanvasPainter",
    "qtwebengine", "Qt6Quick3D", "qtquick3d", "qtmultimedia_ar", "assistant", "linguist", "designer",
    "qtgraphs", "qtlocation", "qtwebsockets", "qtserialport",
]


def datas() -> list[tuple[str, str]]:
    from PyInstaller.utils.hooks import collect_data_files, copy_metadata

    items = [
        (str(PKG / "qml"), "nocturne/qml"),
        (str(PKG / "assets"), "nocturne/assets"),
    ]
    # yt-dlp version detection (updater) and the EJS solver scripts.
    items += copy_metadata("yt-dlp")
    items += collect_data_files("yt_dlp_ejs")
    for qm in (PKG / "i18n").glob("*.qm"):
        items.append((str(qm), "nocturne/i18n"))
    plasmoid = ROOT / "packaging" / "plasmoid"
    if sys.platform.startswith("linux") and plasmoid.exists():
        items.append((str(plasmoid), "nocturne/extras/plasmoid"))
    return items


def hidden_imports() -> list[str]:
    from PyInstaller.utils.hooks import collect_submodules

    names = [
        "PySide6.QtQuick",
        "PySide6.QtQuickControls2",
        "PySide6.QtQml",
        "PySide6.QtMultimedia",
        "PySide6.QtSvg",
        "PySide6.QtNetwork",
        "yt_dlp_ejs",
    ]
    names += collect_submodules("yt_dlp")
    names += collect_submodules("nocturne")
    if sys.platform == "win32":
        names += collect_submodules("winrt")
        names += ["comtypes", "comtypes.client", "comtypes.server"]
    else:
        names += collect_submodules("jeepney")
    return names


def keep(entry: tuple) -> bool:
    dest = str(entry[0]).replace("\\", "/")
    return not any(fragment in dest for fragment in QT_DROP_FRAGMENTS)


def filter_toc(toc: list) -> list:
    return [e for e in toc if keep(e)]
