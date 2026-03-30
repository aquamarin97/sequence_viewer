from typing import Optional, Tuple, List
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtWidgets import QApplication
from .sequence_viewer_model import SequenceViewerModel
from .sequence_viewer_view import SequenceViewerView
from .sequence_viewer_controller import SequenceViewerController

class SequenceViewerWidget(SequenceViewerView):
    selectionChanged = pyqtSignal()
    def __init__(self, parent=None, *, char_width=12.0, char_height=18.0):
        super().__init__(parent=parent, char_width=char_width, char_height=char_height)
        self._model = SequenceViewerModel()
        self._controller = SequenceViewerController(model=self._model, view=self, on_selection_changed=self.selectionChanged.emit)
        self.set_controller(self._controller)
        self._alignment_model = None

    def set_alignment_model(self, alignment_model): self._alignment_model = alignment_model

    @property
    def current_selection_cols(self): return self._model.get_selection_column_range()

    def add_sequence(self, sequence_string): self._controller.add_sequence(sequence_string)
    def clear(self): self._controller.clear()
    def zoom_to_nt_range(self, start_nt, end_nt): super().zoom_to_nt_range(start_nt, end_nt)
    def get_selection_column_range(self): return self._model.get_selection_column_range()
    def get_sequences(self): return self._model.get_sequences()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_C and event.modifiers() & Qt.ControlModifier:
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
