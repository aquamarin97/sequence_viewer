# settings/mouse_binding_manager.py
"""
Merkezi Fare Eylem Yöneticisi
==============================
Tüm fare/klavye bağlamalarını tek bir yerden yönetir.
Yapılandırma data/mouse_bindings.json dosyasından yüklenir;
dosya bulunamazsa ya da hatalıysa yerleşik varsayılanlar devreye girer.

Kullanım:
    from settings.mouse_binding_manager import mouse_binding_manager, MouseAction

    # Drag aksiyonu çözümleme (sequence / consensus)
    action = mouse_binding_manager.resolve_sequence_drag(event.modifiers())
    if action == MouseAction.DRAG_SELECT:
        guides.clear()          # replace
    # DRAG_SELECT_ADDITIVE → guides korunur

    # Tıklama aksiyonu çözümleme
    action = mouse_binding_manager.resolve_sequence_click(event.modifiers())
    if action == MouseAction.GUIDE_TOGGLE:
        ...   # toggle
    else:
        ...   # set single

    # Zoom kontrolü
    if not mouse_binding_manager.is_zoom_event(event.modifiers()):
        return False

    # Drag eşiği
    threshold = mouse_binding_manager.drag_threshold("sequence_viewer")

    # Zoom parametreleri
    factor = mouse_binding_manager.zoom_base_factor
"""
from __future__ import annotations

import json
import os
from enum import Enum
from typing import Optional

from PyQt5.QtCore import QObject, Qt, pyqtSignal

# ---------------------------------------------------------------------------
# Eylem kataloğu
# ---------------------------------------------------------------------------

class MouseAction(Enum):
    """Uygulama genelinde tanımlı tüm fare eylemleri."""
    # Sequence / Consensus
    DRAG_SELECT           = "drag_select"
    DRAG_SELECT_ADDITIVE  = "drag_select_additive"
    GUIDE_SET             = "guide_set"
    GUIDE_TOGGLE          = "guide_toggle"
    ZOOM                  = "zoom"
    # Header
    ROW_SELECT            = "row_select"
    ROW_MULTI_SELECT      = "row_multi_select"
    ROW_RANGE_SELECT      = "row_range_select"
    ROW_REORDER           = "row_reorder"
    # Navigation Ruler
    NAV_ZOOM_TO_RANGE     = "nav_zoom_to_range"
    NAV_SCROLL_TO         = "nav_scroll_to"
    # Sentinel
    NONE                  = "none"


# ---------------------------------------------------------------------------
# İç yardımcılar
# ---------------------------------------------------------------------------

_MODIFIER_STR_TO_QT: dict[str, int] = {
    "None":       Qt.NoModifier,
    "Ctrl":       Qt.ControlModifier,
    "Shift":      Qt.ShiftModifier,
    "Alt":        Qt.AltModifier,
    "Ctrl+Shift": Qt.ControlModifier | Qt.ShiftModifier,
}

# Sabit varsayılanlar — JSON'dan okunamazsa bu değerler kullanılır
_BUILT_IN_DEFAULTS: dict[tuple[str, str], str] = {
    ("sequence_view", "drag_select"):           "None",
    ("sequence_view", "drag_select_additive"):  "Ctrl",
    ("sequence_view", "guide_set"):             "None",
    ("sequence_view", "guide_toggle"):          "Ctrl",
    ("sequence_view", "zoom"):                  "Ctrl",
    ("sequence_view", "h_scroll"):              "Shift",
    ("header_view",   "row_select"):            "None",
    ("header_view",   "row_multi_select"):      "Ctrl",
    ("header_view",   "row_range_select"):      "Shift",
}

_DEFAULT_THRESHOLDS: dict[str, int] = {
    "sequence_viewer":  4,
    "consensus_row":    4,
    "header_viewer":    6,
    "navigation_ruler": 3,
}

_DEFAULT_ZOOM = {
    "base_factor":         1.22,
    "acceleration_factor": 1.06,
    "max_char_width":      90.0,
}

_CONFIG_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "data", "mouse_bindings.json")
)


# ---------------------------------------------------------------------------
# Ana sınıf
# ---------------------------------------------------------------------------

