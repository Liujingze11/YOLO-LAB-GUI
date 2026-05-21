"""
i18n multi-language translation manager.
"""
from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QLabel,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QTabWidget,
    QWidget,
)

LOCALE_DIR = Path(__file__).resolve().parent.parent / "locales"
AVAILABLE_LANGS = {"zh": "中文", "en": "English", "fr": "Français", "es": "Español"}


class I18nManager(QObject):
    language_changed = Signal(str)

    def __init__(self):
        super().__init__()
        self._current_lang = "zh"
        self._translations: dict[str, str] = {}
        self._load_locale("zh")

    @property
    def current_lang(self) -> str:
        return self._current_lang

    def tr(self, key: str, **kwargs) -> str:
        text = self._translations.get(key, key)
        if kwargs:
            try:
                text = text.format(**kwargs)
            except (KeyError, ValueError):
                pass
        return text

    def set_language(self, lang: str) -> None:
        if lang == self._current_lang:
            return
        self._load_locale(lang)
        self.language_changed.emit(lang)

    def apply_language(self, root: QWidget) -> None:
        stack = [root]
        while stack:
            w = stack.pop()
            key = w.property("i18nKey")
            if key:
                self._update_widget(w, key)
            for child in w.children():
                if isinstance(child, QWidget):
                    stack.append(child)

    def _update_widget(self, w: QWidget, base_key: str) -> None:
        if isinstance(w, (QLabel, QPushButton, QCheckBox, QRadioButton)):
            w.setText(self.tr(base_key))
        elif isinstance(w, QTabWidget):
            for i in range(w.count()):
                tab_key = w.tabBar().tabData(i)
                if tab_key and isinstance(tab_key, str):
                    w.setTabText(i, self.tr(tab_key))
        elif isinstance(w, QComboBox):
            for i in range(w.count()):
                item_key = w.itemData(i, Qt.ItemDataRole.UserRole + 1)
                if item_key and isinstance(item_key, str):
                    w.setItemText(i, self.tr(item_key))
        elif isinstance(w, QProgressBar):
            w.setFormat(self.tr(base_key))

    def _load_locale(self, lang: str) -> None:
        path = LOCALE_DIR / f"{lang}.json"
        with open(path, "r", encoding="utf-8") as f:
            self._translations = json.load(f)
        self._current_lang = lang


_i18n = I18nManager()


def tr(key: str, **kwargs) -> str:
    return _i18n.tr(key, **kwargs)


def set_language(lang: str) -> None:
    _i18n.set_language(lang)


def apply_language(root: QWidget) -> None:
    _i18n.apply_language(root)


def current_lang() -> str:
    return _i18n.current_lang
