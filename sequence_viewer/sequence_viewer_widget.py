# msa_viewer/sequence_viewer/sequence_viewer_widget.py

from typing import Optional, Tuple, List

from PyQt5.QtCore import pyqtSignal

from .sequence_viewer_model import SequenceViewerModel
from .sequence_viewer_view import SequenceViewerView
from .sequence_viewer_controller import SequenceViewerController


class SequenceViewerWidget(SequenceViewerView):
    """
    Dışarıdan bakıldığında tek bir widget gibi görünen,
    içeride CMV (Model - View - Controller) ile organize edilmiş sekans viewer.
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

    # --- 🔴 ESKİ API İÇİN GERİYE DÖNÜK UYUMLULUK -----------------------

    @property
    def current_selection_cols(self) -> Optional[Tuple[int, int]]:
        """
        Eski SequenceViewerWidget API'si ile uyumluluk için:
        position_ruler vb. yerler viewer.current_selection_cols okuyordu.
        Artık state model'de, buradan proxy'liyoruz.
        """
        return self._model.get_selection_column_range()
    # ------------------------------------------------------------------
    # Public API: Eski SequenceViewerWidget ile uyumlu yöntemler
    # ------------------------------------------------------------------

    def add_sequence(self, sequence_string: str) -> None:
        """
        Yeni bir sekans ekler.
        """
        self._controller.add_sequence(sequence_string)

    def clear(self) -> None:
        """
        Tüm sekansları ve seçimleri temizler.
        """
        self._controller.clear()

    def zoom_to_nt_range(self, start_nt: float, end_nt: float) -> None:
        """
        Cetvelden gelen 'bu nt aralığına zoom yap' isteği.

        Geometri tamamen view tarafında, model değişmediği için
        doğrudan base class metodunu kullanıyoruz.
        """
        super().zoom_to_nt_range(start_nt, end_nt)

    # ------------------------------------------------------------------
    # Public API: Seçim bilgisi okuma (ruler vb. için)
    # ------------------------------------------------------------------

    def get_selection_column_range(self) -> Optional[Tuple[int, int]]:
        """
        Mevcut seçim sütun aralığını döner (start, end) inclusive.
        Seçim yoksa None.
        """
        return self._model.get_selection_column_range()

    def get_sequences(self) -> List[str]:
        """
        Model'deki sekansların kopyasını döner.
        """
        return self._model.get_sequences()
