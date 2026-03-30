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
    # YENİ: header/sequence satır seçiminde bant vurgusu
    row_band_highlight:   QColor = None

    def __post_init__(self):
        if self.row_band_highlight is None:
            # frozen dataclass workaround
            object.__setattr__(self, 'row_band_highlight',
                QColor(60, 100, 180, 45) if self.name == "dark" else QColor(70, 130, 220, 40))

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
