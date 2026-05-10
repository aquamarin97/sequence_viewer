from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass(frozen=True)
class SequenceRowInput:
    """Host-provided row payload for facade loading methods."""

    header: str
    sequence: object


@dataclass(frozen=True)
class SelectedAnnotationRef:
    """Stable annotation selection reference exposed to host applications."""

    annotation_id: str
    scope: str
    row_index: Optional[int] = None


@dataclass(frozen=True)
class SelectionSnapshot:
    """Read-only selection summary for the workspace public API."""

    selected_rows: Tuple[int, ...] = ()
    sequence_range: Optional[Tuple[int, int, int, int]] = None
    selected_annotations: Tuple[SelectedAnnotationRef, ...] = ()
    consensus_selected: bool = False
    consensus_range: Optional[Tuple[int, int]] = None
    consensus_annotation_ids: Tuple[str, ...] = ()
