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

    # Zebra: daha temiz, daha profesyonel, düşük gürültü
    row_bg_even           = QColor(255, 255, 255),
    row_bg_odd            = QColor(247, 249, 253),

    # Hover: selected ile karışmayacak kadar hafif
    row_bg_hover          = QColor(232, 240, 255),

    # Selected: net ve güçlü vurgu
    row_bg_selected       = QColor(76, 125, 255),
    row_bg_selected_hover = QColor(64, 110, 235),

    # Dragging: selected’dan farklılaşan hafif morumsu mavi
    row_bg_dragging       = QColor(108, 118, 245),

    # Metin: daha dengeli kontrast
    text_primary          = QColor(28, 32, 40),
    text_selected         = QColor(255, 255, 255),

    # Border: daha temiz separation
    border_normal         = QColor(205, 211, 222),
    border_drag           = QColor(88, 122, 245),
    drop_indicator        = QColor(70, 110, 235),

    # Ruler
    ruler_bg              = QColor(255, 255, 255),
    ruler_fg              = QColor(42, 46, 56),
    ruler_border          = QColor(196, 202, 214),
    ruler_selection_fg    = QColor(46, 92, 220),

    # Sequence alanı
    seq_bg                = QColor(255, 255, 255),
    seq_selection_bg      = QColor(76, 125, 255),

    # Eskiye göre daha görünür line rengi
    seq_line_fg           = QColor(112, 118, 130),

    # Inline editor
    editor_bg             = "#F4F7FF",
    editor_border         = "#4C7DFF",
)

DARK_THEME = AppTheme(
    name                  = "dark",

    # Nötr koyu taban: saf siyah değil
    row_bg_even           = QColor(26, 28, 34),
    row_bg_odd            = QColor(32, 34, 42),

    # Hover: selected’dan belirgin şekilde daha hafif
    row_bg_hover          = QColor(43, 53, 80),

    # Selected: güçlü ama göz yormayan mavi
    row_bg_selected       = QColor(62, 102, 196),
    row_bg_selected_hover = QColor(78, 122, 224),

    # Dragging: selected’dan ayrışan ton
    row_bg_dragging       = QColor(92, 96, 210),

    text_primary          = QColor(220, 225, 235),
    text_selected         = QColor(255, 255, 255),

    border_normal         = QColor(61, 66, 80),
    border_drag           = QColor(98, 132, 245),
    drop_indicator        = QColor(112, 150, 255),

    # Ruler
    ruler_bg              = QColor(20, 22, 28),
    ruler_fg              = QColor(192, 198, 212),
    ruler_border          = QColor(61, 66, 80),
    ruler_selection_fg    = QColor(122, 170, 255),

    # Sequence alanı
    seq_bg                = QColor(24, 26, 32),
    seq_selection_bg      = QColor(62, 102, 196),
    seq_line_fg           = QColor(122, 128, 142),

    editor_bg             = "#1C2540",
    editor_border         = "#5A8CFF",
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