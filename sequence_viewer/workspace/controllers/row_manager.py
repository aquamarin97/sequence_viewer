# sequence_viewer/workspace/controllers/row_manager.py
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sequence_viewer.model.alignment_data_model import AlignmentDataModel


class WorkspaceRowManager:
    """Owns row-level model mutations."""

    def __init__(self, model: "AlignmentDataModel") -> None:
        self._model = model

    def add_sequence(self, header, sequence) -> None:
        self._model.append_row(header, sequence)

    def clear(self) -> None:
        self._model.clear()

    def move_row(self, from_index, to_index) -> None:
        self._model.move_row(from_index, to_index)

    def set_header(self, index, new_header) -> None:
        self._model.set_header(index, new_header)
