# sequence_viewer/utils/tm_settings_manager.py
# utils/tm_settings_manager.py
"""
Tm Hesaplama Parametreleri Yöneticisi
=====================================
data/tm_settings.json dosyasından Tm hesaplama parametrelerini yükler.
Dosya yoksa veya bozuksa yerleşik varsayılanlar devreye girer — uygulama
hiçbir zaman çökmez.

Kullanım:
    from sequence_viewer.utils.tm_settings_manager import tm_settings_manager

    method = tm_settings_manager.method          # "NN" | "GC" | "Wallace"
    na     = tm_settings_manager.na              # mM
    params = tm_settings_manager.nn_params()     # Tm_NN'e geçirilecek kwargs

    # Bellek içi güncelleme + sinyal:
    tm_settings_manager.apply({"method": "GC", "parameters": {"na": 100.0}})

    # Disk'ten yeniden yükle:
    tm_settings_manager.reload()

    # Değişiklikleri dinle:
    tm_settings_manager.tmSettingsChanged.connect(my_slot)
"""
from __future__ import annotations

import json
import os
from typing import Any

from PyQt5.QtCore import QObject, pyqtSignal


# ---------------------------------------------------------------------------
# Yerleşik varsayılanlar  (JSON yoksa veya eksik alan varsa devreye girer)
# ---------------------------------------------------------------------------

_DEFAULTS: dict[str, Any] = {
    "method": "NN",
    "parameters": {
        "na":    50.0,   # mM Na⁺
        "mg":     0.0,   # mM Mg²⁺
        "dnac1": 25.0,   # nM primer konsantrasyonu
        "dnac2": 25.0,   # nM tamamlayıcı strand
        "dntps":  0.0,   # mM dNTP
    },
}

_VALID_METHODS = {"Wallace", "GC", "NN"}

_CONFIG_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "data", "tm_settings.json")
)


# ---------------------------------------------------------------------------
# Manager
# ---------------------------------------------------------------------------

class TmSettingsManager(QObject):
    """
    Tm parametrelerini merkezi olarak yöneten yapılandırılabilir yönetici.

    JSON dosyasından yüklenir; dosya yoksa ya da ayrıştırılamıyorsa
    _DEFAULTS devreye girer.

    apply(overrides) — diski değiştirmeden bellek içi güncelleme + sinyal.
    reload()         — diskten yeniden yükle + sinyal.
    save()           — mevcut bellek içi değerleri diske yaz.
    """

    tmSettingsChanged = pyqtSignal()

    # Geçerli method değerleri
    METHODS = frozenset(_VALID_METHODS)

    def __init__(self) -> None:
        super().__init__()
        self._data: dict[str, Any] = {}
        self._load()

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def method(self) -> str:
        """Kullanılacak Tm yöntemi: 'Wallace' | 'GC' | 'NN'"""
        return self._data["method"]

    @property
    def na(self) -> float:
        """Na⁺ konsantrasyonu (mM)."""
        return self._data["parameters"]["na"]

    @property
    def mg(self) -> float:
        """Mg²⁺ konsantrasyonu (mM)."""
        return self._data["parameters"]["mg"]

    @property
    def dnac1(self) -> float:
        """Primer / oligo konsantrasyonu (nM)."""
        return self._data["parameters"]["dnac1"]

    @property
    def dnac2(self) -> float:
        """Tamamlayıcı strand konsantrasyonu (nM)."""
        return self._data["parameters"]["dnac2"]

    @property
    def dntps(self) -> float:
        """Toplam dNTP konsantrasyonu (mM)."""
        return self._data["parameters"]["dntps"]

    # ------------------------------------------------------------------
    # Hazır kwargs paketleri — calculate_tm'e doğrudan geçirilir
    # ------------------------------------------------------------------

    def nn_params(self) -> dict[str, Any]:
        """Tm_NN için gereken tüm parametreleri dict olarak döndürür."""
        return {
            "Na":    self.na,
            "Mg":    self.mg,
            "dnac1": self.dnac1,
            "dnac2": self.dnac2,
            "dNTPs": self.dntps,
        }

    def gc_params(self) -> dict[str, Any]:
        """Tm_GC için gereken parametreleri dict olarak döndürür."""
        return {
            "Na":    self.na,
            "Mg":    self.mg,
            "dNTPs": self.dntps,
        }

    # ------------------------------------------------------------------
    # Güncelleme API'si
    # ------------------------------------------------------------------

    def apply(self, overrides: dict[str, Any]) -> None:
        """
        Derin birleştirme ile bellek içi ayarları günceller ve sinyal yayar.
        Disk'e dokunmaz.
        """
        self._deep_merge(self._data, overrides)
        self._validate()
        self.tmSettingsChanged.emit()

    def reload(self) -> None:
        """Disk'ten yeniden yükler ve sinyal yayar."""
        self._load()
        self.tmSettingsChanged.emit()

    def save(self) -> None:
        """Mevcut bellek içi değerleri diske yazar."""
        try:
            payload = {
                "version": 1,
                "description": "Sequence Viewer — Tm hesaplama parametreleri.",
                "method": self._data["method"],
                "parameters": dict(self._data["parameters"]),
            }
            with open(_CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2, ensure_ascii=False)
        except Exception:
            pass   # disk yazma hatası sessizce yutulur

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _load(self) -> None:
        import copy
        self._data = copy.deepcopy(_DEFAULTS)
        try:
            with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
                raw = json.load(f)
            self._deep_merge(self._data, raw)
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            pass   # varsayılanlarla devam
        self._validate()

    def _validate(self) -> None:
        """Geçersiz değerleri sessizce varsayılanlarla değiştirir."""
        p = self._data
        if p.get("method") not in _VALID_METHODS:
            p["method"] = _DEFAULTS["method"]
        params = p.setdefault("parameters", {})
        defaults_p = _DEFAULTS["parameters"]
        for key, default_val in defaults_p.items():
            val = params.get(key)
            if not isinstance(val, (int, float)) or val < 0:
                params[key] = default_val

    @staticmethod
    def _deep_merge(base: dict, overrides: dict) -> None:
        """Overrides'ı base içine derin birleştir (in-place)."""
        for k, v in overrides.items():
            if k.startswith("_"):      # _comments gibi meta alanları atla
                continue
            if isinstance(v, dict) and isinstance(base.get(k), dict):
                TmSettingsManager._deep_merge(base[k], v)
            else:
                base[k] = v


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

tm_settings_manager = TmSettingsManager()
