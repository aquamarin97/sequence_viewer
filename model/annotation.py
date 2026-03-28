# model/annotation.py
"""
Tek bir annotasyonun domain modeli.

AnnotationType genişletme rehberi
----------------------------------
Yeni bir tip eklemek için:
1. AnnotationType enum'una değer ekle.
2. display_name() sözlüğüne ekle.
3. default_color() sözlüğüne ekle.
4. is_above_sequence() metodunu güncelle.
5. annotation_painter.py içinde draw_* fonksiyonunu ekle/güncelle.
6. annotation_graphics_item.py ve annotation_layer_widget.py
   paint() metodlarını güncelle.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional

from PyQt5.QtGui import QColor


class AnnotationType(Enum):
    PRIMER          = auto()   # Forward veya reverse primer; yön strand ile belirlenir
    PROBE           = auto()   # Hibridizasyon probu; yön strand ile belirlenir
    REPEATED_REGION = auto()   # Tekrarlayan bölge (alt şeritte gösterilir)

    def display_name(self) -> str:
        return {
            AnnotationType.PRIMER:          "Primer",
            AnnotationType.PROBE:           "Probe",
            AnnotationType.REPEATED_REGION: "Repeated Region",
        }[self]

    def default_color(self) -> QColor:
        return {
            AnnotationType.PRIMER:          QColor( 52, 152, 219),  # mavi
            AnnotationType.PROBE:           QColor( 39, 174,  96),  # yeşil
            AnnotationType.REPEATED_REGION: QColor(243, 156,  18),  # turuncu
        }[self]

    def is_above_sequence(self) -> bool:
        """
        True  → annotation dizinin ÜSTÜNDE render edilir (primer, probe).
        False → annotation dizinin ALTINDA render edilir (repeated region, vb.).

        Yeni bir tip eklendiğinde bu metod güncellenmeli.
        """
        return self in (
            AnnotationType.PRIMER,
            AnnotationType.PROBE,
        )

    def uses_strand(self) -> bool:
        """True ise annotation yön (strand) bilgisi taşır ve ok şekli kullanır."""
        return self in (
            AnnotationType.PRIMER,
            AnnotationType.PROBE,
        )


@dataclass
class Annotation:
    """
    Tek bir annotasyonun tam veri modeli.

    strand : "+" → forward (sağa ok), "-" → reverse (sola ok).
             uses_strand() False ise strand yoksayılır.
    """

    type:        AnnotationType
    start:       int
    end:         int
    label:       str              = ""
    strand:      str              = "+"
    color:       Optional[QColor] = None
    score:       Optional[float]  = None
    tm:          Optional[float]  = None
    gc_percent:  Optional[float]  = None
    notes:       str              = ""
    id:          str              = field(default_factory=lambda: str(uuid.uuid4()))

    def __post_init__(self) -> None:
        if self.start > self.end:
            self.start, self.end = self.end, self.start

    def resolved_color(self) -> QColor:
        return self.color if self.color is not None else self.type.default_color()

    def length(self) -> int:
        return self.end - self.start + 1

    def overlaps(self, other: "Annotation") -> bool:
        return self.start <= other.end and self.end >= other.start

    def tooltip_text(self) -> str:
        lines = [
            f"<b>{self.label or '(isimsiz)'}</b>",
            f"Tip: {self.type.display_name()}",
            f"Pozisyon: {self.start + 1}–{self.end + 1} ({self.length()} bp)",
        ]
        if self.type.uses_strand():
            direction = "Forward (+)" if self.strand == "+" else "Reverse (−)"
            lines.append(f"Yön: {direction}")
        if self.tm is not None:
            lines.append(f"Tm: {self.tm:.1f} °C")
        if self.gc_percent is not None:
            lines.append(f"GC: {self.gc_percent:.1f}%")
        if self.score is not None:
            lines.append(f"Score: {self.score:.3g}")
        if self.notes:
            lines.append(f"Notlar: {self.notes}")
        return "<br>".join(lines)