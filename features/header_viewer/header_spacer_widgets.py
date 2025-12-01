# msa_viewer/header_viewer/header_spacer_widgets.py

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPainter, QPen, QBrush, QColor
from PyQt5.QtWidgets import QWidget


class HeaderTopWidget(QWidget):
    """
    Artık tamamen boş spacer — hiç yazı çizmez.
    Sadece cetvel yüksekliği kadar alan oluşturur.
    """

    def __init__(self, height: int = 28, parent=None) -> None:
        super().__init__(parent)
        self._fixed_height = height
        self.setMinimumHeight(self._fixed_height)
        self.setMaximumHeight(self._fixed_height)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        rect = self.rect()

        # Arka plan
        painter.fillRect(rect, QBrush(Qt.white))

        # Alt çizgi (SequencePositionRuler ile uyum için)
        painter.setPen(QPen(QColor(0, 0, 0)))
        painter.drawLine(
            rect.left(),
            rect.bottom() - 1,
            rect.right(),
            rect.bottom() - 1,
        )

        painter.end()


class HeaderPositionSpacerWidget(QWidget):
    """
    'Header' yazısını içeren başlık çubuğu.
    SequencePositionRuler yüksekliğinde olmalıdır.
    """

    def __init__(self, height: int = 24, parent=None) -> None:
        super().__init__(parent)
        self._fixed_height = height
        self.setMinimumHeight(self._fixed_height)
        self.setMaximumHeight(self._fixed_height)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        rect = self.rect()

        # Arka plan
        painter.fillRect(rect, QBrush(Qt.white))

        # "Header" text
        painter.setPen(QPen(QColor(80, 80, 80)))
        font = painter.font()
        font.setPointSize(9)
        painter.setFont(font)

        text_rect = rect.adjusted(6, 0, 0, 0)
        painter.drawText(text_rect, Qt.AlignVCenter | Qt.AlignLeft, "Header")

        # Alt konteyner çizgisi
        painter.setPen(QPen(QColor(0, 0, 0)))
        painter.drawLine(
            rect.left(),
            rect.bottom() - 1,
            rect.right(),
            rect.bottom() - 1,
        )

        painter.end()
