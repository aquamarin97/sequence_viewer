# model/annotation.py

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Optional

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


@dataclass
class Annotation:
    """
    Tek bir annotasyonun tam veri modeli.

    seq_indices
    -----------
    None      → annotasyon tüm satırlara uygulanır (alignment annotasyonu).
    [0, 2, 5] → sadece belirtilen satır indekslerinde görünür.
                 Find Motifs gibi per-sequence eşleşmelerde kullanılır.
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

    # Hangi satır indekslerinde görüneceğini belirler.
    # None → tüm satırlar (global alignment annotation)
    seq_indices: Optional[List[int]] = None

    def __post_init__(self) -> None:
        if self.start > self.end:
            self.start, self.end = self.end, self.start

    def resolved_color(self) -> QColor:
        return self.color if self.color is not None else self.type.default_color()

    def length(self) -> int:
        return self.end - self.start + 1

    def applies_to_row(self, row_index: int) -> bool:
        """Bu annotasyon verilen satırda gösterilmeli mi?"""
        if self.seq_indices is None:
            return True
        return row_index in self.seq_indices

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