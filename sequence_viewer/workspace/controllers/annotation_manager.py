# sequence_viewer/workspace/controllers/annotation_manager.py
from __future__ import annotations


class WorkspaceAnnotationManager:
    """Owns annotation-level model mutations."""

    def __init__(self, model):
        self._model = model

    def add_annotation(self, row_index, annotation) -> None:
        self._model.add_annotation(row_index, annotation)

    def remove_annotation(self, row_index, annotation_id) -> None:
        self._model.remove_annotation(row_index, annotation_id)

    def clear_annotations(self) -> None:
        for row_index in range(self._model.row_count()):
            try:
                self._model.clear_annotations(row_index)
            except Exception:
                pass

