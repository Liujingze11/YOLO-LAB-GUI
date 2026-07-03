"""Pure Python i18n helpers — no GUI dependency.

Used by CLI, engine scripts, and as a base for the Qt I18nManager.
"""
import json
from pathlib import Path


def load_locale(locale_dir: Path, lang: str) -> dict:
    """Load a JSON locale file and return it as a dict."""
    path = locale_dir / f"{lang}.json"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def t(loc: dict, key: str, **kwargs) -> str:
    """Look up *key* in *loc* and optionally format with kwargs."""
    text = loc.get(key, key)
    if kwargs:
        try:
            text = text.format(**kwargs)
        except (KeyError, ValueError):
            pass
    return text
