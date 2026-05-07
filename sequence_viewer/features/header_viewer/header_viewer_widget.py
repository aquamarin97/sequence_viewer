# sequence_viewer/features/header_viewer/header_viewer_widget.py
# features/header_viewer/header_viewer_widget.py
from __future__ import annotations
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

    def selected_rows(self):
        return self.selection.selected_rows()

    def deselect_row(self, row: int) -> None:
        self.selection.remove_row(row)

    def clear_interaction_state(self) -> None:
        """Satır seçim state'ini temizler ve görsel güncellemesini yapar."""
        changed = self.selection.clear()
        self.apply_selection_to_items(changed)

    def clear_selection(self) -> frozenset:
        changed = self.selection.clear()
        self.apply_selection_to_items(changed)
        return changed

    def select_row(self, row: int, n: int) -> frozenset:
        return self.selection.handle_click(row, n)

    def toggle_row(self, row: int, n: int) -> frozenset:
        return self.selection.handle_ctrl_click(row, n)

    def range_select(self, lo: int, hi: int, n: int) -> frozenset:
        changed = frozenset()
        if n <= 0:
            return changed
        lo = max(0, lo)
        hi = min(n - 1, hi)
        if lo > hi:
            return changed
        for row in range(lo, hi + 1):
            if not self.selection.is_selected(row):
                changed = changed | self.selection.handle_ctrl_click(row, n)
        return changed

    def is_row_selected(self, row: int) -> bool:
        return self.selection.is_selected(row)

    def move_row_selection(self, from_index: int, to_index: int) -> None:
        self.selection.move_row(from_index, to_index)

    @staticmethod
    def _strip_row_number(display_text: str) -> str:
        _prefix, sep, rest = display_text.partition(". ")
        return rest if sep else display_text

    def remove_header_item(self, index: int) -> None:
        if index < 0 or index >= len(self.header_items):
            raise IndexError(f"Header index {index} out of range")
        item = self.header_items.pop(index)
        if item.scene() is not None:
            self.scene.removeItem(item)
        self.selection.remove_row(index)
        self._update_scene_rect()

    def move_header_item(self, from_index: int, to_index: int) -> None:
        n = len(self.header_items)
        if not (0 <= from_index < n and 0 <= to_index < n):
            raise IndexError("move_header_item out of range")
        if from_index == to_index:
            return
        item = self.header_items.pop(from_index)
        self.header_items.insert(to_index, item)
        self.move_row_selection(from_index, to_index)
        self._update_scene_rect()

    def renumber_from(self, index: int) -> None:
        start = max(0, index)
        for i in range(start, len(self.header_items)):
            item = self.header_items[i]
            header = self._strip_row_number(item.full_text)
            item.set_row_index(i)
            item.set_full_text(f"{i + 1}. {header}")
        self._update_scene_rect()

    def set_header_item_text(self, index: int, display_text: str) -> None:
        if index < 0 or index >= len(self.header_items):
            raise IndexError(f"Header index {index} out of range")
        self.header_items[index].set_full_text(display_text)
