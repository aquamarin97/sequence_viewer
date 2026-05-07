from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sequence_viewer.model.annotation import Annotation


class WorkspaceSelectionState:
    """Annotation ve row secim durumunu tutar."""

    def __init__(self) -> None:
        self.selected_annotations: list[tuple[Annotation, int | None]] = []
        self.last_clicked_row: int = 0
