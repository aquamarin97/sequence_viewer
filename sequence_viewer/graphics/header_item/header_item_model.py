# graphics/header_item/header_item_model.py
from dataclasses import dataclass
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFontMetrics

@dataclass
class HeaderRowModel:
    full_text: str
    row_height: int
    left_padding: int = 6
    right_padding: int = 4

    def compute_font_point_size(self):
        return self.row_height * 0.5

    def compute_available_width(self, total_width):
        return max(0, total_width - self.left_padding - self.right_padding)

    def choose_display_text(self, metrics, available_width):
        if available_width <= 0: return ""
        full_width = metrics.horizontalAdvance(self.full_text)
        if full_width <= available_width: return self.full_text
        return metrics.elidedText(self.full_text, Qt.ElideRight, available_width)


