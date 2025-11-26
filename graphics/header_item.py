# msa_viewer/graphics/header_item.py

from typing import Optional

from PyQt5.QtCore import Qt, QRectF
from PyQt5.QtGui import QPainter, QFont, QPen, QBrush, QFontMetrics
from PyQt5.QtWidgets import QGraphicsItem

class HeaderRowItem(QGraphicsItem):
    def __init__(
        self,
        text: str,
        width: float,
        row_height: float,
        parent: Optional[QGraphicsItem] = None,
    ) -> None:
        super().__init__(parent)
        self.full_text = text          # 🔹 tam metni burada saklıyoruz
        self.width = width
        self.row_height = int(round(row_height))

        self.font = QFont("Arial")
        self.font.setPointSizeF(self.row_height * 0.5)

    def set_width(self, width: float) -> None:
        if abs(width - self.width) < 0.5:
            return
        self.prepareGeometryChange()
        self.width = width
        self.update()

    def boundingRect(self) -> QRectF:
        return QRectF(0, 0, self.width, self.row_height)
    def paint(self, painter: QPainter, option, widget=None) -> None:
        painter.save()
        painter.setFont(self.font)

        rect = self.boundingRect()

        # Arka plan
        painter.setBrush(QBrush(Qt.white))
        painter.setPen(Qt.NoPen)
        painter.drawRect(rect)

        metrics = QFontMetrics(self.font)
        left_padding = 6
        right_padding = 4
        available_width = max(0, int(rect.width()) - left_padding - right_padding)

        # 🔹 Önce gerçekten sığıp sığmadığını kontrol et
        full_width = metrics.width(self.full_text)  # Qt5 için; Qt6'da horizontalAdvance
        if full_width <= available_width:
            display_text = self.full_text
        else:
            display_text = metrics.elidedText(
                self.full_text,
                Qt.ElideRight,
                available_width,
            )

        painter.setPen(QPen(Qt.black))
        painter.drawText(
            rect.adjusted(left_padding, 0, -right_padding, 0),
            Qt.AlignVCenter | Qt.AlignLeft,
            display_text,
        )

        painter.restore()