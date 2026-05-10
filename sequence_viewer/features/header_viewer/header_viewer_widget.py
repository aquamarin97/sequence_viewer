# sequence_viewer/features/header_viewer/header_viewer_widget.py
from __future__ import annotations

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtGui import QFont, QFontMetrics

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
        self._max_header_text_px = 0
        self._required_width_cache = 100

    # ── Pool data provider ─────────────────────────────────────────────────

    def _get_header_text_for_row(self, row_idx: int) -> str:
        return f"{row_idx + 1}. {self._model.get_header(row_idx)}"

    # ── Signal forwarding ──────────────────────────────────────────────────

    def _on_edit_committed(self, row_index, new_text): self.headerEdited.emit(row_index, new_text)
    def _on_row_move_requested(self, from_index, to_index): self.rowMoveRequested.emit(from_index, to_index)
    def _on_selection_changed(self, selected_rows): self.selectionChanged.emit(selected_rows)
    def _on_rows_delete_requested(self, rows): self.rowsDeleteRequested.emit(rows)

    # ── Public API ─────────────────────────────────────────────────────────

    def add_header(self, text: str) -> None:
        row_index = self._model.add_header(text)
        display_text = f"{row_index + 1}. {text}"
        self._include_header_width(display_text)
        self.add_header_item(display_text)

    def set_headers(self, headers) -> None:
        self._model.set_headers(headers)
        self._total_header_count = self._model.get_row_count()
        self._selection.clear()
        self._editor.cancel_edit()
        self._drag.reset()
        self._full_header_pool_remount()
        self._rebuild_width_cache()
        self._update_scene_rect()

    def clear(self):
        self._model.clear_headers()
        self._max_header_text_px = 0
        self._required_width_cache = 100
        self.clear_items()

    def get_headers(self): return self._model.get_headers()
    def get_row_count(self): return self._model.get_row_count()

    def selected_rows(self):
        return self.selection.selected_rows()

    def deselect_row(self, row: int) -> None:
        self.selection.remove_row(row)

    def clear_interaction_state(self) -> None:
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
        if index < 0 or index >= self._total_header_count:
            raise IndexError(f"Header index {index} out of range")
        self._model.remove_header(index)
        self._invalidate_width_cache()
        self.selection.remove_row(index)
        self._total_header_count -= 1
        self._full_header_pool_remount()
        self._update_scene_rect()

    def move_header_item(self, from_index: int, to_index: int) -> None:
        if not (0 <= from_index < self._total_header_count and
                0 <= to_index < self._total_header_count):
            raise IndexError("move_header_item out of range")
        if from_index == to_index:
            return
        self._model.move_header(from_index, to_index)
        self._invalidate_width_cache()
        self.move_row_selection(from_index, to_index)
        self._full_header_pool_remount()
        self._update_scene_rect()

    def renumber_from(self, index: int) -> None:
        # Pool items in range get updated text on next mount/remount.
        # Touch visible items now so renumbering is immediate.
        start = max(0, index)
        for item in self.header_items:
            if item.isVisible() and item.row_index >= start:
                item.set_full_text(self._get_header_text_for_row(item.row_index))

    def set_header_item_text(self, index: int, display_text: str) -> None:
        self._model.set_header(index, self._strip_row_number(display_text))
        self._invalidate_width_cache()
        item = self._find_pool_item(index)
        if item is not None:
            item.set_full_text(display_text)

    def compute_required_width(self) -> int:
        if self._required_width_cache is not None:
            return self._required_width_cache
        return self._rebuild_width_cache()

    def _on_display_settings_changed(self):
        super()._on_display_settings_changed()
        self._invalidate_width_cache()

    def _font_metrics(self) -> QFontMetrics:
        font = self.header_items[0].font if self.header_items else QFont("Arial")
        return QFontMetrics(font)

    def _include_header_width(self, display_text: str) -> None:
        if self._required_width_cache is None:
            self._rebuild_width_cache()
        metrics = self._font_metrics()
        self._max_header_text_px = max(
            self._max_header_text_px,
            metrics.horizontalAdvance(display_text),
        )
        self._required_width_cache = max(100, self._max_header_text_px + 14)

    def _invalidate_width_cache(self) -> None:
        self._required_width_cache = None

    def _rebuild_width_cache(self) -> int:
        headers = self._model.get_headers()
        if not headers:
            self._max_header_text_px = 0
            self._required_width_cache = 100
            return self._required_width_cache
        metrics = self._font_metrics()
        self._max_header_text_px = max(
            metrics.horizontalAdvance(f"{i + 1}. {h}")
            for i, h in enumerate(headers)
        )
        self._required_width_cache = max(100, self._max_header_text_px + 14)
        return self._required_width_cache
