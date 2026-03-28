# settings/i18n/locale_manager.py
"""
Uygulama lokalizasyon sistemi.

Kullanım
--------
    from settings.i18n.locale_manager import locale_manager

    # Kısa alias (önerilen)
    _t = locale_manager.t

    # Basit anahtar
    _t("menu.file")                          # → "Dosya" (tr) veya "File" (en)

    # Parametreli anahtar
    _t("find_motifs.result_found",
       hits=5, added=5)                      # → "5 eşleşme bulundu, 5 annotasyon eklendi."

    # Dil değiştir
    locale_manager.set_locale("en")

    # Değişimi dinle
    locale_manager.localeChanged.connect(self._retranslate_ui)

Anahtar formatı
---------------
Anahtarlar nokta-ayrımlı hiyerarşiyi takip eder:
    "kategori.alt_kategori.anahtar"

JSON dosyalarında iç içe nesne veya düz anahtar (nokta dahil) olarak saklanabilir.
Buradaki loader her iki formatı da destekler.

Fallback
--------
1. İstenen locale → 2. İngilizce → 3. Anahtar kendisi
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from PyQt5.QtCore import QObject, pyqtSignal

_STRINGS_DIR = Path(__file__).parent / "strings"
_DEFAULT_LOCALE = "tr"
_FALLBACK_LOCALE = "en"


def _load_strings(locale_code: str) -> Dict[str, Any]:
    """JSON dosyasını yükler; bulunamazsa boş dict döner."""
    path = _STRINGS_DIR / f"{locale_code}.json"
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def _flatten(d: Dict[str, Any], prefix: str = "") -> Dict[str, str]:
    """
    İç içe dict'i nokta-ayrımlı düz dict'e çevirir.
    {"menu": {"file": "Dosya"}} → {"menu.file": "Dosya"}
    """
    out: Dict[str, str] = {}
    for k, v in d.items():
        if k.startswith("_"):        # _meta gibi meta alanları atla
            continue
        full_key = f"{prefix}.{k}" if prefix else k
        if isinstance(v, dict):
            out.update(_flatten(v, full_key))
        else:
            out[full_key] = str(v)
    return out


class _LocaleManager(QObject):
    """
    Aktif dili tutar; değiştiğinde sinyal yayınlar.

    Widget'lar __init__ içinde:
        locale_manager.localeChanged.connect(self._retranslate_ui)
    bağlantısını kurar, `_retranslate_ui` içinde tüm label/button
    metinlerini `_t(...)` ile yeniden yazar.
    """

    localeChanged = pyqtSignal(str)   # yeni locale kodu

    def __init__(self) -> None:
        super().__init__()
        self._locale: str = _DEFAULT_LOCALE
        self._strings: Dict[str, str] = {}
        self._fallback: Dict[str, str] = {}
        self._reload()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def current_locale(self) -> str:
        return self._locale

    @property
    def available_locales(self) -> list[str]:
        """Kullanılabilir locale kodları (JSON dosyalarından)."""
        return [
            p.stem for p in _STRINGS_DIR.glob("*.json")
            if not p.stem.startswith("_")
        ]

    def set_locale(self, locale_code: str) -> None:
        """Aktif dili değiştirir ve `localeChanged` sinyali yayınlar."""
        if locale_code == self._locale:
            return
        self._locale = locale_code
        self._reload()
        self.localeChanged.emit(self._locale)

    def t(self, key: str, **kwargs: Any) -> str:
        """
        Verilen anahtara karşılık gelen çeviriyi döner.

        Parametreler `{name}` biçimindeki yer tutucuları doldurur.
        Anahtar bulunamazsa İngilizce fallback, o da yoksa anahtarın kendisi döner.
        """
        raw = (
            self._strings.get(key)
            or self._fallback.get(key)
            or key
        )
        if kwargs:
            try:
                return raw.format(**kwargs)
            except (KeyError, ValueError):
                return raw
        return raw

    # ------------------------------------------------------------------
    # İç yükleme
    # ------------------------------------------------------------------

    def _reload(self) -> None:
        data = _load_strings(self._locale)
        self._strings = _flatten(data)

        if self._locale != _FALLBACK_LOCALE:
            fallback_data = _load_strings(_FALLBACK_LOCALE)
            self._fallback = _flatten(fallback_data)
        else:
            self._fallback = {}


# Modül düzeyinde tek örnek
locale_manager = _LocaleManager()