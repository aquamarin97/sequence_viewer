# model/annotation.py
"""
Tek bir annotasyonun domain modeli.

Adım 1 değişikliği
------------------
seq_indices alanı kaldırıldı.  Annotation artık hangi diziye ait olduğunu
kendi içinde tutmaz; bu ilişki SequenceRecord.annotations listesinin
sahipliği ile ifade edilir.  Bir annotation bir SequenceRecord'a
aitse o record'un listesindedir — başka bir referansa gerek yoktur.

global_annotations (AlignmentDataModel düzeyi) için de aynı prensip:
o liste içindeyse globaldir, başka bir alan gerekmez.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional

from PyQt5.QtGui import QColor


class AnnotationType(Enum):
    FORWARD_PRIMER = auto()
    REVERSE_PRIMER = auto()
    PROBE          = auto()
    REGION         = auto()

    def display_name(self) -> str:
        return {
            AnnotationType.FORWARD_PRIMER: "Forward Primer",
            AnnotationType.REVERSE_PRIMER: "Reverse Primer",
            AnnotationType.PROBE:          "Probe",
            AnnotationType.REGION:         "Region",
        }[self]

    def default_color(self) -> QColor:
        return {
            AnnotationType.FORWARD_PRIMER: QColor( 52, 152, 219),
            AnnotationType.REVERSE_PRIMER: QColor(231,  76,  60),
            AnnotationType.PROBE:          QColor( 39, 174,  96),
            AnnotationType.REGION:         QColor(243, 156,  18),
        }[self]

    def is_above_sequence(self) -> bool:
        """
        True  → annotation dizinin ÜSTÜNDE render edilir  (primer, probe).
        False → annotation dizinin ALTINDA render edilir  (region, gelecek tipler).

        Yeni bir AnnotationType eklendiğinde bu metoda da eklenmeli.
        """
        return self in (
            AnnotationType.FORWARD_PRIMER,
            AnnotationType.REVERSE_PRIMER,
            AnnotationType.PROBE,
        )


@dataclass
class Annotation:
    """
    Tek bir annotasyonun tam veri modeli.

    Sahiplik ilişkisi
    -----------------
    Bu obje hangi diziye ait olduğunu bilmez.  İlişki şu şekilde ifade edilir:
        - Per-sequence annotation → SequenceRecord.annotations listesinde
        - Alignment-level (global) annotation → AlignmentDataModel.global_annotations listesinde
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
            f"Strand: {self.strand}",
        ]
        if self.tm is not None:
            lines.append(f"Tm: {self.tm:.1f} °C")
        if self.gc_percent is not None:
            lines.append(f"GC: {self.gc_percent:.1f}%")
        if self.score is not None:
            lines.append(f"Score: {self.score:.3g}")
        if self.notes:
            lines.append(f"Notlar: {self.notes}")
        return "<br>".join(lines)