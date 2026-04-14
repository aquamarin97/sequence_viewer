# sequence_viewer/settings/display_settings_manager.py
# settings/display_settings_manager.py
"""
Merkezi Görüntüleme Ayarları Yöneticisi
========================================
Font ve (ileride) layout / renk görüntüleme ayarlarını tek yerden yönetir.
Yapılandırma data/display_settings.json dosyasından yüklenir; dosya bulunamazsa
ya da hatalıysa yerleşik varsayılanlar devreye girer â€” uygulama asla çökmez.

Kullanım:
    from sequence_viewer.settings.display_settings_manager import display_settings_manager

    family  = display_settings_manager.sequence_font_family
    base_fs = display_settings_manager.sequence_font_size_base
    display_settings_manager.displaySettingsChanged.connect(my_slot)

    # Disk'e yazmadan bellek içi güncelleme + sinyal:
    display_settings_manager.apply({"font": {"sequence_font_size_base": 12.0}})

    # Disk'ten yeniden yükle:
    display_settings_manager.reload()
"""
from __future__ import annotations

import json
import os
from typing import Optional

from PyQt5.QtCore import QObject, pyqtSignal

# ---------------------------------------------------------------------------
# Yerleşik varsayılanlar
# ---------------------------------------------------------------------------

_BUILT_IN_DEFAULTS: dict = {
    "font": {
        "sequence_font_family":    "Courier New",
        "consensus_font_family":   "Courier New",
        "sequence_font_size_base": 10.8,   # char_height = round(10.8 / 0.6) = 18
    }
}

_CONFIG_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "data", "display_settings.json")
)


# ---------------------------------------------------------------------------
# Ana sınıf
# ---------------------------------------------------------------------------

class DisplaySettingsManager(QObject):
    """
    Görüntüleme ayarlarını merkezi olarak yöneten yapılandırılabilir yönetici.

    JSON dosyasından yüklenir; dosya yoksa ya da ayrıştırılamıyorsa
    _BUILT_IN_DEFAULTS devreye girer â€” uygulama hiçbir zaman çökmez.

    apply(overrides) â€” disk'e dokunmadan bellek içi güncelleme yapar ve sinyal yayar.
    reload()         â€” disk'ten yeniden yükler ve sinyal yayar.
    """

    #: Herhangi bir ayar deĞŸiştiĞŸinde yayınlanır
    displaySettingsChanged = pyqtSignal()

    def __init__(self, config_path: Optional[str] = None):
        super().__init__()
        self._config_path: str = config_path or _CONFIG_PATH
        self._data: dict = {}
        self._load()
        # Font deĞŸişiminde glyph cache'i otomatik temizle
        try:
            from sequence_viewer.graphics.sequence_item.sequence_glyph_cache import GLYPH_CACHE
            self.displaySettingsChanged.connect(GLYPH_CACHE.invalidate)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Font ayarları
    # ------------------------------------------------------------------

    @property
    def sequence_font_family(self) -> str:
        """Dizi satırları için kullanılacak font ailesi."""
        return str(
            self._data.get("font", {}).get(
                "sequence_font_family",
                _BUILT_IN_DEFAULTS["font"]["sequence_font_family"],
            )
        )

    @property
    def consensus_font_family(self) -> str:
        """Konsensüs satırı için kullanılacak font ailesi."""
        return str(
            self._data.get("font", {}).get(
                "consensus_font_family",
                _BUILT_IN_DEFAULTS["font"]["consensus_font_family"],
            )
        )

    @property
    def sequence_font_size_base(self) -> float:
        """
        Sequence satırı için baz font boyutu (punto, float).
        char_height = round(sequence_font_size_base / 0.6) formülüyle türetilir.
        LOD zoom adımları bu deĞŸere orantılı hesaplanır.
        Sınır: 8.0 â€“ 32.0 pt.
        """
        raw = self._data.get("font", {}).get(
            "sequence_font_size_base",
            _BUILT_IN_DEFAULTS["font"]["sequence_font_size_base"],
        )
        return max(8.0, min(32.0, float(raw)))

    @property
    def consensus_font_size_base(self) -> float:
        """Konsensüs satırı için baz font boyutu: daima sequence_font_size_base + 1.0 pt."""
        return self.sequence_font_size_base + 1.0

    @property
    def sequence_char_height(self) -> int:
        """sequence_font_size_base'den türetilen piksel yüksekliĞŸi."""
        return round(self.sequence_font_size_base / 0.6)

    @property
    def consensus_char_height(self) -> int:
        """consensus_font_size_base'den türetilen piksel yüksekliĞŸi."""
        return round(self.consensus_font_size_base / 0.6)

    # ------------------------------------------------------------------
    # Güncelleme â€” disk'e dokunmaz
    # ------------------------------------------------------------------

    def apply(self, overrides: dict):
        """
        Bellek içi ayarları günceller ve displaySettingsChanged sinyali yayar.
        Disk'e yazma yapmaz; reload() ile disk ezmez.

        overrides â€” iç içe dict, örn. {"font": {"sequence_font_size_base": 12.0}}
        """
        self._deep_update(self._data, overrides)
        self.displaySettingsChanged.emit()

    # ------------------------------------------------------------------
    # Yeniden yükleme â€” diskten
    # ------------------------------------------------------------------

    def reload(self):
        """Yapılandırma dosyasını diskten yeniden yükler ve sinyal yayar."""
        self._load()
        self.displaySettingsChanged.emit()

    # ------------------------------------------------------------------
    # Özel
    # ------------------------------------------------------------------

    def _load(self):
        try:
            if os.path.isfile(self._config_path):
                with open(self._config_path, "r", encoding="utf-8") as fh:
                    self._data = json.load(fh)
            else:
                self._data = {}
        except Exception:
            self._data = {}

    @staticmethod
    def _deep_update(target: dict, source: dict):
        """source'daki key'leri target'a derinlemesine uygular."""
        for k, v in source.items():
            if isinstance(v, dict) and isinstance(target.get(k), dict):
                DisplaySettingsManager._deep_update(target[k], v)
            else:
                target[k] = v


# ---------------------------------------------------------------------------
# Modül-düzeyinde singleton
# ---------------------------------------------------------------------------

display_settings_manager = DisplaySettingsManager()


