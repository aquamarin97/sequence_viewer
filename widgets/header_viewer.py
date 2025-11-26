# msa_viewer/widgets/header_viewer.py

from typing import List

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPainter, QPen, QBrush, QColor
from PyQt5.QtWidgets import (
    QGraphicsView,
    QGraphicsScene,
    QWidget,
)
from graphics.header_item import HeaderRowItem

from PyQt5.QtGui import QFontMetrics


class HeaderViewerWidget(QGraphicsView):
    """
    Sadece header satırlarını çizen view.
    SequenceViewerWidget ile aynı row_height kullanır,
    dikey scroll barları senkronize edilir (SequenceWorkspaceWidget içinde).
    """

    def __init__(
        self,
        parent=None,
        row_height: float = 18.0,
        initial_width: float = 160.0,
    ) -> None:
        super().__init__(parent)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)

        self.row_height = int(round(row_height))
        self.header_width = initial_width

        self.header_items: List[HeaderRowItem] = []

        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.setAlignment(Qt.AlignLeft | Qt.AlignTop)

        self.setMinimumWidth(60)
        self.setMaximumWidth(400)

    def add_header(self, text: str) -> None:
        row_index = len(self.header_items)

        # 🔹 Gösterilecek metin: "1. HeaderText", "2. HeaderText", ...
        display_text = f"{row_index + 1}. {text}"

        item = HeaderRowItem(
            text=display_text,
            width=self.viewport().width() or self.header_width,
            row_height=self.row_height,
        )
        item.setPos(0, row_index * self.row_height)
        self.scene.addItem(item)
        self.header_items.append(item)
        self._update_scene_rect()

    def clear(self) -> None:
        self.header_items.clear()
        self.scene.clear()
        self._update_scene_rect()

    def _update_scene_rect(self) -> None:
        height = len(self.header_items) * self.row_height
        width = self.viewport().width() or self.header_width
        self.scene.setSceneRect(0, 0, width, height)
    def compute_required_width(self) -> int:
        """
        Header panelinin en fazla olması gereken genişliği hesaplar.
        En uzun header FULL metninin piksel genişliği + padding + küçük buffer döner.
        """
        if not self.header_items:
            return 100  # fallback

        metrics = QFontMetrics(self.header_items[0].font)
        max_px = 0

        left_padding = 6
        right_padding = 4
        safety = 4   # 🔹 1–2 px’lik hesaplama farklarını tolere etmek için

        for item in self.header_items:
            w = metrics.width(item.full_text)
            if w > max_px:
                max_px = w

        return max_px + left_padding + right_padding + safety
    
    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)

        # Header genişliği değiştiğinde tüm item'ların genişliğini güncelle
        w = self.viewport().width()
        for item in self.header_items:
            item.set_width(w)
        self._update_scene_rect()

        # 🔹 Dinamik max-width sınırı
        required = self.compute_required_width() if self.header_items else 10

        if w >= required:
            # Header metinlerinin tamamını gösterebildiğimiz noktaya geldik
            # -> daha fazla büyümeye izin vermeyelim
            self.setMaximumWidth(required)
        else:
            # Henüz tam göstermiyorsa serbest büyüyebilsin
            # Qt'nin "sonsuz" default max'ına yakın büyük bir değer
            self.setMaximumWidth(16777215)

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
        painter.drawLine(rect.left(), rect.bottom() - 1,
                         rect.right(), rect.bottom() - 1)

        painter.end()
        
class HeaderPositionSpacerWidget(QWidget):
    """
    Artık 'Header' yazısını içeren başlık çubuğu.
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
            rect.left(), rect.bottom() - 1,
            rect.right(), rect.bottom() - 1
        )

        painter.end()
