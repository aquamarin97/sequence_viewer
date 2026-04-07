# settings/color_styles.py
from __future__ import annotations
from typing import Dict, Optional
from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtGui import QColor
from model.annotation import AnnotationType

# Light theme için geliştirilmiş nükleotid renkleri
# G rengi daha koyu turuncu yapıldı (kontrast artırıldı)
_NUCLEOTIDE_COLORS_LIGHT = {
    "A": QColor(21,128,61), "T": QColor(185,28,28), "U": QColor(185,28,28),
    "C": QColor(29,78,216), "G": QColor(180,100,10),  # Kontrast artırıldı
    "-": QColor(100,116,139), "N": QColor(107,114,128),
}
_NUCLEOTIDE_COLORS_DARK = {
    "A": QColor(74,199,120), "T": QColor(220,90,90), "U": QColor(220,90,90),
    "C": QColor(88,152,235), "G": QColor(218,160,50),
    "-": QColor(140,148,162), "N": QColor(130,140,158),
}
# Consensus renkleri - U tutarlı kırmızı ailesinde tutuldu
_CONSENSUS_COLORS = {
    "light": {"A":QColor(0,170,80),"T":QColor(220,30,30),"U":QColor(220,30,30),"C":QColor(20,100,255),"G":QColor(255,140,0),"-":QColor(75,85,105),"N":QColor(100,110,130)},
    "dark": {"A":QColor(40,255,110),"T":QColor(255,60,60),"U":QColor(255,80,80),"C":QColor(30,220,255),"G":QColor(255,190,30),"-":QColor(110,120,140),"N":QColor(140,150,170)},  # U tutarlı kırmızı tonunda
}
_DEFAULT_NUCLEOTIDE_COLORS = _NUCLEOTIDE_COLORS_LIGHT
_DEFAULT_ANNOTATION_COLORS = {
    AnnotationType.PRIMER: QColor(52,152,219),
    AnnotationType.PROBE: QColor(39,174,96),
    AnnotationType.REPEATED_REGION: QColor(243,156,18),
}

# Renk körü (colorblind) modları için alternatif paletler
_COLORBLIND_MODES = {
    "deuteranopia": {  # Kırmızı-yeşil renk körlüğü
        "A": QColor(0,114,178),      # Mavi
        "T": QColor(230,159,0),      # Turuncu
        "U": QColor(230,159,0),      # Turuncu
        "C": QColor(86,180,233),     # Açık mavi
        "G": QColor(240,228,66),     # Sarı
        "-": QColor(100,116,139),
        "N": QColor(107,114,128),
    },
    "protanopia": {  # Kırmızı renk körlüğü
        "A": QColor(0,114,178),      # Mavi
        "T": QColor(213,94,0),       # Vermillion
        "U": QColor(213,94,0),       # Vermillion
        "C": QColor(86,180,233),     # Açık mavi
        "G": QColor(240,228,66),     # Sarı
        "-": QColor(100,116,139),
        "N": QColor(107,114,128),
    },
}

NUCLEOTIDE_BASE_ORDER = ("A", "T", "U", "C", "G", "-", "N")


def _clone_color_map(palette):
    return {k: QColor(v) for k, v in palette.items()}


def _clone_annotation_map(palette):
    return {k: QColor(v) for k, v in palette.items()}

