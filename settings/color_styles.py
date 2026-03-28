# settings/color_styles.py
"""
Uygulama renk stili sistemi.

Bu modül SEMANTIC olmayan, içerik-spesifik renkleri merkezi olarak yönetir:
    - Nükleotid renkleri  (A, T, C, G, -, N)
    - Annotasyon tip renkleri (PRIMER, PROBE, REPEATED_REGION)

Ayrım
-----
`theme.py`  → Semantic UI token'ları (arka plan, metin, kenar rengi, seçim rengi…)
              Bunlar widget'ların yapısal görünümünü belirler.

`color_styles.py` → İçerik renkleri (biyolojik veri gösterimi).
                    Bunlar kullanıcının kişiselleştirebileceği görsel tercihlerdir.

Kullanım
--------
    from settings.color_styles import color_style_manager

    # Nükleotid rengi
    color = color_style_manager.nucleotide_color("A")

    # Annotasyon tip rengi
    color = color_style_manager.annotation_color(AnnotationType.PRIMER)

    # Renk değiştir (ileride Settings diyaloğundan çağrılacak)
    color_style_manager.set_nucleotide_color("A", QColor(0, 200, 0))

    # Değişimi dinle
    color_style_manager.stylesChanged.connect(self.update)

Genişletme
----------
Yeni bir AnnotationType eklendiğinde `_DEFAULT_ANNOTATION_COLORS`
sözlüğüne karşılık gelen rengi eklemek yeterlidir.
"""

from __future__ import annotations

from typing import Dict, Optional

from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtGui import QColor

# AnnotationType import'u döngüsel bağımlılık yaratmaz;
# model/annotation.py → settings'e import etmez.
from model.annotation import AnnotationType


# ---------------------------------------------------------------------------
# Varsayılan renk paletleri
# ---------------------------------------------------------------------------

_DEFAULT_NUCLEOTIDE_COLORS: Dict[str, QColor] = {
    "A": QColor(  0, 180,   0),   # yeşil
    "T": QColor(200,   0,   0),   # kırmızı
    "U": QColor(200,   0,   0),   # kırmızı (RNA)
    "C": QColor(52, 152, 219),   # mavi
    "G": QColor(230, 140,   0),   # turuncu
    "-": QColor(150, 150, 150),   # gri (gap)
    "N": QColor(120, 120, 120),   # koyu gri (belirsiz)
}

_DEFAULT_ANNOTATION_COLORS: Dict[AnnotationType, QColor] = {
    AnnotationType.PRIMER:          QColor( 52, 152, 219),  # mavi
    AnnotationType.PROBE:           QColor( 39, 174,  96),  # yeşil
    AnnotationType.REPEATED_REGION: QColor(243, 156,  18),  # turuncu
}


# ---------------------------------------------------------------------------
# ColorStyleManager
# ---------------------------------------------------------------------------

