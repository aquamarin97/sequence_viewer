# msa_viewer/header_viewer/header_viewer_widget.py

from typing import List

from .header_viewer_model import HeaderViewerModel
from .header_viewer_view import HeaderViewerView


class HeaderViewerWidget(HeaderViewerView):
    """
    Dışarıya görünen header viewer widget'ı.

    İçeride:
    - Model: HeaderViewerModel (ham header metinleri)
    - View : HeaderViewerView (QGraphicsView + HeaderRowItem'lar)

    Eski HeaderViewerWidget API'sini koruyarak:
    - add_header(text)
    - clear()
    - compute_required_width()
    vb. sağlar.
    """

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
    # Public API (eski kodla uyumlu)
    # ------------------------------------------------------------------

    def add_header(self, text: str) -> None:
        """
        Yeni bir header ekler:
        - Model'e ham metni ekler
        - View'da "1. Text", "2. Text" şeklinde numaralı display_text oluşturur
        """
        row_index = self._model.add_header(text)

        # Gösterilecek metin: "1. HeaderText", "2. HeaderText", ...
        display_text = f"{row_index + 1}. {text}"
        self.add_header_item(display_text)

    def clear(self) -> None:
        """
        Tüm header'ları ve item'ları temizler.
        """
        self._model.clear_headers()
        self.clear_items()

    # ------------------------------------------------------------------
    # Model'le ilgili okuma yardımcıları
    # ------------------------------------------------------------------

    def get_headers(self) -> List[str]:
        """
        Model'deki ham header metinlerini döner.
        """
        return self._model.get_headers()

    def get_row_count(self) -> int:
        """
        Header satır sayısı.
        """
        return self._model.get_row_count()
