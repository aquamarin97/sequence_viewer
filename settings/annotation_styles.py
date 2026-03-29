# settings/annotation_styles.py
"""
Annotation görsel stil sistemi.

Bu modül annotation tiplerinin GÖRSEL parametrelerini merkezi olarak yönetir:
    - Dolgu saydamlığı  (fill_alpha)
    - Kenar saydamlığı  (border_alpha)
    - Kenar kalınlığı   (border_width)
    - Etiket minimum genişliği (label_min_width)
    - Etiket font boyutu       (label_font_size)

Ayrım
-----
`color_styles.py`       → Renk değerleri (RGB)
`annotation_styles.py`  → Görsel stil parametreleri (alpha, width, font)

İkisi birlikte annotation_painter.py tarafından tüketilir.

Kullanım
--------
    from settings.annotation_styles import annotation_style_manager

    style = annotation_style_manager.get(AnnotationType.PRIMER)
    fill_color = QColor(base_color)
    fill_color.setAlpha(style.fill_alpha)

    # Tema değişince
    annotation_style_manager.stylesChanged.connect(self.update)

Genişletme
----------
Yeni AnnotationType eklendiğinde _STYLES_LIGHT ve _STYLES_DARK
sözlüklerine karşılık gelen AnnotationTypeStyle eklemek yeterlidir.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

from PyQt5.QtCore import QObject, pyqtSignal

from model.annotation import AnnotationType


@dataclass(frozen=True)
class AnnotationTypeStyle:
    """
    Tek bir annotation tipinin görsel parametreleri.

    fill_alpha      : Dolgu rengi saydamlığı (0=tamamen şeffaf, 255=tamamen opak).
    border_alpha    : Kenar rengi saydamlığı.
    border_width    : Kenar kalınlığı piksel cinsinden. 0.0 → kenar çizilmez.
    label_min_width : Etiket çizilmesi için gereken minimum piksel genişliği.
    label_font_size : Etiket font boyutu (pt). 0 → varsayılan (7pt).
    """
    fill_alpha:      int
    border_alpha:    int
    border_width:    float
    label_min_width: int
    label_font_size: int = 7


# ---------------------------------------------------------------------------
# Varsayılan stiller — Light mod
# ---------------------------------------------------------------------------
_STYLES_LIGHT: Dict[AnnotationType, AnnotationTypeStyle] = {
    AnnotationType.PRIMER: AnnotationTypeStyle(
        fill_alpha      = 255,    # tam opak — güçlü varlık
        border_alpha    = 0,      # kenar yok — temiz yamuk
        border_width    = 0.0,
        label_min_width = 20,
        label_font_size = 7,
    ),
    AnnotationType.PROBE: AnnotationTypeStyle(
        fill_alpha      = 165,    # %65 opak — primer'dan ayırt edilebilir
        border_alpha    = 220,    # güçlü kenar — sınırı belirtir
        border_width    = 1.5,
        label_min_width = 20,
        label_font_size = 7,
    ),
    AnnotationType.REPEATED_REGION: AnnotationTypeStyle(
        fill_alpha      = 55,     # çok saydam — sekans okunurluğunu bozmaz
        border_alpha    = 170,    # orta kenar — bölgeyi belirtir
        border_width    = 1.0,
        label_min_width = 24,
        label_font_size = 7,
    ),
}

# ---------------------------------------------------------------------------
# Varsayılan stiller — Dark mod
# ---------------------------------------------------------------------------
# Dark modda:
#   - PRIMER dolgusu biraz yumuşatılır (255 → 210): koyu zemin üzerinde çok baskın olmasın
#   - PROBE kenarlığı hafif azaltılır (220 → 190): koyu bg'da border daha az gerekli
#   - REPEATED_REGION dolgusu artırılır (55 → 75): koyu zeminde daha görünür olması için
_STYLES_DARK: Dict[AnnotationType, AnnotationTypeStyle] = {
    AnnotationType.PRIMER: AnnotationTypeStyle(
        fill_alpha      = 210,    # biraz saydam — koyu zeminde agresif değil
        border_alpha    = 0,
        border_width    = 0.0,
        label_min_width = 20,
        label_font_size = 7,
    ),
    AnnotationType.PROBE: AnnotationTypeStyle(
        fill_alpha      = 150,    # primer'dan belirgin fark korunur
        border_alpha    = 190,    # kenar hâlâ görünür ama daha yumuşak
        border_width    = 1.5,
        label_min_width = 20,
        label_font_size = 7,
    ),
    AnnotationType.REPEATED_REGION: AnnotationTypeStyle(
        fill_alpha      = 75,     # koyu zeminde biraz daha görünür
        border_alpha    = 160,    # kenar geri çekilir
        border_width    = 1.0,
        label_min_width = 24,
        label_font_size = 7,
    ),
}

# Aktif tema için çalışma zamanı kopyası başlangıçta light
_ACTIVE_STYLES: Dict[AnnotationType, AnnotationTypeStyle] = dict(_STYLES_LIGHT)


# ---------------------------------------------------------------------------
# AnnotationStyleManager
# ---------------------------------------------------------------------------

class _AnnotationStyleManager(QObject):
    """
    Annotation görsel stillerini tutar ve değiştiğinde sinyal yayınlar.

    Tema değişiminde `apply_theme(name)` çağrılır — bu, `workspace._on_theme_changed`
    içinde `color_style_manager.apply_theme()` ile birlikte çağrılmalıdır.
    """

    stylesChanged = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self._styles: Dict[AnnotationType, AnnotationTypeStyle] = dict(_STYLES_LIGHT)

    def get(self, ann_type: AnnotationType) -> AnnotationTypeStyle:
        """
        Verilen annotation tipi için aktif stili döner.
        Tanımsız tip için PRIMER stilini fallback olarak kullanır.
        """
        return self._styles.get(ann_type, _STYLES_LIGHT[AnnotationType.PRIMER])

    def apply_theme(self, theme_name: str) -> None:
        """
        Tema değişince (workspace._on_theme_changed içinden) çağrılır.
        Uygun stil setini aktif eder ve stylesChanged yayınlar.
        """
        new_styles = (
            dict(_STYLES_DARK) if theme_name == "dark"
            else dict(_STYLES_LIGHT)
        )
        if new_styles != self._styles:
            self._styles = new_styles
            self.stylesChanged.emit()

    def set_style(self, ann_type: AnnotationType, style: AnnotationTypeStyle) -> None:
        """Çalışma zamanında tek bir tipin stilini günceller (ileride Settings için)."""
        if self._styles.get(ann_type) != style:
            self._styles[ann_type] = style
            self.stylesChanged.emit()

    def reset(self, theme_name: str = "light") -> None:
        """Fabrika ayarlarına döner."""
        self.apply_theme(theme_name)


# Modül düzeyinde tek örnek
annotation_style_manager = _AnnotationStyleManager()