# sequence_viewer/features/header_viewer/header_viewer_widget.py
# features/header_viewer/header_viewer_widget.py
from __future__ import annotations
from typing import FrozenSet, List
from PyQt5.QtCore import pyqtSignal
from .header_viewer_model import HeaderViewerModel
from .header_viewer_view import HeaderViewerView

class HeaderViewerWidget(HeaderViewerView):
    headerEdited = pyqtSignal(int, str)
    rowMoveRequested = pyqtSignal(int, int)
    selectionChanged = pyqtSignal(object)
    rowsDeleteRequested = pyqtSignal(object)

    def __init__(self, parent=None, *, row_height=18.0, initial_width=160.0):
        super().__init__(parent=parent, row_height=row_height, initial_width=initial_width)
        self._model = HeaderViewerModel()

    def _on_edit_committed(self, row_index, new_text): self.headerEdited.emit(row_index, new_text)
    def _on_row_move_requested(self, from_index, to_index): self.rowMoveRequested.emit(from_index, to_index)
    def _on_selection_changed(self, selected_rows): self.selectionChanged.emit(selected_rows)
    def _on_rows_delete_requested(self, rows): self.rowsDeleteRequested.emit(rows)

    def add_header(self, text):
        row_index = self._model.add_header(text)
        display_text = f"{row_index + 1}. {text}"
        self.add_header_item(display_text)

    def clear(self): self._model.clear_headers(); self.clear_items()
    def get_headers(self): return self._model.get_headers()
    def get_row_count(self): return self._model.get_row_count()

    def clear_selection(self):
        changed = self._selection.clear()
        self.apply_selection_to_items(changed)


