"""System tray icon with player controls, language quick switch and quit."""

from __future__ import annotations

from typing import Callable

from PySide6.QtCore import QCoreApplication, QObject
from PySide6.QtGui import QAction, QActionGroup
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

from nocturne import APP_NAME, icons
from nocturne.i18n import LANGUAGE_INFO, LanguageManager
from nocturne.player import PlayerController
from nocturne.settings import SettingsType


def _t(text: str) -> str:
    return QCoreApplication.translate("Tray", text)


class TrayController(QObject):
    def __init__(
        self,
        player: PlayerController,
        languages: LanguageManager,
        settings: SettingsType,
        show_window: Callable[[], None],
        toggle_widget: Callable[[], None],
        toggle_mini: Callable[[], None],
        quit_app: Callable[[], None],
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._player = player
        self._languages = languages
        self._settings = settings
        self._show_window = show_window
        self.available = QSystemTrayIcon.isSystemTrayAvailable()
        self.tray = QSystemTrayIcon(icons.app_qicon(), self)
        self.menu = QMenu()

        self.act_show = QAction(icons.qicon("window", "#2B2B40"), "", self.menu)
        self.act_play = QAction("", self.menu)
        self.act_prev = QAction(icons.qicon("previous", "#2B2B40"), "", self.menu)
        self.act_next = QAction(icons.qicon("next", "#2B2B40"), "", self.menu)
        self.act_widget = QAction(icons.qicon("widgets", "#2B2B40"), "", self.menu)
        self.act_mini = QAction(icons.qicon("miniplayer", "#2B2B40"), "", self.menu)
        self.act_quit = QAction(icons.qicon("power", "#2B2B40"), "", self.menu)
        self.lang_menu = QMenu(self.menu)
        self.lang_menu.setIcon(icons.qicon("globe", "#2B2B40"))
        self.lang_group = QActionGroup(self.lang_menu)
        self.lang_group.setExclusive(True)
        self.lang_actions: dict[str, QAction] = {}
        for code in ["system", *[info["code"] for info in LANGUAGE_INFO]]:
            act = QAction("", self.lang_menu)
            act.setCheckable(True)
            act.setData(code)
            act.triggered.connect(lambda _c=False, c=code: self._languages.setLanguage(c))
            self.lang_group.addAction(act)
            self.lang_menu.addAction(act)
            self.lang_actions[code] = act

        self.act_show.triggered.connect(show_window)
        self.act_play.triggered.connect(player.togglePlay)
        self.act_prev.triggered.connect(player.previous)
        self.act_next.triggered.connect(player.next)
        self.act_widget.triggered.connect(toggle_widget)
        self.act_mini.triggered.connect(toggle_mini)
        self.act_quit.triggered.connect(quit_app)

        self.menu.addAction(self.act_show)
        self.menu.addSeparator()
        self.menu.addAction(self.act_play)
        self.menu.addAction(self.act_prev)
        self.menu.addAction(self.act_next)
        self.menu.addSeparator()
        self.menu.addAction(self.act_widget)
        self.menu.addAction(self.act_mini)
        self.menu.addMenu(self.lang_menu)
        self.menu.addSeparator()
        self.menu.addAction(self.act_quit)
        self.tray.setContextMenu(self.menu)
        self.tray.activated.connect(self._on_activated)

        player.playingChanged.connect(self.refresh)
        player.currentTrackChanged.connect(self.refresh)
        languages.languageChanged.connect(self.retranslate)
        settings.widgetVisibleChanged.connect(self.refresh)  # type: ignore[attr-defined]
        self.retranslate()

    def show(self) -> None:
        if self.available:
            self.tray.show()

    def hide(self) -> None:
        self.tray.hide()

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason in (QSystemTrayIcon.ActivationReason.Trigger, QSystemTrayIcon.ActivationReason.DoubleClick):
            self._show_window()
        elif reason == QSystemTrayIcon.ActivationReason.MiddleClick:
            self._player.togglePlay()

    def retranslate(self) -> None:
        self.act_show.setText(_t("Show Nocturne"))
        self.act_prev.setText(_t("Previous"))
        self.act_next.setText(_t("Next"))
        self.act_mini.setText(_t("Mini player"))
        self.act_quit.setText(_t("Quit"))
        self.lang_menu.setTitle(_t("Language"))
        for code, act in self.lang_actions.items():
            if code == "system":
                act.setText(_t("System language"))
            else:
                act.setText(next(i["name"] for i in LANGUAGE_INFO if i["code"] == code))
        self.refresh()

    def refresh(self) -> None:
        playing = self._player.playing
        self.act_play.setText(_t("Pause") if playing else _t("Play"))
        self.act_play.setIcon(icons.qicon("pause" if playing else "play", "#2B2B40"))
        has = self._player.hasTrack or self._player.queueLength > 0
        self.act_prev.setEnabled(has)
        self.act_next.setEnabled(has)
        self.act_widget.setText(
            _t("Hide desktop widget") if self._settings.value("widgetVisible") else _t("Show desktop widget")
        )
        current = self._languages.language
        if current in self.lang_actions:
            self.lang_actions[current].setChecked(True)
        track = self._player.current
        tip = APP_NAME if track is None else f"{track.title} — {track.artist}"
        self.tray.setToolTip(tip[:120])

    def message(self, title: str, body: str) -> None:
        if self.available and self.tray.isVisible():
            self.tray.showMessage(title, body, icons.app_qicon(), 5000)
