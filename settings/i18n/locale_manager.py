# settings/i18n/locale_manager.py
from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Dict
from PyQt5.QtCore import QObject, pyqtSignal

_STRINGS_DIR = Path(__file__).parent / "strings"
_DEFAULT_LOCALE = "tr"
_FALLBACK_LOCALE = "en"

def _load_strings(locale_code):
    path = _STRINGS_DIR / f"{locale_code}.json"
    if not path.exists(): return {}
    with path.open(encoding="utf-8") as f: return json.load(f)

def _flatten(d, prefix=""):
    out = {}
    for k, v in d.items():
        if k.startswith("_"): continue
        full_key = f"{prefix}.{k}" if prefix else k
        if isinstance(v, dict): out.update(_flatten(v, full_key))
        else: out[full_key] = str(v)
    return out

class _LocaleManager(QObject):
    localeChanged = pyqtSignal(str)
    def __init__(self):
        super().__init__()
        self._locale = _DEFAULT_LOCALE
        self._strings = {}
        self._fallback = {}
        self._reload()
    @property
    def current_locale(self): return self._locale
    def set_locale(self, locale_code):
        if locale_code == self._locale: return
        self._locale = locale_code
        self._reload()
        self.localeChanged.emit(self._locale)
    def t(self, key, **kwargs):
        raw = self._strings.get(key) or self._fallback.get(key) or key
        if kwargs:
            try: return raw.format(**kwargs)
            except: return raw
        return raw
    def _reload(self):
        self._strings = _flatten(_load_strings(self._locale))
        if self._locale != _FALLBACK_LOCALE:
            self._fallback = _flatten(_load_strings(_FALLBACK_LOCALE))
        else: self._fallback = {}

locale_manager = _LocaleManager()
