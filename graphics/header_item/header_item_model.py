# msa_viewer/graphics/header_item_model.py

from dataclasses import dataclass

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFontMetrics


@dataclass
class HeaderRowModel:
    """
    Tek bir header satırının model katmanı.

    - full_text: tam gösterilmek istenen metin
    - row_height: satır yüksekliği (px)
    - left/right padding: metin içi boşluklar (px)
    """

    full_text: str
    row_height: int
    left_padding: int = 6
    right_padding: int = 4

    # ------------------------------------------------------------------
    # Font / layout yardımcıları
    # ------------------------------------------------------------------

    def compute_font_point_size(self) -> float:
        """
        Satır yüksekliğine göre font point size hesaplar.
        """
        return self.row_height * 0.5

    def compute_available_width(self, total_width: int) -> int:
        """
        Padding'ler çıkarılmış kullanılabilir genişlik.
        """
        return max(0, total_width - self.left_padding - self.right_padding)

    def choose_display_text(
        self,
        metrics: QFontMetrics,
        available_width: int,
    ) -> str:
        """
        - Metnin tam hali sığıyorsa full_text
        - Sığmıyorsa Qt elideText ile '...' kısaltılmış hali döner.

        FIX: metrics.width() Qt5'te de deprecated — horizontalAdvance() kullanılıyor.
        """
        if available_width <= 0:
            return ""

        # BUG FIX: metrics.width(text) → metrics.horizontalAdvance(text)
        full_width = metrics.horizontalAdvance(self.full_text)
        if full_width <= available_width:
            return self.full_text

        return metrics.elidedText(
            self.full_text,
            Qt.ElideRight,
            available_width,
        )