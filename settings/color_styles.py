# settings/color_styles.py
from __future__ import annotations
from typing import Dict, Optional
from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtGui import QColor
from model.annotation import AnnotationType

_NUCLEOTIDE_COLORS_LIGHT = {
    "A": QColor(21,128,61), "T": QColor(185,28,28), "U": QColor(185,28,28),
    "C": QColor(29,78,216), "G": QColor(161,98,7),
    "-": QColor(100,116,139), "N": QColor(107,114,128),
}
_NUCLEOTIDE_COLORS_DARK = {
    "A": QColor(74,199,120), "T": QColor(220,90,90), "U": QColor(220,90,90),
    "C": QColor(88,152,235), "G": QColor(218,160,50),
    "-": QColor(140,148,162), "N": QColor(130,140,158),
}
_CONSENSUS_COLORS = {
    "light": {"A":QColor(0,170,80),"T":QColor(220,30,30),"U":QColor(220,30,30),"C":QColor(20,100,255),"G":QColor(255,140,0),"-":QColor(75,85,105),"N":QColor(100,110,130)},
    "dark": {"A":QColor(40,255,110),"T":QColor(255,60,60),"U":QColor(255,70,160),"C":QColor(30,220,255),"G":QColor(255,190,30),"-":QColor(110,120,140),"N":QColor(140,150,170)},
}
_DEFAULT_NUCLEOTIDE_COLORS = _NUCLEOTIDE_COLORS_LIGHT
_DEFAULT_ANNOTATION_COLORS = {
    AnnotationType.PRIMER: QColor(52,152,219),
    AnnotationType.PROBE: QColor(39,174,96),
    AnnotationType.REPEATED_REGION: QColor(243,156,18),
}

class _ColorStyleManager(QObject):
    stylesChanged = pyqtSignal()
    def __init__(self):
        super().__init__()
        self._nucleotide = {k:QColor(v) for k,v in _DEFAULT_NUCLEOTIDE_COLORS.items()}
        self._annotation = {k:QColor(v) for k,v in _DEFAULT_ANNOTATION_COLORS.items()}

    def nucleotide_color(self, base):
        return QColor(self._nucleotide.get(base.upper(), self._nucleotide.get("N", QColor(80,80,80))))

    def nucleotide_color_map(self):
        return {k:QColor(v) for k,v in self._nucleotide.items()}

    def consensus_nucleotide_color_map(self):
        base = {k:QColor(v) for k,v in self._nucleotide.items()}
        try:
            from settings.theme import theme_manager
            overrides = _CONSENSUS_COLORS.get(theme_manager.current.name, {})
        except: overrides = {}
        base.update({k:QColor(v) for k,v in overrides.items()})
        return base

    def apply_theme(self, theme_name):
        palette = _NUCLEOTIDE_COLORS_DARK if theme_name == "dark" else _NUCLEOTIDE_COLORS_LIGHT
        new_nuc = {k:QColor(v) for k,v in palette.items()}
        if new_nuc != self._nucleotide:
            self._nucleotide = new_nuc
            self.stylesChanged.emit()

    def set_nucleotide_color(self, base, color):
        key = base.upper()
        if key not in self._nucleotide or self._nucleotide[key] != color:
            self._nucleotide[key] = QColor(color)
            self.stylesChanged.emit()

    def reset_nucleotide_colors(self):
        try:
            from settings.theme import theme_manager
            palette = _NUCLEOTIDE_COLORS_DARK if theme_manager.current.name == "dark" else _NUCLEOTIDE_COLORS_LIGHT
        except: palette = _NUCLEOTIDE_COLORS_LIGHT
        self._nucleotide = {k:QColor(v) for k,v in palette.items()}
        self.stylesChanged.emit()

    def annotation_color(self, ann_type):
        return QColor(self._annotation.get(ann_type, QColor(128,128,128)))

    def set_annotation_color(self, ann_type, color):
        if self._annotation.get(ann_type) != color:
            self._annotation[ann_type] = QColor(color)
            self.stylesChanged.emit()

    def reset_annotation_colors(self):
        self._annotation = {k:QColor(v) for k,v in _DEFAULT_ANNOTATION_COLORS.items()}
        self.stylesChanged.emit()

    def reset_all(self):
        self._nucleotide = {k:QColor(v) for k,v in _DEFAULT_NUCLEOTIDE_COLORS.items()}
        self._annotation = {k:QColor(v) for k,v in _DEFAULT_ANNOTATION_COLORS.items()}
        self.stylesChanged.emit()

    def to_dict(self):
        return {"nucleotide":{k:v.name() for k,v in self._nucleotide.items()},
                "annotation":{t.name:c.name() for t,c in self._annotation.items()}}

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
        if changed: self.stylesChanged.emit()

color_style_manager = _ColorStyleManager()
