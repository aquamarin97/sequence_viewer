# settings/annotation_styles.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict
from PyQt5.QtCore import QObject, pyqtSignal
from model.annotation import AnnotationType

@dataclass(frozen=True)
class AnnotationTypeStyle:
    fill_alpha: int
    border_alpha: int
    border_width: float
    label_min_width: int
    label_font_size: int = 7

_STYLES_LIGHT = {
    AnnotationType.PRIMER: AnnotationTypeStyle(255,0,0.0,20,7),
    AnnotationType.PROBE: AnnotationTypeStyle(165,220,1.5,20,7),
    AnnotationType.REPEATED_REGION: AnnotationTypeStyle(55,170,1.0,24,7),
}
_STYLES_DARK = {
    AnnotationType.PRIMER: AnnotationTypeStyle(210,0,0.0,20,7),
    AnnotationType.PROBE: AnnotationTypeStyle(150,190,1.5,20,7),
    AnnotationType.REPEATED_REGION: AnnotationTypeStyle(75,160,1.0,24,7),
}

class _AnnotationStyleManager(QObject):
    stylesChanged = pyqtSignal()
    def __init__(self):
        super().__init__()
        self._styles = dict(_STYLES_LIGHT)
    def get(self, ann_type):
        return self._styles.get(ann_type, _STYLES_LIGHT[AnnotationType.PRIMER])
    def apply_theme(self, theme_name):
        new_styles = dict(_STYLES_DARK) if theme_name == "dark" else dict(_STYLES_LIGHT)
        if new_styles != self._styles:
            self._styles = new_styles
            self.stylesChanged.emit()
    def set_style(self, ann_type, style):
        if self._styles.get(ann_type) != style:
            self._styles[ann_type] = style
            self.stylesChanged.emit()
    def reset(self, theme_name="light"):
        self.apply_theme(theme_name)

annotation_style_manager = _AnnotationStyleManager()
