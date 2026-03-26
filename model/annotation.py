# model/annotation.py
"""
Annotasyon veri modeli.

AnnotationType
--------------
FORWARD_PRIMER   ok sağa, dolgu kutu
REVERSE_PRIMER   ok sola, dolgu kutu
PROBE            düz dikdörtgen, farklı renk
REGION           yarı saydam bant (amplikon vb.)

Annotation
----------
Geneious benzeri tam metadata.
id         : UUID string — store içinde benzersiz anahtar
type       : AnnotationType
start      : 0-based, inclusive
end        : 0-based, inclusive
label      : görüntülenen kısa isim
strand     : "+" | "-" | "." (belirsiz)
color      : None → type için varsayılan renk kullanılır
score      : float veya None
tm         : erime sıcaklığı (°C) veya None
gc_percent : GC yüzdesi (0-100) veya None
notes      : serbest metin
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
            AnnotationType.FORWARD_PRIMER: QColor( 52, 152, 219),  # mavi
            AnnotationType.REVERSE_PRIMER: QColor(231,  76,  60),  # kırmızı
            AnnotationType.PROBE:          QColor( 39, 174,  96),  # yeşil
            AnnotationType.REGION:         QColor(243, 156,  18),  # turuncu
        }[self]


@dataclass
class Annotation:
    """Tek bir annotasyonun tam veri modeli."""

    type:        AnnotationType
    start:       int                       # 0-based, inclusive
    end:         int                       # 0-based, inclusive
    label:       str        = ""
    strand:      str        = "+"          # "+" | "-" | "."
    color:       Optional[QColor] = None   # None → type.default_color()
    score:       Optional[float]  = None
    tm:          Optional[float]  = None   # erime sıcaklığı °C
    gc_percent:  Optional[float]  = None   # 0-100
    notes:       str        = ""
    id:          str        = field(default_factory=lambda: str(uuid.uuid4()))

    def __post_init__(self) -> None:
        # start ≤ end garantisi
        if self.start > self.end:
            self.start, self.end = self.end, self.start

    # ------------------------------------------------------------------
    # Yardımcılar
    # ------------------------------------------------------------------

    def resolved_color(self) -> QColor:
        """Renk tanımlanmışsa onu, yoksa tip varsayılanını döner."""
        return self.color if self.color is not None else self.type.default_color()

    def length(self) -> int:
        return self.end - self.start + 1

    def overlaps(self, other: "Annotation") -> bool:
        return self.start <= other.end and self.end >= other.start

    def tooltip_text(self) -> str:
        """Tooltip veya metadata paneli için formatlanmış metin."""
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