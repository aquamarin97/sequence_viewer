# features/header_viewer/header_viewer_widget.py

from __future__ import annotations

from typing import FrozenSet, List

from PyQt5.QtCore import pyqtSignal

from .header_viewer_model import HeaderViewerModel
from .header_viewer_view import HeaderViewerView


class HeaderViewerWidget(HeaderViewerView):
    """
    Dışarıya görünen header viewer widget'ı.

    Sinyaller
    ---------
    headerEdited(row_index, new_text)
        Kullanıcı double-click ile düzenleyip Enter'a bastı.

    rowMoveRequested(from_index, to_index)
        Kullanıcı drag & drop ile sıraladı.

    selectionChanged(selected_rows: frozenset)
        Seçim değişti. Workspace / diğer bileşenler bunu dinleyebilir.

    rowsDeleteRequested(rows: frozenset)
        Kullanıcı Delete/Backspace'e bastı.
        Workspace modelden satırları siler.
    """

    headerEdited       = pyqtSignal(int, str)     # row_index, new_text
    rowMoveRequested   = pyqtSignal(int, int)     # from_index, to_index
    selectionChanged   = pyqtSignal(object)       # frozenset[int]
    rowsDeleteRequested = pyqtSignal(object)      # frozenset[int]

    def __init__(
        self,
        parent=None,
        *,
        row_height: float = 18.0,
        initial_width: float = 160.0,
    ) -> None:
        super().__init__(
            parent=parent,
            row_height=row_height,
            initial_width=initial_width,
        )
        self._model = HeaderViewerModel()

    # ------------------------------------------------------------------
    # Hook override'ları → sinyal olarak yayınla
    # ------------------------------------------------------------------

    def _on_edit_committed(self, row_index: int, new_text: str) -> None:
        self.headerEdited.emit(row_index, new_text)

    def _on_row_move_requested(self, from_index: int, to_index: int) -> None:
        self.rowMoveRequested.emit(from_index, to_index)

    def _on_selection_changed(self, selected_rows: FrozenSet[int]) -> None:
        self.selectionChanged.emit(selected_rows)

    def _on_rows_delete_requested(self, rows: FrozenSet[int]) -> None:
        self.rowsDeleteRequested.emit(rows)

    # ------------------------------------------------------------------
    # Public API (eski kodla uyumlu)
    # ------------------------------------------------------------------

    def add_header(self, text: str) -> None:
        row_index    = self._model.add_header(text)
        display_text = f"{row_index + 1}. {text}"
        self.add_header_item(display_text)

    def clear(self) -> None:
        self._model.clear_headers()
        self.clear_items()

    def get_headers(self) -> List[str]:
        return self._model.get_headers()

    def get_row_count(self) -> int:
        return self._model.get_row_count()

    # ------------------------------------------------------------------
    # Seçim sıfırlama (workspace'den çağrılır — rebuild sonrası)
    # ------------------------------------------------------------------

    def clear_selection(self) -> None:
        """_rebuild_views sonrası seçimi ve item görselini sıfırlar."""
        changed = self._selection.clear()
        self.apply_selection_to_items(changed)