class MouseBindingManager(QObject):
    """
    Fare eylemlerini merkezi olarak çözen yapılandırılabilir bağlama yöneticisi.

    JSON dosyasından yüklenir; dosya yoksa ya da ayrıştırılamıyorsa
    _BUILT_IN_DEFAULTS devreye girer — uygulama hiçbir zaman çökmez.
    """

    #: Yapılandırma yeniden yüklendiğinde yayınlanır
    bindingsChanged = pyqtSignal()

    def __init__(self, config_path: Optional[str] = None):
        super().__init__()
        self._config_path: str = config_path or _CONFIG_PATH
        self._data: dict = {}
        self._load()

    # ------------------------------------------------------------------
    # Sequence / Consensus aksiyon çözümleyicileri
    # ------------------------------------------------------------------

    def resolve_sequence_drag(self, qt_modifiers) -> MouseAction:
        """
        Drag başladığında hangi aksiyon uygulanacağını döner.

        Returns:
            DRAG_SELECT_ADDITIVE  → mevcut guide çizgileri korunur
            DRAG_SELECT           → guide çizgileri temizlenir, yeni aralık eklenir
        """
        additive_mod = self._qt_modifier("sequence_view", "drag_select_additive")
        if qt_modifiers & additive_mod:
            return MouseAction.DRAG_SELECT_ADDITIVE
        return MouseAction.DRAG_SELECT

    def resolve_sequence_click(self, qt_modifiers) -> MouseAction:
        """
        Drag eşiği geçilmeden fare bırakıldığında (boundary tıklama) hangi
        aksiyon uygulanacağını döner.

        Returns:
            GUIDE_TOGGLE  → tıklanan sınırda guide varsa kaldır, yoksa ekle
            GUIDE_SET     → tüm guide'ları temizle, bu tek guide'ı koy
        """
        toggle_mod = self._qt_modifier("sequence_view", "guide_toggle")
        if qt_modifiers & toggle_mod:
            return MouseAction.GUIDE_TOGGLE
        return MouseAction.GUIDE_SET

    def is_zoom_event(self, qt_modifiers) -> bool:
        """Tekerlek olayının zoom aksiyonu tetikleyip tetiklemediğini döner."""
        zoom_mod = self._qt_modifier("sequence_view", "zoom")
        return bool(qt_modifiers & zoom_mod)

    def is_h_scroll_event(self, qt_modifiers) -> bool:
        """Tekerlek olayının yatay kaydırma aksiyonu tetikleyip tetiklemediğini döner."""
        h_scroll_mod = self._qt_modifier("sequence_view", "h_scroll")
        return bool(qt_modifiers & h_scroll_mod)

    # ------------------------------------------------------------------
    # Header aksiyon çözümleyicisi
    # ------------------------------------------------------------------

    def resolve_header_click(self, qt_modifiers) -> MouseAction:
        """
        Header satır tıklamasında hangi seçim modu uygulanacağını döner.

        Returns:
            ROW_MULTI_SELECT  → Ctrl tık, toggle seçim
            ROW_RANGE_SELECT  → Shift tık, aralık seçim
            ROW_SELECT        → normal tık, tek satır seçim
        """
        ctrl_mod  = self._qt_modifier("header_view", "row_multi_select")
        shift_mod = self._qt_modifier("header_view", "row_range_select")
        if qt_modifiers & ctrl_mod:
            return MouseAction.ROW_MULTI_SELECT
        if qt_modifiers & shift_mod:
            return MouseAction.ROW_RANGE_SELECT
        return MouseAction.ROW_SELECT

    # ------------------------------------------------------------------
    # Drag eşikleri
    # ------------------------------------------------------------------

    def drag_threshold(self, context: str) -> int:
        """
        Belirtilen bağlam için fare drag eşiğini piksel cinsinden döner.

        context: 'sequence_viewer' | 'consensus_row' | 'header_viewer' | 'navigation_ruler'
        """
        return int(
            self._data
            .get("drag_thresholds_px", {})
            .get(context, _DEFAULT_THRESHOLDS.get(context, 4))
        )

    # ------------------------------------------------------------------
    # Zoom parametreleri
    # ------------------------------------------------------------------

    @property
    def zoom_base_factor(self) -> float:
        """Her tekerlek adımı için temel büyütme/küçültme çarpanı."""
        return float(self._data.get("zoom", {}).get("base_factor", _DEFAULT_ZOOM["base_factor"]))

    @property
    def zoom_accel_factor(self) -> float:
        """Ardışık tekerlek hareketlerinde uygulanacak ivmelenme çarpanı."""
        return float(
            self._data.get("zoom", {}).get("acceleration_factor", _DEFAULT_ZOOM["acceleration_factor"])
        )

    @property
    def zoom_max_char_width(self) -> float:
        """İzin verilen maksimum karakter genişliği (piksel)."""
        return float(
            self._data.get("zoom", {}).get("max_char_width", _DEFAULT_ZOOM["max_char_width"])
        )

    # ------------------------------------------------------------------
    # Ham veri erişimi (gelişmiş kullanım)
    # ------------------------------------------------------------------

    def raw_binding(self, section: str, action_key: str) -> dict:
        """JSON'daki ham bağlama kaydını döner; yoksa boş dict."""
        return dict(self._data.get(section, {}).get(action_key, {}))

    # ------------------------------------------------------------------
    # Yeniden yükleme
    # ------------------------------------------------------------------

    def reload(self):
        """Yapılandırma dosyasını diskten yeniden yükler ve sinyal yayar."""
        self._load()
        self.bindingsChanged.emit()

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

    def _qt_modifier(self, section: str, action_key: str) -> int:
        """
        JSON section/action_key için Qt modifier flag döner.
        JSON'da bulunamazsa _BUILT_IN_DEFAULTS'a, o da yoksa NoModifier'a düşer.
        """
        raw = (
            self._data
            .get(section, {})
            .get(action_key, {})
            .get("modifier",
                 _BUILT_IN_DEFAULTS.get((section, action_key), "None"))
        )
        return _MODIFIER_STR_TO_QT.get(raw, Qt.NoModifier)


# ---------------------------------------------------------------------------
# Modül-düzeyinde singleton
# ---------------------------------------------------------------------------

mouse_binding_manager = MouseBindingManager()
