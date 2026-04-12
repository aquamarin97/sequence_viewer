# settings/display_settings_manager.py
"""
Merkezi GÃ¶rÃ¼ntÃ¼leme AyarlarÄ± YÃ¶neticisi
========================================
Font ve (ileride) layout / renk gÃ¶rÃ¼ntÃ¼leme ayarlarÄ±nÄ± tek yerden yÃ¶netir.
YapÄ±landÄ±rma data/display_settings.json dosyasÄ±ndan yÃ¼klenir; dosya bulunamazsa
ya da hatalÄ±ysa yerleÅŸik varsayÄ±lanlar devreye girer â€” uygulama asla Ã§Ã¶kmez.

KullanÄ±m:
    from sequence_viewer.settings.display_settings_manager import display_settings_manager

    family  = display_settings_manager.sequence_font_family
    base_fs = display_settings_manager.sequence_font_size_base
    display_settings_manager.displaySettingsChanged.connect(my_slot)

    # Disk'e yazmadan bellek iÃ§i gÃ¼ncelleme + sinyal:
    display_settings_manager.apply({"font": {"sequence_font_size_base": 12.0}})

    # Disk'ten yeniden yÃ¼kle:
    display_settings_manager.reload()
"""
from __future__ import annotations

import json
import os
from typing import Optional

from PyQt5.QtCore import QObject, pyqtSignal

# ---------------------------------------------------------------------------
# YerleÅŸik varsayÄ±lanlar
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
# Ana sÄ±nÄ±f
# ---------------------------------------------------------------------------

class DisplaySettingsManager(QObject):
    """
    GÃ¶rÃ¼ntÃ¼leme ayarlarÄ±nÄ± merkezi olarak yÃ¶neten yapÄ±landÄ±rÄ±labilir yÃ¶netici.

    JSON dosyasÄ±ndan yÃ¼klenir; dosya yoksa ya da ayrÄ±ÅŸtÄ±rÄ±lamÄ±yorsa
    _BUILT_IN_DEFAULTS devreye girer â€” uygulama hiÃ§bir zaman Ã§Ã¶kmez.

    apply(overrides) â€” disk'e dokunmadan bellek iÃ§i gÃ¼ncelleme yapar ve sinyal yayar.
    reload()         â€” disk'ten yeniden yÃ¼kler ve sinyal yayar.
    """

    #: Herhangi bir ayar deÄŸiÅŸtiÄŸinde yayÄ±nlanÄ±r
    displaySettingsChanged = pyqtSignal()

    def __init__(self, config_path: Optional[str] = None):
        super().__init__()
        self._config_path: str = config_path or _CONFIG_PATH
        self._data: dict = {}
        self._load()
        # Font deÄŸiÅŸiminde glyph cache'i otomatik temizle
        try:
            from sequence_viewer.graphics.sequence_item.sequence_glyph_cache import GLYPH_CACHE
            self.displaySettingsChanged.connect(GLYPH_CACHE.invalidate)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Font ayarlarÄ±
    # ------------------------------------------------------------------

    @property
    def sequence_font_family(self) -> str:
        """Dizi satÄ±rlarÄ± iÃ§in kullanÄ±lacak font ailesi."""
        return str(
            self._data.get("font", {}).get(
                "sequence_font_family",
                _BUILT_IN_DEFAULTS["font"]["sequence_font_family"],
            )
        )

    @property
    def consensus_font_family(self) -> str:
        """KonsensÃ¼s satÄ±rÄ± iÃ§in kullanÄ±lacak font ailesi."""
        return str(
            self._data.get("font", {}).get(
                "consensus_font_family",
                _BUILT_IN_DEFAULTS["font"]["consensus_font_family"],
            )
        )

    @property
    def sequence_font_size_base(self) -> float:
        """
        Sequence satÄ±rÄ± iÃ§in baz font boyutu (punto, float).
        char_height = round(sequence_font_size_base / 0.6) formÃ¼lÃ¼yle tÃ¼retilir.
        LOD zoom adÄ±mlarÄ± bu deÄŸere orantÄ±lÄ± hesaplanÄ±r.
        SÄ±nÄ±r: 8.0 â€“ 32.0 pt.
        """
        raw = self._data.get("font", {}).get(
            "sequence_font_size_base",
            _BUILT_IN_DEFAULTS["font"]["sequence_font_size_base"],
        )
        return max(8.0, min(32.0, float(raw)))

    @property
    def consensus_font_size_base(self) -> float:
        """KonsensÃ¼s satÄ±rÄ± iÃ§in baz font boyutu: daima sequence_font_size_base + 1.0 pt."""
        return self.sequence_font_size_base + 1.0

    @property
    def sequence_char_height(self) -> int:
        """sequence_font_size_base'den tÃ¼retilen piksel yÃ¼ksekliÄŸi."""
        return round(self.sequence_font_size_base / 0.6)

    @property
    def consensus_char_height(self) -> int:
        """consensus_font_size_base'den tÃ¼retilen piksel yÃ¼ksekliÄŸi."""
        return round(self.consensus_font_size_base / 0.6)

    # ------------------------------------------------------------------
    # GÃ¼ncelleme â€” disk'e dokunmaz
    # ------------------------------------------------------------------

    def apply(self, overrides: dict):
        """
        Bellek iÃ§i ayarlarÄ± gÃ¼nceller ve displaySettingsChanged sinyali yayar.
        Disk'e yazma yapmaz; reload() ile disk ezmez.

        overrides â€” iÃ§ iÃ§e dict, Ã¶rn. {"font": {"sequence_font_size_base": 12.0}}
        """
        self._deep_update(self._data, overrides)
        self.displaySettingsChanged.emit()

    # ------------------------------------------------------------------
    # Yeniden yÃ¼kleme â€” diskten
    # ------------------------------------------------------------------

    def reload(self):
        """YapÄ±landÄ±rma dosyasÄ±nÄ± diskten yeniden yÃ¼kler ve sinyal yayar."""
        self._load()
        self.displaySettingsChanged.emit()

    # ------------------------------------------------------------------
    # Ã–zel
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
# ModÃ¼l-dÃ¼zeyinde singleton
# ---------------------------------------------------------------------------

display_settings_manager = DisplaySettingsManager()


