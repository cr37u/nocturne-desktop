"""Live language switching (Qt Linguist) and locale-aware formatting helpers."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from PySide6.QtCore import (
    Property,
    QCoreApplication,
    QDate,
    QLibraryInfo,
    QLocale,
    QObject,
    QTranslator,
    Signal,
    Slot,
)
from PySide6.QtQml import QQmlEngine

from nocturne import paths

log = logging.getLogger(__name__)

SUPPORTED = ("ro", "en", "ru")
DEFAULT_LANGUAGE = "ro"
LOCALE_NAMES = {"ro": "ro_RO", "en": "en_US", "ru": "ru_RU"}
LANGUAGE_INFO = [
    {"code": "ro", "name": "Română", "chip": "RO"},
    {"code": "en", "name": "English", "chip": "EN"},
    {"code": "ru", "name": "Русский", "chip": "RU"},
]


def tr(context: str, text: str, n: int = -1) -> str:
    return QCoreApplication.translate(context, text, None, n)


def system_language() -> str:
    for name in QLocale.system().uiLanguages():
        code = name.split("-")[0].split("_")[0].lower()
        if code in SUPPORTED:
            return code
    return DEFAULT_LANGUAGE


def resolve_language(setting: str) -> str:
    return setting if setting in SUPPORTED else system_language()


class LanguageManager(QObject):
    """Installs the right QTranslator and re-translates every QML binding on change."""

    languageChanged = Signal()
    revisionChanged = Signal()

    def __init__(self, setting: str, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._setting = setting if setting in (*SUPPORTED, "system") else "system"
        self._effective = resolve_language(self._setting)
        self._translator: QTranslator | None = None
        self._qt_translator: QTranslator | None = None
        self._engines: list[QQmlEngine] = []
        self._revision = 0
        self._install()

    # -------------------------------------------------------------- properties
    def _get_language(self) -> str:
        return self._setting

    def _get_effective(self) -> str:
        return self._effective

    def _get_revision(self) -> int:
        return self._revision

    def _get_languages(self) -> list[dict[str, str]]:
        return LANGUAGE_INFO

    language = Property(str, _get_language, notify=languageChanged)
    effectiveLanguage = Property(str, _get_effective, notify=languageChanged)
    revision = Property(int, _get_revision, notify=revisionChanged)
    languages = Property("QVariantList", _get_languages, constant=True)

    @property
    def locale(self) -> QLocale:
        return QLocale(LOCALE_NAMES[self._effective])

    def attach_engine(self, engine: QQmlEngine) -> None:
        self._engines.append(engine)

    @Slot(str)
    def setLanguage(self, setting: str) -> None:  # noqa: N802 - Qt naming
        if setting not in (*SUPPORTED, "system"):
            return
        effective = resolve_language(setting)
        changed = effective != self._effective
        self._setting = setting
        self._effective = effective
        if changed:
            self._install()
            for engine in self._engines:
                engine.retranslate()
            self._revision += 1
            self.revisionChanged.emit()
        self.languageChanged.emit()
        log.info("Language set to %s (effective %s)", setting, effective)

    def _install(self) -> None:
        app = QCoreApplication.instance()
        if app is None:
            return
        for old in (self._translator, self._qt_translator):
            if old is not None:
                app.removeTranslator(old)
        QLocale.setDefault(self.locale)

        translator = QTranslator(self)
        qm_dir = str(paths.resource("i18n"))
        if translator.load(f"nocturne_{self._effective}", qm_dir):
            app.installTranslator(translator)
            self._translator = translator
        else:
            log.warning("Translation file nocturne_%s.qm not found in %s", self._effective, qm_dir)
            self._translator = None

        qt_translator = QTranslator(self)
        qt_dir = QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)
        if qt_translator.load(self.locale, "qtbase", "_", qt_dir):
            app.installTranslator(qt_translator)
            self._qt_translator = qt_translator
        else:
            self._qt_translator = None


class Formatter(QObject):
    """Locale-aware formatting exposed to QML as ``Fmt``.

    QML bindings reference ``Fmt.revision`` so they re-evaluate on language change.
    """

    revisionChanged = Signal()

    def __init__(self, languages: LanguageManager, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._lm = languages
        languages.revisionChanged.connect(self.revisionChanged)

    def _get_revision(self) -> int:
        return self._lm.revision

    revision = Property(int, _get_revision, notify=revisionChanged)

    # ------------------------------------------------------------------ python
    def clock(self, seconds: float) -> str:
        total = max(0, int(round(seconds or 0)))
        h, rem = divmod(total, 3600)
        m, s = divmod(rem, 60)
        return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"

    def total(self, seconds: float) -> str:
        total_min = max(0, int(round((seconds or 0) / 60)))
        h, m = divmod(total_min, 60)
        if h:
            return tr("Fmt", "%1 h %2 min").replace("%1", str(h)).replace("%2", str(m))
        return tr("Fmt", "%1 min").replace("%1", str(m))

    def bytes_(self, size: float) -> str:
        loc = self._lm.locale
        units = [tr("Fmt", "B"), tr("Fmt", "KB"), tr("Fmt", "MB"), tr("Fmt", "GB"), tr("Fmt", "TB")]
        value = float(max(0.0, size or 0.0))
        idx = 0
        while value >= 1024 and idx < len(units) - 1:
            value /= 1024
            idx += 1
        decimals = 0 if idx == 0 or value >= 100 else 1
        return f"{loc.toString(value, 'f', decimals)} {units[idx]}"

    def songs_(self, n: int) -> str:
        return tr("Fmt", "%n song(s)", int(n))

    # --------------------------------------------------------------------- QML
    @Slot(float, result=str)
    def duration(self, seconds: float) -> str:
        return self.clock(seconds)

    @Slot(float, result=str)
    def durationMs(self, ms: float) -> str:  # noqa: N802
        return self.clock((ms or 0) / 1000.0)

    @Slot(float, result=str)
    def totalDuration(self, seconds: float) -> str:  # noqa: N802
        return self.total(seconds)

    @Slot(float, result=str)
    def size(self, size: float) -> str:
        return self.bytes_(size)

    @Slot(float, result=str)
    def speed(self, bytes_per_sec: float) -> str:
        return tr("Fmt", "%1/s").replace("%1", self.bytes_(bytes_per_sec))

    @Slot(float, result=str)
    def percent(self, fraction: float) -> str:
        return tr("Fmt", "%1%").replace("%1", str(int(round(max(0.0, min(1.0, fraction or 0)) * 100))))

    @Slot(int, result=str)
    def number(self, n: int) -> str:
        return self._lm.locale.toString(int(n))

    @Slot(int, result=str)
    def songs(self, n: int) -> str:
        return self.songs_(n)

    @Slot(str, result=str)
    def date(self, iso: str) -> str:
        if not iso:
            return ""
        try:
            moment = datetime.fromisoformat(iso)
        except ValueError:
            return ""
        if moment.tzinfo is None:
            moment = moment.replace(tzinfo=timezone.utc)
        local = moment.astimezone()
        today = datetime.now().astimezone().date()
        day = local.date()
        delta = (today - day).days
        if delta == 0:
            return tr("Fmt", "Today")
        if delta == 1:
            return tr("Fmt", "Yesterday")
        qdate = QDate(day.year, day.month, day.day)
        pattern = tr("Fmt", "d MMM") if day.year == today.year else tr("Fmt", "d MMM yyyy")
        return self._lm.locale.toString(qdate, pattern)
