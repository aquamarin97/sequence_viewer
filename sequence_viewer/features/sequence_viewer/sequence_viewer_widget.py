# sequence_viewer/features/sequence_viewer/sequence_viewer_widget.py
# features/sequence_viewer/sequence_viewer_widget.py
from typing import Optional, Tuple, List
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtWidgets import QApplication
from .sequence_viewer_model import SequenceViewerModel
from .sequence_viewer_view import SequenceViewerView
from .sequence_viewer_controller import SequenceViewerController

class SequenceViewerWidget(SequenceViewerView):
    selectionChanged = pyqtSignal()
    rowClicked = pyqtSignal(int, int)  # (row_start, row_end)

    def __init__(self, parent=None, *, char_width=12.0, char_height=18.0):
        super().__init__(parent=parent, char_width=char_width, char_height=char_height)
        self._model = SequenceViewerModel()
        self._controller = SequenceViewerController(
            model=self._model, view=self,
            on_selection_changed=self.selectionChanged.emit,
            on_row_clicked=self.rowClicked.emit,
        )
        self.set_controller(self._controller)
        self._alignment_model = None

        # Scroll → paneli gizle (hover ile tekrar açılabilir)
        self.horizontalScrollBar().valueChanged.connect(self._on_scroll)
        self.verticalScrollBar().valueChanged.connect(self._on_scroll)

    def _on_scroll(self) -> None:
        """Scroll sırasında seçim yokmuş gibi değil; sadece paneli gizle."""
        if self._controller and not self._controller._is_selecting:
            self._controller._drag_tooltip.clear_panel()

    def set_alignment_model(self, alignment_model):
        self._alignment_model = alignment_model

    @property
    def current_selection_cols(self):
        return self._model.get_selection_column_range()

    def add_sequence(self, sequence_string):
        self._controller.add_sequence(sequence_string)

    def clear(self):
        self._controller.clear()

    def zoom_to_nt_range(self, start_nt, end_nt):
        super().zoom_to_nt_range(start_nt, end_nt)

    def get_selection_column_range(self):
        return self._model.get_selection_column_range()

    def get_sequences(self):
        return self._model.get_sequences()

    def show_info_panel(self, row_start: int, row_end: int,
                        col_start: int, col_end: int) -> None:
        """Annotation click gibi dış olaylardan bp/Tm panelini gösterir."""
        self._controller.show_info_panel(row_start, row_end, col_start, col_end)

    def keyPressEvent(self, event):
        ctrl = bool(event.modifiers() & Qt.ControlModifier)
        shift = bool(event.modifiers() & Qt.ShiftModifier)
        if event.key() == Qt.Key_C and ctrl and shift:
            parent = self.parent()
            while parent is not None:
                if hasattr(parent, "_copy_fasta"):
                    parent._copy_fasta()
                    event.accept()
                    return
                parent = parent.parent()
        if event.key() == Qt.Key_C and ctrl and not shift:
            self._copy_selection_to_clipboard(); event.accept(); return
        super().keyPressEvent(event)

    def _copy_selection_to_clipboard(self):
        lines = []
        for item in self.sequence_items:
            if item.selection_range is not None:
                start, end = item.selection_range
                fragment = item.sequence[start:end]
                if fragment: lines.append(fragment)
        if lines: QApplication.clipboard().setText("\n".join(lines))