class _ColorStyleManager(QObject):
    """
    İçerik renklerini tutar ve değiştiğinde sinyal yayınlar.

    İki renk grubu:
    - nucleotide_colors  : tek karakter → QColor
    - annotation_colors  : AnnotationType → QColor

    Her iki grup da bağımsız olarak güncellenebilir.
    """

    stylesChanged = pyqtSignal()   # herhangi bir renk değiştiğinde

    def __init__(self) -> None:
        super().__init__()
        # Kopyasını al — orijinal varsayılanlar bozulmasın
        self._nucleotide: Dict[str, QColor] = {
            k: QColor(v) for k, v in _DEFAULT_NUCLEOTIDE_COLORS.items()
        }
        self._annotation: Dict[AnnotationType, QColor] = {
            k: QColor(v) for k, v in _DEFAULT_ANNOTATION_COLORS.items()
        }

    # ------------------------------------------------------------------
    # Nükleotid renkleri
    # ------------------------------------------------------------------

    def nucleotide_color(self, base: str) -> QColor:
        """
        Tek nükleotid karakteri için renk döner.
        Bilinmeyen karakter için varsayılan gri kullanılır.
        """
        return QColor(
            self._nucleotide.get(base.upper(),
            self._nucleotide.get("N", QColor(80, 80, 80)))
        )

    def nucleotide_color_map(self) -> Dict[str, QColor]:
        """
        Tüm nükleotid renk haritasının bir kopyasını döner.
        `sequence_glyph_cache.default_nucleotide_color_map()` yerine
        bu metod kullanılmalıdır.
        """
        return {k: QColor(v) for k, v in self._nucleotide.items()}

    def set_nucleotide_color(self, base: str, color: QColor) -> None:
        """Bir nükleotid için rengi günceller."""
        key = base.upper()
        if key not in self._nucleotide or self._nucleotide[key] != color:
            self._nucleotide[key] = QColor(color)
            self.stylesChanged.emit()

    def reset_nucleotide_colors(self) -> None:
        """Nükleotid renklerini fabrika ayarlarına döndürür."""
        self._nucleotide = {
            k: QColor(v) for k, v in _DEFAULT_NUCLEOTIDE_COLORS.items()
        }
        self.stylesChanged.emit()

    # ------------------------------------------------------------------
    # Annotasyon tip renkleri
    # ------------------------------------------------------------------

    def annotation_color(self, ann_type: AnnotationType) -> QColor:
        """
        Annotasyon tipi için varsayılan rengi döner.
        `Annotation.resolved_color()` bu kaynağa başvurur.
        """
        return QColor(
            self._annotation.get(ann_type,
            QColor(128, 128, 128))   # tanımsız tip için gri
        )

    def set_annotation_color(self, ann_type: AnnotationType, color: QColor) -> None:
        """Bir annotasyon tipi için rengi günceller."""
        if self._annotation.get(ann_type) != color:
            self._annotation[ann_type] = QColor(color)
            self.stylesChanged.emit()

    def reset_annotation_colors(self) -> None:
        """Annotasyon renklerini fabrika ayarlarına döndürür."""
        self._annotation = {
            k: QColor(v) for k, v in _DEFAULT_ANNOTATION_COLORS.items()
        }
        self.stylesChanged.emit()

    # ------------------------------------------------------------------
    # Toplu sıfırlama
    # ------------------------------------------------------------------

    def reset_all(self) -> None:
        """Tüm renkleri fabrika ayarlarına döndürür."""
        self._nucleotide = {
            k: QColor(v) for k, v in _DEFAULT_NUCLEOTIDE_COLORS.items()
        }
        self._annotation = {
            k: QColor(v) for k, v in _DEFAULT_ANNOTATION_COLORS.items()
        }
        self.stylesChanged.emit()

    # ------------------------------------------------------------------
    # Serileştirme (ileride persistence için)
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        """Tüm renk ayarlarını JSON-serileştirilebilir dict olarak döner."""
        return {
            "nucleotide": {
                k: v.name() for k, v in self._nucleotide.items()
            },
            "annotation": {
                ann_type.name: color.name()
                for ann_type, color in self._annotation.items()
            },
        }

    def from_dict(self, data: dict) -> None:
        """Daha önce `to_dict()` ile kaydedilmiş ayarları yükler."""
        changed = False

        for base, hex_color in data.get("nucleotide", {}).items():
            color = QColor(hex_color)
            if color.isValid() and base in self._nucleotide:
                self._nucleotide[base] = color
                changed = True

        for type_name, hex_color in data.get("annotation", {}).items():
            color = QColor(hex_color)
            if not color.isValid():
                continue
            try:
                ann_type = AnnotationType[type_name]
                self._annotation[ann_type] = color
                changed = True
            except KeyError:
                pass   # Bilinmeyen tip — yoksay

        if changed:
            self.stylesChanged.emit()


# Modül düzeyinde tek örnek
color_style_manager = _ColorStyleManager()