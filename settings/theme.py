# settings/theme.py
"""
Uygulama tema sistemi.

Token grupları - YENİ: row_band_highlight eklendi.
"""
from __future__ import annotations
from dataclasses import dataclass
from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtGui import QColor

@dataclass(frozen=True)
class AppTheme:
    name: str
    row_bg_even:          QColor
    row_bg_odd:           QColor
    row_bg_hover:         QColor
    row_bg_selected:      QColor
    row_bg_selected_hover:QColor
    row_bg_dragging:      QColor
    text_primary:         QColor
    text_selected:        QColor
    border_normal:        QColor
    border_drag:          QColor
    drop_indicator:       QColor
    ruler_bg:             QColor
    nav_ruler_bg:         QColor
    ruler_fg:             QColor
    ruler_border:         QColor
    ruler_selection_fg:   QColor
    seq_bg:               QColor
    seq_selection_bg:     QColor
    seq_line_fg:          QColor
    editor_bg:            str
    editor_border:        str
    # header/sequence satır seçiminde bant vurgusu
    row_band_highlight:   QColor = None

    # ── Kılavuz çizgileri (Guide Lines) ──────────────────────────────────────
    # Dikey ve yatay kılavuz çizgilerinin rengi (yarı saydam mavi).
    # Hem SequenceViewerView hem ConsensusRowWidget tarafından kullanılır.
    guide_line_color:          QColor = None

    # ── Seçim odak efekti: seçim dışı alan kararması ──────────────────────────
    # Drag seçimi sırasında ve sonrasında, seçim aralığının dışındaki kolonlar
    # üzerine yarı saydam bir overlay çizilerek arka plana itilir.
    selection_dim_color:       QColor = None

    # ── Navigation Ruler: Görünüm Penceresi ──────────────────────────────────
    # Ekranda görünen bölgeyi mini harita üzerinde gösteren dikdörtgen.
    nav_ruler_viewport_fill:   QColor = None   # iç dolgu (düşük alfa)
    nav_ruler_viewport_border: QColor = None   # kenarlık

    # ── Navigation Ruler: Sürükleme Seçimi ───────────────────────────────────
    # Kullanıcı fare ile yeni bir görüntüleme aralığı sürüklerken çizilen geçici kutu.
    nav_ruler_drag_fill:       QColor = None   # iç dolgu (düşük alfa)
    nav_ruler_drag_border:     QColor = None   # kenarlık

    def __post_init__(self):
        if self.row_band_highlight is None:
            # frozen dataclass workaround
            object.__setattr__(self, 'row_band_highlight',
                QColor(60, 100, 180, 45) if self.name == "dark" else QColor(70, 130, 220, 40))
        if self.guide_line_color is None:
            # Her iki temada da aynı renk; alfa kanalı saydamlığı sağlar
            object.__setattr__(self, 'guide_line_color', QColor(80, 130, 220, 160))
        if self.selection_dim_color is None:
            object.__setattr__(self, 'selection_dim_color',
                QColor(0, 0, 0, 155) if self.name == "dark" else QColor(255, 255, 255, 155))
        if self.nav_ruler_viewport_fill is None:
            object.__setattr__(self, 'nav_ruler_viewport_fill',
                QColor(0, 180, 0, 55) if self.name == "dark" else QColor(0, 200, 0, 60))
        if self.nav_ruler_viewport_border is None:
            object.__setattr__(self, 'nav_ruler_viewport_border',
                QColor(0, 140, 0) if self.name == "dark" else QColor(0, 150, 0))
        if self.nav_ruler_drag_fill is None:
            object.__setattr__(self, 'nav_ruler_drag_fill',
                QColor(80, 80, 255, 50) if self.name == "dark" else QColor(0, 0, 255, 40))
        if self.nav_ruler_drag_border is None:
            object.__setattr__(self, 'nav_ruler_drag_border',
                QColor(80, 80, 200) if self.name == "dark" else QColor(0, 0, 160))

LIGHT_THEME = AppTheme(
    name="light",
    row_bg_even=QColor(255,255,255), row_bg_odd=QColor(244,246,250),
    row_bg_hover=QColor(224,235,255), row_bg_selected=QColor(193,214,255),
    row_bg_selected_hover=QColor(170,200,255), row_bg_dragging=QColor(200,215,245),
    text_primary=QColor(30,30,30), text_selected=QColor(0,30,90),
    border_normal=QColor(210,215,225), border_drag=QColor(100,140,220),
    drop_indicator=QColor(60,120,240),
    ruler_bg=QColor(255,255,255), nav_ruler_bg=QColor(236,238,244),
    ruler_fg=QColor(30,30,30), ruler_border=QColor(180,185,195),
    ruler_selection_fg=QColor(0,0,200),
    seq_bg=QColor(255,255,255),
    seq_selection_bg=QColor(100,160,220),
    seq_line_fg=QColor(160,160,160),
    editor_bg="#EEF4FF", editor_border="#5B8DEF",
    row_band_highlight=QColor(70, 130, 220, 40),
    # Guide lines
    guide_line_color=QColor(80, 130, 220, 160),
    # Selection dim overlay
    selection_dim_color=QColor(255, 255, 255, 155),
    # Navigation ruler
    nav_ruler_viewport_fill=QColor(0, 200, 0, 60),
    nav_ruler_viewport_border=QColor(0, 150, 0),
    nav_ruler_drag_fill=QColor(0, 0, 255, 40),
    nav_ruler_drag_border=QColor(0, 0, 160),
)

DARK_THEME = AppTheme(
    name="dark",
    row_bg_even=QColor(30,32,38), row_bg_odd=QColor(36,38,46),
    row_bg_hover=QColor(50,60,90), row_bg_selected=QColor(40,80,160),
    row_bg_selected_hover=QColor(50,95,180), row_bg_dragging=QColor(45,70,140),
    text_primary=QColor(210,215,225), text_selected=QColor(220,235,255),
    border_normal=QColor(55,60,72), border_drag=QColor(90,140,230),
    drop_indicator=QColor(80,150,255),
    ruler_bg=QColor(22,24,30), nav_ruler_bg=QColor(36,38,46),
    ruler_fg=QColor(190,195,210), ruler_border=QColor(55,60,72),
    ruler_selection_fg=QColor(100,160,255),
    seq_bg=QColor(28,30,36),
    seq_selection_bg=QColor(62,102,196),
    seq_line_fg=QColor(100,105,120),
    editor_bg="#1E2A4A", editor_border="#4A80E0",
    row_band_highlight=QColor(60, 100, 180, 45),
    # Guide lines
    guide_line_color=QColor(193, 16, 160),
    # Selection dim overlay
    selection_dim_color=QColor(0, 0, 0, 155),
    # Navigation ruler
    nav_ruler_viewport_fill=QColor(0, 180, 0, 55),
    nav_ruler_viewport_border=QColor(0, 140, 0),
    nav_ruler_drag_fill=QColor(80, 80, 255, 50),
    nav_ruler_drag_border=QColor(80, 80, 200),
)

class _ThemeManager(QObject):
    themeChanged = pyqtSignal(object)
    def __init__(self):
        super().__init__()
        self._current = LIGHT_THEME
    @property
    def current(self): return self._current
    def set_light(self):
        if self._current.name != "light":
            self._current = LIGHT_THEME
            self.themeChanged.emit(self._current)
    def set_dark(self):
        if self._current.name != "dark":
            self._current = DARK_THEME
            self.themeChanged.emit(self._current)
    def toggle(self):
        if self._current.name == "light": self.set_dark()
        else: self.set_light()

theme_manager = _ThemeManager()
