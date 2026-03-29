# settings/theme.py
"""
Uygulama tema sistemi.

Token grupları
--------------
row_bg_*    → Header/sequence satır arkaplanları (zebra, seçim, hover)
text_*      → Metin renkleri
border_*    → Kenarlık ve çizgi renkleri
ruler_*     → Navigation ruler + Position ruler arkaplan/metin
seq_*       → Sequence görüntüleme (hücre arkaplanı, seçim, line modu)
editor_*    → Inline edit alanı (CSS string)
drop_*      → Drag & drop göstergeleri

Yeni widget eklerken
--------------------
1. paintEvent / paint içinde renkleri sabit yazmak yerine
   theme_manager.current.<token> kullanın.
2. __init__ içinde theme_manager.themeChanged.connect(self.update) ekleyin.
"""

from __future__ import annotations
from dataclasses import dataclass
from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtGui import QColor


@dataclass(frozen=True)
class AppTheme:
    name: str

    # --- Satır arkaplanları (zebra) ---
    row_bg_even:          QColor
    row_bg_odd:           QColor
    row_bg_hover:         QColor
    row_bg_selected:      QColor
    row_bg_selected_hover:QColor
    row_bg_dragging:      QColor

    # --- Metin ---
    text_primary:         QColor
    text_selected:        QColor

    # --- Kenarlık / çizgi ---
    border_normal:        QColor
    border_drag:          QColor
    drop_indicator:       QColor

    # --- Ruler (navigation minimap + position cetvel) ---
    ruler_bg:             QColor   # cetvel arkaplanı
    ruler_fg:             QColor   # cetvel metin ve tick rengi
    ruler_border:         QColor   # cetvel çerçeve rengi
    ruler_selection_fg:   QColor   # seçili pozisyon label rengi (bold)

    # --- Sequence hücresi ---
    seq_bg:               QColor   # dizi hücresi arkaplanı
    seq_selection_bg:     QColor   # seçim highlight arkaplanı
    seq_line_fg:          QColor   # LINE modu çizgi rengi

    # --- Inline editor (CSS string) ---
    editor_bg:            str
    editor_border:        str


# ---------------------------------------------------------------------------
# Hazır tema sabitleri
# ---------------------------------------------------------------------------

LIGHT_THEME = AppTheme(
    name                  = "light",

    row_bg_even           = QColor(255, 255, 255),
    row_bg_odd            = QColor(244, 246, 250),
    row_bg_hover          = QColor(224, 235, 255),
    row_bg_selected       = QColor(193, 214, 255),
    row_bg_selected_hover = QColor(170, 200, 255),
    row_bg_dragging       = QColor(200, 215, 245),

    text_primary          = QColor( 30,  30,  30),
    text_selected         = QColor(  0,  30,  90),

    border_normal         = QColor(210, 215, 225),
    border_drag           = QColor(100, 140, 220),
    drop_indicator        = QColor( 60, 120, 240),

    # Ruler — light: beyaz zemin, siyah metin
    ruler_bg              = QColor(255, 255, 255),
    ruler_fg              = QColor( 30,  30,  30),
    ruler_border          = QColor(180, 185, 195),
    ruler_selection_fg    = QColor(  0,   0, 200),

    # Sequence hücresi — light: beyaz zemin
    # seq_selection_bg yarı saydam kullanılır (alpha=120) — baz rengi altında görünür.
    seq_bg                = QColor(255, 255, 255),
    seq_selection_bg      = QColor(100, 160, 220),   # steel-blue, yarı saydam overlay
    seq_line_fg           = QColor(160, 160, 160),

    editor_bg             = "#EEF4FF",
    editor_border         = "#5B8DEF",
)

DARK_THEME = AppTheme(
    name                  = "dark",

    row_bg_even           = QColor( 30,  32,  38),
    row_bg_odd            = QColor( 36,  38,  46),
    row_bg_hover          = QColor( 50,  60,  90),
    row_bg_selected       = QColor( 40,  80, 160),
    row_bg_selected_hover = QColor( 50,  95, 180),
    row_bg_dragging       = QColor( 45,  70, 140),

    text_primary          = QColor(210, 215, 225),
    text_selected         = QColor(220, 235, 255),

    border_normal         = QColor( 55,  60,  72),
    border_drag           = QColor( 90, 140, 230),
    drop_indicator        = QColor( 80, 150, 255),

    # Ruler — dark: koyu zemin, açık metin
    ruler_bg              = QColor( 22,  24,  30),
    ruler_fg              = QColor(190, 195, 210),
    ruler_border          = QColor( 55,  60,  72),
    ruler_selection_fg    = QColor(100, 160, 255),

    # Sequence hücresi — dark: koyu zemin
    # seq_selection_bg yarı saydam kullanılır (alpha=110) — baz rengi altında görünür.
    seq_bg                = QColor( 28,  30,  36),
    seq_selection_bg      = QColor( 80,  40, 120),   # deep-purple, yarı saydam overlay
    seq_line_fg           = QColor(100, 105, 120),

    editor_bg             = "#1E2A4A",
    editor_border         = "#4A80E0",
)


class _ThemeManager(QObject):
    themeChanged = pyqtSignal(object)

    def __init__(self) -> None:
        super().__init__()
        self._current: AppTheme = LIGHT_THEME

    @property
    def current(self) -> AppTheme:
        return self._current

    def set_light(self) -> None:
        if self._current.name != "light":
            self._current = LIGHT_THEME
            self.themeChanged.emit(self._current)

    def set_dark(self) -> None:
        if self._current.name != "dark":
            self._current = DARK_THEME
            self.themeChanged.emit(self._current)

    def toggle(self) -> None:
        if self._current.name == "light":
            self.set_dark()
        else:
            self.set_light()


theme_manager = _ThemeManager()