from __future__ import annotations


class WorkspaceSelectionState:
    """Annotation ve row secim durumunu tutar."""

    def __init__(self) -> None:
        self.selected_annotations: list = []
        self.last_clicked_row: int = 0
