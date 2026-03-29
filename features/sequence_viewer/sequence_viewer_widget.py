# features/sequence_viewer/sequence_viewer_widget.py

from typing import Optional, Tuple, List

from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtWidgets import QApplication

from .sequence_viewer_model import SequenceViewerModel
from .sequence_viewer_view import SequenceViewerView
from .sequence_viewer_controller import SequenceViewerController


class SequenceViewerWidget(SequenceViewerView):
    """
    Dışarıdan bakıldığında tek bir widget gibi görünen,
    içeride CMV ile organize edilmiş sekans viewer.
    """

    selectionChanged = pyqtSignal()

    def __init__(
        self,
        parent=None,
        *,
        char_width: float = 12.0,
        char_height: float = 18.0,
    ) -> None:
        super().__init__(
            parent=parent,
            char_width=char_width,
            char_height=char_height,
        )

        self._model = SequenceViewerModel()
        self._controller = SequenceViewerController(
            model=self._model,
            view=self,
            on_selection_changed=self.selectionChanged.emit,
        )
        self.set_controller(self._controller)

        # AlignmentDataModel — workspace tarafından set_alignment_model() ile bağlanır.
        # Kopyalama işlemi için alignment_model referansı (ileride kullanım için).
        self._alignment_model = None

    def set_alignment_model(self, alignment_model) -> None:
        """Workspace __init__ sonrasında çağrılır."""
        self._alignment_model = alignment_model

    # ------------------------------------------------------------------
    # Seçim proxy — ruler vb. için
    # ------------------------------------------------------------------

    @property
    def current_selection_cols(self) -> Optional[Tuple[int, int]]:
        return self._model.get_selection_column_range()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def add_sequence(self, sequence_string: str) -> None:
        self._controller.add_sequence(sequence_string)

    def clear(self) -> None:
        self._controller.clear()

    def zoom_to_nt_range(self, start_nt: float, end_nt: float) -> None:
        super().zoom_to_nt_range(start_nt, end_nt)

    def get_selection_column_range(self) -> Optional[Tuple[int, int]]:
        return self._model.get_selection_column_range()

    def get_sequences(self) -> List[str]:
        return self._model.get_sequences()

    # ------------------------------------------------------------------
    # Ctrl+C — seçili kolonları kopyala
    # ------------------------------------------------------------------

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key_C and event.modifiers() & Qt.ControlModifier:
            self._copy_selection_to_clipboard()
            event.accept()
            return
        super().keyPressEvent(event)

    def _copy_selection_to_clipboard(self) -> None:
        """Sadece seçimi olan satırların seçili kolonlarını kopyalar.

        Seçim olmayan satırlar atlanır. Her satır ayrı satır.
        Header yok, sadece nükleotid string.
        """
        lines: List[str] = []
        for item in self.sequence_items:
            if item.selection_range is not None:
                start, end = item.selection_range
                fragment = item.sequence[start:end]
                if fragment:
                    lines.append(fragment)

        if lines:
            QApplication.clipboard().setText("\n".join(lines))