class _ColorStyleManager(QObject):
    stylesChanged = pyqtSignal()
    def __init__(self):
        super().__init__()
        self._theme_palettes = {
            "light": _clone_color_map(_NUCLEOTIDE_COLORS_LIGHT),
            "dark": _clone_color_map(_NUCLEOTIDE_COLORS_DARK),
        }
        self._consensus_palettes = {
            "light": _clone_color_map(_CONSENSUS_COLORS["light"]),
            "dark": _clone_color_map(_CONSENSUS_COLORS["dark"]),
        }
        self._colorblind_palettes = {
            "deuteranopia": _clone_color_map(_COLORBLIND_MODES["deuteranopia"]),
            "protanopia": _clone_color_map(_COLORBLIND_MODES["protanopia"]),
        }
        self._nucleotide = _clone_color_map(_DEFAULT_NUCLEOTIDE_COLORS)
        self._annotation = _clone_annotation_map(_DEFAULT_ANNOTATION_COLORS)
        self._colorblind_mode = None  # None, "deuteranopia", veya "protanopia"

    def nucleotide_color(self, base):
        return QColor(self._nucleotide.get(base.upper(), self._nucleotide.get("N", QColor(80,80,80))))

    def nucleotide_color_map(self):
        return {k:QColor(v) for k,v in self._nucleotide.items()}

    def nucleotide_palette(self, palette_name: str):
        palette = self._theme_palettes.get(palette_name)
        return _clone_color_map(palette) if palette else {}

    def consensus_palette(self, theme_name: str):
        palette = self._consensus_palettes.get(theme_name)
        return _clone_color_map(palette) if palette else {}

    def colorblind_palette(self, mode: str):
        palette = self._colorblind_palettes.get(mode)
        return _clone_color_map(palette) if palette else {}

    def consensus_nucleotide_color_map(self):
        base = {k:QColor(v) for k,v in self._nucleotide.items()}
        try:
            from settings.theme import theme_manager
            overrides = self._consensus_palettes.get(theme_manager.current.name, {})
        except: overrides = {}
        base.update({k:QColor(v) for k,v in overrides.items()})
        return base

    def apply_theme(self, theme_name):
        # Colorblind mode aktifse, o paleti kullan
        if self._colorblind_mode:
            palette = self._colorblind_palettes.get(self._colorblind_mode, self._theme_palettes["light"])
        else:
            palette = self._theme_palettes["dark"] if theme_name == "dark" else self._theme_palettes["light"]
        new_nuc = _clone_color_map(palette)
        if new_nuc != self._nucleotide:
            self._nucleotide = new_nuc
            self.stylesChanged.emit()

    def set_colorblind_mode(self, mode: Optional[str]):
        """
        Renk körü modu ayarla.
        mode: None (normal), "deuteranopia" (kırmızı-yeşil), veya "protanopia" (kırmızı)
        """
        if mode not in (None, "deuteranopia", "protanopia"):
            return
        if self._colorblind_mode != mode:
            self._colorblind_mode = mode
            # Mevcut temayı yeniden uygula
            try:
                from settings.theme import theme_manager
                self.apply_theme(theme_manager.current.name)
            except:
                self.reset_nucleotide_colors()

    def get_colorblind_mode(self):
        return self._colorblind_mode

    def set_theme_palette_color(self, theme_name, base, color):
        palette = self._theme_palettes.get(theme_name)
        key = base.upper()
        if palette is None or key not in palette:
            return
        new_color = QColor(color)
        if palette[key] != new_color:
            palette[key] = new_color
            if self._colorblind_mode is None:
                try:
                    from settings.theme import theme_manager
                    active_theme = theme_manager.current.name
                except:
                    active_theme = "light"
                if active_theme == theme_name:
                    self.set_nucleotide_color(key, new_color)

    def set_consensus_palette_color(self, theme_name, base, color):
        palette = self._consensus_palettes.get(theme_name)
        key = base.upper()
        if palette is None or key not in palette:
            return
        new_color = QColor(color)
        if palette[key] != new_color:
            palette[key] = new_color
            try:
                from settings.theme import theme_manager
                if theme_manager.current.name == theme_name:
                    self.stylesChanged.emit()
            except:
                self.stylesChanged.emit()

    def set_colorblind_palette_color(self, mode, base, color):
        palette = self._colorblind_palettes.get(mode)
        key = base.upper()
        if palette is None or key not in palette:
            return
        new_color = QColor(color)
        if palette[key] != new_color:
            palette[key] = new_color
            if self._colorblind_mode == mode:
                self.set_nucleotide_color(key, new_color)

    def set_nucleotide_color(self, base, color):
        key = base.upper()
        if key not in self._nucleotide or self._nucleotide[key] != color:
            self._nucleotide[key] = QColor(color)
            self.stylesChanged.emit()

    def reset_nucleotide_colors(self):
        try:
            from settings.theme import theme_manager
            palette = self._theme_palettes["dark"] if theme_manager.current.name == "dark" else self._theme_palettes["light"]
        except: palette = self._theme_palettes["light"]
        self._nucleotide = _clone_color_map(palette)
        self.stylesChanged.emit()

    def annotation_color(self, ann_type):
        return QColor(self._annotation.get(ann_type, QColor(128,128,128)))

    def annotation_color_map(self):
        return _clone_annotation_map(self._annotation)

    def set_annotation_color(self, ann_type, color):
        if self._annotation.get(ann_type) != color:
            self._annotation[ann_type] = QColor(color)
            self.stylesChanged.emit()

    def reset_annotation_colors(self):
        self._annotation = _clone_annotation_map(_DEFAULT_ANNOTATION_COLORS)
        self.stylesChanged.emit()

    def reset_all(self):
        self._theme_palettes = {
            "light": _clone_color_map(_NUCLEOTIDE_COLORS_LIGHT),
            "dark": _clone_color_map(_NUCLEOTIDE_COLORS_DARK),
        }
        self._consensus_palettes = {
            "light": _clone_color_map(_CONSENSUS_COLORS["light"]),
            "dark": _clone_color_map(_CONSENSUS_COLORS["dark"]),
        }
        self._colorblind_palettes = {
            "deuteranopia": _clone_color_map(_COLORBLIND_MODES["deuteranopia"]),
            "protanopia": _clone_color_map(_COLORBLIND_MODES["protanopia"]),
        }
        self._nucleotide = _clone_color_map(_DEFAULT_NUCLEOTIDE_COLORS)
        self._annotation = _clone_annotation_map(_DEFAULT_ANNOTATION_COLORS)
        self._colorblind_mode = None
        self.stylesChanged.emit()

    def to_dict(self):
        return {
            "nucleotide":{k:v.name() for k,v in self._nucleotide.items()},
            "annotation":{t.name:c.name() for t,c in self._annotation.items()},
            "colorblind_mode": self._colorblind_mode
        }

    def from_dict(self, data):
        changed = False
        for base, hex_color in data.get("nucleotide",{}).items():
            color = QColor(hex_color)
            if color.isValid() and base in self._nucleotide:
                self._nucleotide[base] = color; changed = True
        for type_name, hex_color in data.get("annotation",{}).items():
            color = QColor(hex_color)
            if not color.isValid(): continue
            try:
                ann_type = AnnotationType[type_name]
                self._annotation[ann_type] = color; changed = True
            except KeyError: pass
        # Colorblind mode'u yükle
        colorblind_mode = data.get("colorblind_mode")
        if colorblind_mode in (None, "deuteranopia", "protanopia"):
            self._colorblind_mode = colorblind_mode
        if changed: self.stylesChanged.emit()

    def reset_theme_palette(self, theme_name):
        if theme_name == "dark":
            self._theme_palettes["dark"] = _clone_color_map(_NUCLEOTIDE_COLORS_DARK)
        else:
            self._theme_palettes["light"] = _clone_color_map(_NUCLEOTIDE_COLORS_LIGHT)
        if self._colorblind_mode is None:
            try:
                from settings.theme import theme_manager
                if theme_manager.current.name == theme_name:
                    self.apply_theme(theme_name)
            except:
                self.stylesChanged.emit()

    def reset_consensus_palette(self, theme_name):
        source = _CONSENSUS_COLORS["dark" if theme_name == "dark" else "light"]
        self._consensus_palettes["dark" if theme_name == "dark" else "light"] = _clone_color_map(source)
        self.stylesChanged.emit()

    def reset_colorblind_palette(self, mode):
        if mode not in self._colorblind_palettes:
            return
        self._colorblind_palettes[mode] = _clone_color_map(_COLORBLIND_MODES[mode])
        if self._colorblind_mode == mode:
            try:
                from settings.theme import theme_manager
                self.apply_theme(theme_manager.current.name)
            except:
                self.stylesChanged.emit()

color_style_manager = _ColorStyleManager()
