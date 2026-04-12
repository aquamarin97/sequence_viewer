# model/annotation.py
from __future__ import annotations
import uuid
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional
from PyQt5.QtGui import QColor

class AnnotationType(Enum):
    PRIMER          = auto()
    PROBE           = auto()
    REPEATED_REGION = auto()
    MISMATCH_MARKER = auto()

    def display_name(self) -> str:
        return {
            AnnotationType.PRIMER:          "Primer",
            AnnotationType.PROBE:           "Probe",
            AnnotationType.REPEATED_REGION: "Repeated Region",
            AnnotationType.MISMATCH_MARKER: "Mismatch Marker",
        }[self]

    def default_color(self) -> QColor:
        from sequence_viewer.settings.color_styles import color_style_manager
        return color_style_manager.annotation_color(self)

    def is_above_sequence(self) -> bool:
        return self in (AnnotationType.PRIMER, AnnotationType.PROBE,)

    def uses_strand(self) -> bool:
        return self in (AnnotationType.PRIMER, AnnotationType.PROBE,)

    def participates_in_lane_assignment(self) -> bool:
        return self != AnnotationType.MISMATCH_MARKER

@dataclass
class Annotation:
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
    parent_id:   Optional[str]    = None
    mismatch_base: Optional[str]  = None
    expected_base: Optional[str]  = None
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
        if self.type == AnnotationType.MISMATCH_MARKER:
            base = self.mismatch_base or self.label or "?"
            lines = [
                f"<b>{base}</b>",
                f"Tip: {self.type.display_name()}",
                f"Pozisyon: {self.start + 1}",
            ]
            if self.notes:
                lines.append(f"Notlar: {self.notes}")
            return "<br>".join(lines)
        lines = [
            f"<b>{self.label or '(isimsiz)'}</b>",
            f"Tip: {self.type.display_name()}",
            f"Pozisyon: {self.start + 1}â€“{self.end + 1} ({self.length()} bp)",
        ]
        if self.type.uses_strand():
            direction = "Forward (+)" if self.strand == "+" else "Reverse (âˆ’)"
            lines.append(f"YÃ¶n: {direction}")
        if self.tm is not None:
            lines.append(f"Tm: {self.tm:.1f} Â°C")
        if self.gc_percent is not None:
            lines.append(f"GC: {self.gc_percent:.1f}%")
        if self.score is not None:
            lines.append(f"Score: {self.score:.3g}")
        if self.notes:
            lines.append(f"Notlar: {self.notes}")
        return "<br>".join(lines)


