# settings/annotation_styles.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict
from PyQt5.QtCore import QObject, pyqtSignal
from sequence_viewer.model.annotation import AnnotationType

@dataclass(frozen=True)
class AnnotationTypeStyle:
    fill_alpha: int
    border_alpha: int
    border_width: float
    label_min_width: int
    label_font_size: int = 11
    label_font_family: str = "Arial"

_STYLES_LIGHT = {
    AnnotationType.PRIMER:          AnnotationTypeStyle(255, 0,   0.0, 20, 11, "Arial"),
    AnnotationType.PROBE:           AnnotationTypeStyle(165, 220, 1.5, 20, 11, "Arial"),
    AnnotationType.REPEATED_REGION: AnnotationTypeStyle(55,  170, 1.0, 24, 11, "Arial"),
    AnnotationType.MISMATCH_MARKER: AnnotationTypeStyle(255, 255, 1.2, 1, 11, "Arial"),
}
_STYLES_DARK = {
    AnnotationType.PRIMER:          AnnotationTypeStyle(210, 0,   0.0, 20, 11, "Arial"),
    AnnotationType.PROBE:           AnnotationTypeStyle(150, 190, 1.5, 20, 11, "Arial"),
    AnnotationType.REPEATED_REGION: AnnotationTypeStyle(75,  160, 1.0, 24, 11, "Arial"),
    AnnotationType.MISMATCH_MARKER: AnnotationTypeStyle(255, 255, 1.2, 1, 11, "Arial"),
}

class _AnnotationStyleManager(QObject):
    stylesChanged = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._styles = dict(_STYLES_LIGHT)

    def get(self, ann_type):
        return self._styles.get(ann_type, _STYLES_LIGHT[AnnotationType.PRIMER])

    def apply_theme(self, theme_name):
        import dataclasses
        base = _STYLES_DARK if theme_name == "dark" else _STYLES_LIGHT
        changed = False
        for ann_type, base_style in base.items():
            current = self._styles.get(ann_type)
            if current is None:
                self._styles[ann_type] = base_style
                changed = True
                continue
            # YalnÄ±zca tema-Ã¶zgÃ¼ alanlarÄ± gÃ¼ncelle; kullanÄ±cÄ± ayarlarÄ±nÄ± koru.
            merged = dataclasses.replace(
                current,
                fill_alpha=base_style.fill_alpha,
                border_alpha=base_style.border_alpha,
                border_width=base_style.border_width,
            )
            if merged != current:
                self._styles[ann_type] = merged
                changed = True
        if changed:
            self.stylesChanged.emit()

    def set_style(self, ann_type, style):
        if self._styles.get(ann_type) != style:
            self._styles[ann_type] = style
            self.stylesChanged.emit()

    def set_label_font_size(self, ann_type, size):
        """label_font_size'Ä± 6pt minimumla gÃ¼nceller; Ã¼st sÄ±nÄ±r yoktur."""
        clamped = max(6, int(round(size)))
        current = self._styles.get(ann_type)
        if current is None or current.label_font_size == clamped:
            return
        import dataclasses
        self._styles[ann_type] = dataclasses.replace(current, label_font_size=clamped)
        self.stylesChanged.emit()

    def set_label_font_family(self, ann_type, family):
        """label_font_family'yi gÃ¼nceller."""
        current = self._styles.get(ann_type)
        if current is None or current.label_font_family == family:
            return
        import dataclasses
        self._styles[ann_type] = dataclasses.replace(current, label_font_family=family)
        self.stylesChanged.emit()

    def get_lane_height(self) -> int:
        """
        TÃ¼m annotation tiplerindeki gerÃ§ek font metriklerine gÃ¶re lane
        yÃ¼ksekliÄŸini hesaplar.

        QFontMetrics.height() = ascent + descent kullanÄ±lÄ±r; bu deÄŸer
        "p", "g", "y", "q" gibi descender'lÄ± karakterleri tam kapsar.
        Font-agnostic: farklÄ± font family'lerde de doÄŸru Ã§alÄ±ÅŸÄ±r.
        """
        from PyQt5.QtGui import QFont, QFontMetrics
        _V_PAD = 4  # Ã¼st + alt boÅŸluk toplamÄ± (px)
        max_h = 0
        for s in self._styles.values():
            font = QFont(s.label_font_family, s.label_font_size)
            font.setBold(True)
            fm = QFontMetrics(font)
            # height() descender'larÄ± da iÃ§erir
            actual_h = fm.height() + _V_PAD
            max_h = max(max_h, actual_h)
        return max(16, max_h) if max_h > 0 else 16

    def reset(self, theme_name="light"):
        self.apply_theme(theme_name)

annotation_style_manager = _AnnotationStyleManager()


