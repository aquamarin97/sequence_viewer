# settings/theme.py
"""
Uygulama tema sistemi.

Kullanım
--------
    from settings.theme import theme_manager, AppTheme

    # Mevcut temayı oku
    t = theme_manager.current

    # Tema değişikliğini dinle
    theme_manager.themeChanged.connect(my_widget.on_theme_changed)

    # Temayı değiştir
    theme_manager.set_dark()
    theme_manager.set_light()

Yeni widget eklerken
--------------------
    1. paintEvent / paint içinde renkleri sabit yazmak yerine
       theme_manager.current.<token> kullanın.
    2. __init__ içinde theme_manager.themeChanged.connect(self.update) ekleyin.
    Başka bir şey gerekmez.
"""

from __future__ import annotations

from dataclasses import dataclass

from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtGui import QColor


# ---------------------------------------------------------------------------
# Renk token kataloğu
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class AppTheme:
    """
    Uygulamada kullanılan tüm renk token'ları.

    frozen=True: tema nesneleri değiştirilemez;
    tema değiştirmek için ThemeManager.set_light/dark() kullanılır.
    """

    name: str                   # "light" | "dark"

    # --- Satır arkaplanları (zebra) ---
    row_bg_even:          QColor  # çift indeksli satırlar
    row_bg_odd:           QColor  # tek indeksli satırlar

    # --- Satır durumları ---
    row_bg_hover:         QColor  # fare üzerindeyken (seçili değil)
    row_bg_selected:      QColor  # seçili, fare dışında
    row_bg_selected_hover:QColor  # seçili + fare üzerinde
    row_bg_dragging:      QColor  # sürükleniyor

    # --- Metin ---
    text_primary:         QColor  # normal satır metni
    text_selected:        QColor  # seçili satır metni

    # --- Kenarlık / çizgi ---
    border_normal:        QColor  # satır alt çizgisi
    border_drag:          QColor  # drag modunda item kenarlığı
    drop_indicator:       QColor  # drop indicator çizgisi ve daire

    # --- Inline editor (CSS string) ---
    editor_bg:            str     # örn. "#EEF4FF"
    editor_border:        str     # örn. "#5B8DEF"


# ---------------------------------------------------------------------------
# Hazır tema sabitleri
# ---------------------------------------------------------------------------

LIGHT_THEME = AppTheme(
    name                 = "light",

    row_bg_even          = QColor(255, 255, 255),   # saf beyaz
    row_bg_odd           = QColor(244, 246, 250),   # çok hafif gri-mavi

    row_bg_hover         = QColor(224, 235, 255),   # soluk mavi
    row_bg_selected      = QColor(193, 214, 255),   # orta mavi
    row_bg_selected_hover= QColor(170, 200, 255),   # biraz daha koyu mavi
    row_bg_dragging      = QColor(200, 215, 245),   # drag mavi

    text_primary         = QColor( 30,  30,  30),   # neredeyse siyah
    text_selected        = QColor(  0,  30,  90),   # koyu lacivert

    border_normal        = QColor(210, 215, 225),   # açık gri çizgi
    border_drag          = QColor(100, 140, 220),   # mavi dashed kenarlık
    drop_indicator       = QColor( 60, 120, 240),   # drop çizgisi

    editor_bg            = "#EEF4FF",
    editor_border        = "#5B8DEF",
)

DARK_THEME = AppTheme(
    name                 = "dark",

    row_bg_even          = QColor( 30,  32,  38),
    row_bg_odd           = QColor( 36,  38,  46),

    row_bg_hover         = QColor( 50,  60,  90),
    row_bg_selected      = QColor( 40,  80, 160),
    row_bg_selected_hover= QColor( 50,  95, 180),
    row_bg_dragging      = QColor( 45,  70, 140),

    text_primary         = QColor(210, 215, 225),
    text_selected        = QColor(220, 235, 255),

    border_normal        = QColor( 55,  60,  72),
    border_drag          = QColor( 90, 140, 230),
    drop_indicator       = QColor( 80, 150, 255),

    editor_bg            = "#1E2A4A",
    editor_border        = "#4A80E0",
)


# ---------------------------------------------------------------------------
# ThemeManager — singleton
# ---------------------------------------------------------------------------

class _ThemeManager(QObject):
    """
    Aktif temayı tutar ve değişiklikte sinyal yayınlar.

    Widget'lar __init__ içinde:
        theme_manager.themeChanged.connect(self.update)
    bağlantısını kurar; başka bir şey gerekmez.
    """

    themeChanged = pyqtSignal(object)   # AppTheme nesnesi iletilir

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


# Modül düzeyinde tek örnek — her yerden import edilebilir
theme_manager = _ThemeManager()