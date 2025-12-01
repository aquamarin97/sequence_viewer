# msa_viewer/graphics/header_item.py

from typing import Optional

from PyQt5.QtCore import Qt, QRectF
from PyQt5.QtGui import QPainter, QFont, QPen, QBrush, QFontMetrics
from PyQt5.QtWidgets import QGraphicsItem

from graphics.header_item.header_item_model import HeaderRowModel



class HeaderRowItem(QGraphicsItem):
    """
    Header viewer içindeki tek satırlık header item'i.

    CMV:
    - Model : HeaderRowModel (full_text, row_height, padding, font size hesaplama)
    - View  : Bu sınıf (QGraphicsItem + paint/boundingRect)
    - Controller: Şimdilik yok; metin değişikliği vb. doğrudan model üzerinden
      yapılabilir ama dış API aynı bırakıldı.

    Dışarıdan bakıldığında hâlâ:
        HeaderRowItem(text, width, row_height)
        item.full_text
        item.font
        item.set_width(...)
    API'leri değişmeden çalışır.
    """

    def __init__(
        self,
        text: str,
        width: float,
        row_height: float,
        parent: Optional[QGraphicsItem] = None,
    ) -> None:
        super().__init__(parent)

        # Model
        self._model = HeaderRowModel(
            full_text=text,
            row_height=int(round(row_height)),
        )

        # View-side state
        self.width = float(width)
        self.row_height = int(round(row_height))

        self.font = QFont("Arial")
        self.font.setPointSizeF(self._model.compute_font_point_size())

    # ------------------------------------------------------------------
    # Eski API ile uyumluluk için property'ler
    # ------------------------------------------------------------------

    @property
    def full_text(self) -> str:
        """
        Eski kodlar item.full_text diye okuduğu için property ile forward ediyoruz.
        """
        return self._model.full_text

    # Gerekirse ileride setter eklenebilir:
    # @full_text.setter
    # def full_text(self, value: str) -> None:
    #     self._model.full_text = value
    #     self.update()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_width(self, width: float) -> None:
        """
        Header viewer resize olduğunda çağrılır.
        """
        if abs(width - self.width) < 0.5:
            return
        self.prepareGeometryChange()
        self.width = float(width)
        self.update()

    # ------------------------------------------------------------------
    # QGraphicsItem interface
    # ------------------------------------------------------------------

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

        total_width = int(rect.width())
        available_width = self._model.compute_available_width(total_width)
        display_text = self._model.choose_display_text(metrics, available_width)

        # Metin rengi
        painter.setPen(QPen(Qt.black))

        # Padding'leri modele göre kullan
        text_rect = rect.adjusted(
            self._model.left_padding,
            0,
            -self._model.right_padding,
            0,
        )

        painter.drawText(
            text_rect,
            Qt.AlignVCenter | Qt.AlignLeft,
            display_text,
        )

        painter.restore()
