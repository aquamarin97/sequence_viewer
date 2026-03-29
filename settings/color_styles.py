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

# Light mod: Jalview tarzı profesyonel, dengeli renkler
# Her baz WCAG ≥4.5:1 beyaz arka plan üzerinde.
_NUCLEOTIDE_COLORS_LIGHT: Dict[str, QColor] = {
    "A": QColor( 21, 128,  61),   # yeşil   — orman tonu
    "T": QColor(185,  28,  28),   # kırmızı — güçlü, aşırı değil
    "U": QColor(185,  28,  28),   # kırmızı — RNA
    "C": QColor( 29,  78, 216),   # mavi    — koyu kobalt
    "G": QColor(161,  98,   7),   # turuncu — sıcak amber
    "-": QColor(100, 116, 139),   # gri     — nötr boşluk
    "N": QColor(107, 114, 128),   # gri     — belirsiz baz
}

# Dark mod: göz yormayan orta parlaklıkta renkler.
# Parlak neon yerine sakin, doygun renkler tercih edildi.
_NUCLEOTIDE_COLORS_DARK: Dict[str, QColor] = {
    "A": QColor( 74, 199, 120),   # yeşil   — sakin parlak yeşil
    "T": QColor(220,  90,  90),   # kırmızı — yumuşak mercan
    "U": QColor(220,  90,  90),   # kırmızı — RNA
    "C": QColor( 88, 152, 235),   # mavi    — sakin gökyüzü
    "G": QColor(218, 160,  50),   # turuncu — sıcak altın
    "-": QColor(140, 148, 162),   # gri     — orta gri
    "N": QColor(130, 140, 158),   # gri     — belirsiz baz
}

# ---------------------------------------------------------------------------
# Konsensüs satırına özel renkler — TÜM BAZLAR
# ---------------------------------------------------------------------------
# Konsensüs satırı diziden daha çok odaklanılan alan olduğu için
# tüm bazlar sekans renklerinin aynı tonunda ama daha canlı/doygun versiyonları.
# Light: S+20, L-8  → daha doygun ve koyu (beyaz zeminde daha güçlü)
# Dark:  S+15, L+12 → daha parlak/vivid (koyu zeminde daha baskın)
_CONSENSUS_COLORS: dict = {
    "light": {
        "A": QColor(  0, 170,  80),   # canlı orman yeşili
        "T": QColor(220,  30,  30),   # derin güçlü kırmızı
        "U": QColor(220,  30,  30),   # RNA
        "C": QColor( 20, 100, 255),   # parlak elektrik mavisi
        "G": QColor(255, 140,   0),   # canlı turuncu
        "-": QColor( 75,  85, 105),   # koyu gri
        "N": QColor(100, 110, 130),   # nötr koyu
    },
    "dark": {
        "A": QColor( 40, 255, 110),   # neon yeşil
        "T": QColor(255,  60,  60),   # elektrik kırmızısı
        "U": QColor(255,  70, 160),   # magenta-pembe (RNA)
        "C": QColor( 30, 220, 255),   # parlak cyan
        "G": QColor(255, 190,  30),   # parlak altın
        "-": QColor(110, 120, 140),   # orta gri
        "N": QColor(140, 150, 170),   # yumuşak gri
    },
}

_DEFAULT_NUCLEOTIDE_COLORS = _NUCLEOTIDE_COLORS_LIGHT

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

    def consensus_nucleotide_color_map(self) -> Dict[str, QColor]:
        """
        Konsensüs satırı için renk haritası.
        Tüm bazlar sekans renklerinin aynı tonunda ama daha canlı/doygun
        versiyonlarıdır — konsensüs satırı görsel odak noktasıdır.
        """
        base = {k: QColor(v) for k, v in self._nucleotide.items()}
        try:
            from settings.theme import theme_manager
            overrides = _CONSENSUS_COLORS.get(theme_manager.current.name, {})
        except Exception:
            overrides = {}
        base.update({k: QColor(v) for k, v in overrides.items()})
        return base

    def apply_theme(self, theme_name: str) -> None:
        """Tema değişince uygun nükleotid paletini aktif eder."""
        palette = (
            _NUCLEOTIDE_COLORS_DARK if theme_name == "dark"
            else _NUCLEOTIDE_COLORS_LIGHT
        )
        new_nuc = {k: QColor(v) for k, v in palette.items()}
        if new_nuc != self._nucleotide:
            self._nucleotide = new_nuc
            self.stylesChanged.emit()

    def set_nucleotide_color(self, base: str, color: QColor) -> None:
        """Bir nükleotid için rengi günceller."""
        key = base.upper()
        if key not in self._nucleotide or self._nucleotide[key] != color:
            self._nucleotide[key] = QColor(color)
            self.stylesChanged.emit()

    def reset_nucleotide_colors(self) -> None:
        """Nükleotid renklerini aktif tema paletine döndürür."""
        try:
            from settings.theme import theme_manager
            palette = (
                _NUCLEOTIDE_COLORS_DARK if theme_manager.current.name == "dark"
                else _NUCLEOTIDE_COLORS_LIGHT
            )
        except Exception:
            palette = _NUCLEOTIDE_COLORS_LIGHT
        self._nucleotide = {k: QColor(v) for k, v in palette.items()}
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