# graphics/header_item/header_item.py

from __future__ import annotations

from typing import Optional

from PyQt5.QtCore import Qt, QRectF
from PyQt5.QtGui import (
    QPainter, QFont, QPen, QBrush,
    QFontMetrics, QColor,
)
from PyQt5.QtWidgets import QGraphicsItem, QStyleOptionGraphicsItem

from graphics.header_item.header_item_model import HeaderRowModel
from settings.theme import theme_manager


class HeaderRowItem(QGraphicsItem):
    """
    Header viewer içindeki tek satırlık item.

    Görsel özellikler
    -----------------
    * Zebra striping : çift/tek satır farklı arkaplan (tema token'ı)
    * Hover          : fare üzerinde highlight
    * Selected       : Windows tarzı seçim rengi
    * Dragging       : sürükleniyor göstergesi
    * Dark Mode      : theme_manager.themeChanged sinyaline bağlı

    Parametre
    ---------
    row_index : int
        Zebra ve seçim mantığı için satır indeksi.
        Sıra değişince HeaderViewerView tarafından güncellenir.
    """

    def __init__(
        self,
        text: str,
        width: float,
        row_height: float,
        row_index: int = 0,
        parent: Optional[QGraphicsItem] = None,
    ) -> None:
        super().__init__(parent)

        self._model = HeaderRowModel(
            full_text=text,
            row_height=int(round(row_height)),
        )

        self.width      = float(width)
        self.row_height = int(round(row_height))
        self.row_index  = row_index

        self.font = QFont("Arial")
        self.font.setPointSizeF(self._model.compute_font_point_size())

        # Görsel durum
        self._hovered:  bool = False
        self._selected: bool = False
        self._dragging: bool = False

        # Tema değişince yeniden çiz
        theme_manager.themeChanged.connect(self._on_theme_changed)
        self.setAcceptHoverEvents(True)

    # ------------------------------------------------------------------
    # Eski API uyumluluğu
    # ------------------------------------------------------------------

    @property
    def full_text(self) -> str:
        return self._model.full_text

    # ------------------------------------------------------------------
    # Durum güncelleme
    # ------------------------------------------------------------------

    def set_hovered(self, hovered: bool) -> None:
        if self._hovered == hovered:
            return
        self._hovered = hovered
        self.update()

    def set_selected(self, selected: bool) -> None:
        if self._selected == selected:
            return
        self._selected = selected
        self.update()

    def set_dragging(self, dragging: bool) -> None:
        if self._dragging == dragging:
            return
        self._dragging = dragging
        self.update()

    def set_row_index(self, index: int) -> None:
        """Sıra değişince zebra rengini güncellemek için çağrılır."""
        if self.row_index == index:
            return
        self.row_index = index
        self.update()

    def set_width(self, width: float) -> None:
        if abs(width - self.width) < 0.5:
            return
        self.prepareGeometryChange()
        self.width = float(width)
        self.update()

    def _on_theme_changed(self, _theme) -> None:
        self.update()

    # ------------------------------------------------------------------
    # Renk seçimi
    # ------------------------------------------------------------------

    def _resolve_bg_color(self) -> QColor:
        t = theme_manager.current

        if self._dragging:
            return t.row_bg_dragging

        if self._selected:
            return t.row_bg_selected_hover if self._hovered else t.row_bg_selected

        if self._hovered:
            return t.row_bg_hover

        # Zebra
        return t.row_bg_even if self.row_index % 2 == 0 else t.row_bg_odd

    def _resolve_text_color(self) -> QColor:
        t = theme_manager.current
        return t.text_selected if self._selected else t.text_primary

    def _resolve_border_pen(self) -> QPen:
        t = theme_manager.current
        if self._dragging:
            return QPen(t.border_drag, 1, Qt.DashLine)
        # Alt sınır çizgisi — cosmetic
        return QPen(t.border_normal, 0)

    # ------------------------------------------------------------------
    # QGraphicsItem
    # ------------------------------------------------------------------

    def boundingRect(self) -> QRectF:
        return QRectF(0, 0, self.width, self.row_height)

    def hoverEnterEvent(self, event) -> None:
        self.set_hovered(True)
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event) -> None:
        self.set_hovered(False)
        super().hoverLeaveEvent(event)

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionGraphicsItem,
        widget=None,
    ) -> None:
        painter.save()
        painter.setFont(self.font)

        rect = self.boundingRect()

        # --- Arkaplan ---
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(self._resolve_bg_color()))
        painter.drawRect(rect)

        # --- Alt kenarlık çizgisi (drag değilse ince gri; drag ise dashed mavi) ---
        painter.setPen(self._resolve_border_pen())
        if self._dragging:
            painter.drawRect(rect.adjusted(0, 0, -1, -1))
        else:
            # Sadece alt çizgi — daha temiz görünüm
            painter.drawLine(
                int(rect.left()),  int(rect.bottom()) - 1,
                int(rect.right()), int(rect.bottom()) - 1,
            )

        # --- Seçim göstergesi: sol kenar çubuğu (2 px) ---
        if self._selected:
            t = theme_manager.current
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(t.drop_indicator))   # aynı mavi
            painter.drawRect(QRectF(0, 0, 2, self.row_height))

        # --- Metin ---
        metrics      = QFontMetrics(self.font)
        avail_width  = self._model.compute_available_width(int(rect.width()))
        display_text = self._model.choose_display_text(metrics, avail_width)

        painter.setPen(QPen(self._resolve_text_color()))
        text_rect = rect.adjusted(
            self._model.left_padding + (3 if self._selected else 0),
            0,
            -self._model.right_padding,
            0,
        )
        painter.drawText(text_rect, Qt.AlignVCenter | Qt.AlignLeft, display_text)

        painter.restore()