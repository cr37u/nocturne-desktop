"""Logging to a rotating file in the user data directory."""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler

from nocturne import paths

_FORMAT = "%(asctime)s %(levelname)-7s %(threadName)-14s %(name)s: %(message)s"


def setup_logging(debug: bool = False) -> None:
    root = logging.getLogger()
    if any(isinstance(h, RotatingFileHandler) for h in root.handlers):
        return
    root.setLevel(logging.DEBUG if debug else logging.INFO)

    file_handler = RotatingFileHandler(
        paths.logs_dir() / "nocturne.log", maxBytes=2 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    file_handler.setFormatter(logging.Formatter(_FORMAT))
    root.addHandler(file_handler)

    if sys.stderr is not None and not paths.IS_FROZEN:
        console = logging.StreamHandler(sys.stderr)
        console.setFormatter(logging.Formatter(_FORMAT))
        root.addHandler(console)

    def _excepthook(exc_type, exc, tb):  # type: ignore[no-untyped-def]
        logging.getLogger("nocturne").critical("Unhandled exception", exc_info=(exc_type, exc, tb))

    sys.excepthook = _excepthook
    _install_qt_handler()
    logging.getLogger("nocturne").info("Logging initialised (%s)", paths.logs_dir())


def _install_qt_handler() -> None:
    """Send Qt/QML warnings to the log file (a windowed build has no console)."""
    from PySide6.QtCore import QtMsgType, qInstallMessageHandler

    qt_log = logging.getLogger("qt")
    levels = {
        QtMsgType.QtDebugMsg: logging.DEBUG,
        QtMsgType.QtInfoMsg: logging.INFO,
        QtMsgType.QtWarningMsg: logging.WARNING,
        QtMsgType.QtCriticalMsg: logging.ERROR,
        QtMsgType.QtFatalMsg: logging.CRITICAL,
    }

    def handler(mode, context, message):  # type: ignore[no-untyped-def]
        where = f" ({context.file}:{context.line})" if context.file else ""
        qt_log.log(levels.get(mode, logging.WARNING), "%s%s", message, where)

    qInstallMessageHandler(handler)
