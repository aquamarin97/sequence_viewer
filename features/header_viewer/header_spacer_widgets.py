# features/header_viewer/header_spacer_widgets.py

from __future__ import annotations

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPainter, QPen, QBrush, QFont
from PyQt5.QtWidgets import QWidget

from settings.theme import theme_manager


class HeaderTopWidget(QWidget):
    """Navigation ruler ile hizalı üst boşluk."""

    def __init__(self, height: int = 28, parent=None) -> None:
        super().__init__(parent)
        self.setFixedHeight(height)
        theme_manager.themeChanged.connect(self.update)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        t = theme_manager.current
        painter.fillRect(self.rect(), QBrush(t.ruler_bg))
        painter.setPen(QPen(t.ruler_border))
        painter.drawLine(0, self.rect().bottom() - 1,
                         self.rect().right(), self.rect().bottom() - 1)
        painter.end()


class HeaderPositionSpacerWidget(QWidget):
    """Position ruler ile hizalı başlık spacer'ı."""

    def __init__(self, height: int = 24, parent=None) -> None:
        super().__init__(parent)
        self.setFixedHeight(height)
        theme_manager.themeChanged.connect(self.update)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        t    = theme_manager.current
        rect = self.rect()
        painter.fillRect(rect, QBrush(t.ruler_bg))
        font = QFont("Arial", 9)
        painter.setFont(font)
        painter.setPen(QPen(t.ruler_fg))
        painter.drawText(rect.adjusted(6, 0, 0, 0),
                         Qt.AlignVCenter | Qt.AlignLeft, "Header")
        painter.setPen(QPen(t.ruler_border))
        painter.drawLine(rect.left(), rect.bottom() - 1,
                         rect.right(), rect.bottom() - 1)
        painter.end()


class AnnotationSpacerWidget(QWidget):
    """
    Sol panelde AnnotationLayerWidget ile yükseklik-senkronlu spacer.
    """

    def __init__(self, height: int = 24, parent=None) -> None:
        super().__init__(parent)
        self.setFixedHeight(height)
        theme_manager.themeChanged.connect(self.update)

    def sync_height(self, height: int) -> None:
        if self.height() != height:
            self.setFixedHeight(height)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        t    = theme_manager.current
        rect = self.rect()
        painter.fillRect(rect, QBrush(t.row_bg_even))
        font = QFont("Arial", 8)
        font.setItalic(True)
        painter.setFont(font)
        painter.setPen(QPen(t.text_primary))
        painter.drawText(rect.adjusted(6, 0, 0, 0),
                         Qt.AlignVCenter | Qt.AlignLeft, "Annotations")
        painter.setPen(QPen(t.border_normal))
        painter.drawLine(rect.left(), rect.bottom() - 1,
                         rect.right(), rect.bottom() - 1)
        painter.end()


class ConsensusSpacerWidget(QWidget):
    """Consensus satırı ile hizalı sol panel spacer'ı."""

    def __init__(self, height: int = 20, parent=None) -> None:
        super().__init__(parent)
        self.setFixedHeight(height)
        theme_manager.themeChanged.connect(self.update)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        t    = theme_manager.current
        rect = self.rect()
        painter.fillRect(rect, QBrush(t.row_bg_odd))
        font = QFont("Arial", 8)
        font.setItalic(True)
        painter.setFont(font)
        painter.setPen(QPen(t.text_primary))
        painter.drawText(rect.adjusted(6, 0, 0, 0),
                         Qt.AlignVCenter | Qt.AlignLeft, "Consensus")
        painter.setPen(QPen(t.border_normal))
        painter.drawLine(rect.left(), rect.bottom() - 1,
                         rect.right(), rect.bottom() - 1)
        painter.end()