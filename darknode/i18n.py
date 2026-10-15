"""Translation loader shared by the terminal and the browser front-ends.

All player-facing text lives in ``darknode/locales/<lang>.json`` as a nested
dictionary. The engine never embeds prose: it passes i18n keys around and the
front-end formats them in the player's language.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

LOCALES_DIR = Path(__file__).resolve().parent / "locales"

DEFAULT_LANG = "en"
LANGUAGES = ("en", "uk")

#: Human-readable names for the language switcher.
LANGUAGE_NAMES = {"en": "English", "uk": "Українська"}


@lru_cache(maxsize=None)
def load(lang: str) -> dict[str, Any]:
    """Load and cache one locale file."""
    if lang not in LANGUAGES:
        lang = DEFAULT_LANG
    path = LOCALES_DIR / f"{lang}.json"
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _dig(tree: dict[str, Any], key: str) -> Any:
    node: Any = tree
    for part in key.split("."):
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return node


def t(key: str, lang: str = DEFAULT_LANG, **params: Any) -> str:
    """Translate ``key`` for ``lang``, formatting ``params`` into it.

    Falls back to English, then to the raw key, so a missing string is visible
    rather than crashing the game.
    """
    value = _dig(load(lang), key)
    if value is None and lang != DEFAULT_LANG:
        value = _dig(load(DEFAULT_LANG), key)
    if value is None:
        return key
    if isinstance(value, list):
        value = "\n".join(str(v) for v in value)
    if not isinstance(value, str):
        return key
    if params:
        try:
            return value.format(**params)
        except (KeyError, IndexError, ValueError):
            return value
    return value


def get(key: str, lang: str = DEFAULT_LANG) -> Any:
    """Return the raw value at ``key`` (may be a list, dict or string)."""
    value = _dig(load(lang), key)
    if value is None and lang != DEFAULT_LANG:
        value = _dig(load(DEFAULT_LANG), key)
    return value


class Translator:
    """A small bound helper so callers can do ``tr('ui.run')``."""

    def __init__(self, lang: str = DEFAULT_LANG) -> None:
        self.lang = lang if lang in LANGUAGES else DEFAULT_LANG

    def __call__(self, key: str, **params: Any) -> str:
        return t(key, self.lang, **params)

    def raw(self, key: str) -> Any:
        return get(key, self.lang)


# --- completeness checking (used by tests) ---------------------------------

def _flatten(tree: dict[str, Any], prefix: str = "") -> set[str]:
    keys: set[str] = set()
    for name, value in tree.items():
        path = f"{prefix}.{name}" if prefix else name
        if isinstance(value, dict):
            keys |= _flatten(value, path)
        else:
            keys.add(path)
    return keys


def missing_keys() -> dict[str, set[str]]:
    """For each language, the keys present in some other language but not it."""
    per_lang = {lang: _flatten(load(lang)) for lang in LANGUAGES}
    union: set[str] = set()
    for keys in per_lang.values():
        union |= keys
    return {lang: union - keys for lang, keys in per_lang.items()}
