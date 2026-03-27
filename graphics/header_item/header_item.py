# graphics/header_item/header_item.py
"""
Header satır item'ı — v3 hizalama düzeltmesi.

Yükseklik artık row_stride (per_row_annot_h + char_height) olabilir.
Metin ve seçim rengi SADECE alt char_height kısmında çizilir.
Üst per_row_annot_h kısım annotation şeridine karşılık gelen boş/tonlu alan.

Bu sayede:
- Header font boyutu değişmez — profesyonel görünüm korunur.
- Header ve sequence satırları annotation varlığında da piksel-piksel hizalı.
"""

from __future__ import annotations

from typing import Optional

from PyQt5.QtCore import Qt, QRectF
from PyQt5.QtGui import (
    QPainter, QFont, QPen, QBrush, QFontMetrics, QColor,
)
from PyQt5.QtWidgets import QGraphicsItem, QStyleOptionGraphicsItem

from graphics.header_item.header_item_model import HeaderRowModel
from settings.theme import theme_manager


class HeaderRowItem(QGraphicsItem):
    """
    Header viewer içindeki tek satırlık item.

    Parametreler
    ------------
    text        : görüntülenecek metin
    width       : item genişliği (px)
    row_height  : char_height — metnin çizildiği gerçek satır yüksekliği
    annot_height: annotation şerid yüksekliği (üst boşluk). 0 ise yok.
    row_index   : zebra ve seçim için
    """

    def __init__(
        self,
        text:         str,
        width:        float,
        row_height:   float,
        annot_height: int   = 0,
        row_index:    int   = 0,
        parent: Optional[QGraphicsItem] = None,
    ) -> None:
        super().__init__(parent)

        self._model = HeaderRowModel(
            full_text=text,
            row_height=int(round(row_height)),
        )

        self.width        = float(width)
        self.row_height   = int(round(row_height))   # metin bölgesi yüksekliği
        self.annot_height = int(annot_height)         # üst boşluk yüksekliği
        self.row_index    = row_index

        # Font — char_height bazlı, değişmez
        self.font = QFont("Arial")
        self.font.setPointSizeF(self._model.compute_font_point_size())

        # Görsel durum
        self._hovered:  bool = False
        self._selected: bool = False
        self._dragging: bool = False

        self.setAcceptHoverEvents(True)
        theme_manager.themeChanged.connect(self._on_theme_changed)

    # ------------------------------------------------------------------
    # Toplam item yüksekliği (annot_height + row_height)
    # ------------------------------------------------------------------

    @property
    def total_height(self) -> int:
        return self.annot_height + self.row_height

    # ------------------------------------------------------------------
    # Eski API uyumluluğu
    # ------------------------------------------------------------------

    @property
    def full_text(self) -> str:
        return self._model.full_text

    # ------------------------------------------------------------------
    # Durum güncelleme
    # ------------------------------------------------------------------

    def set_annot_height(self, h: int) -> None:
        """Workspace per_row_annot_height değişince çağrılır."""
        if self.annot_height == h:
            return
        self.prepareGeometryChange()
        self.annot_height = h
        self.update()

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
        return t.row_bg_even if self.row_index % 2 == 0 else t.row_bg_odd

    def _resolve_text_color(self) -> QColor:
        t = theme_manager.current
        return t.text_selected if self._selected else t.text_primary

    # ------------------------------------------------------------------
    # QGraphicsItem
    # ------------------------------------------------------------------

    def boundingRect(self) -> QRectF:
        return QRectF(0, 0, self.width, self.total_height)

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
        t = theme_manager.current

        total_w = self.width
        total_h = float(self.total_height)
        ann_h   = float(self.annot_height)
        row_h   = float(self.row_height)

        # ---- Üst bölge: annotation şeridine karşılık gelen boş alan ----
        if ann_h > 0:
            # Sequence viewer'daki annotation şerit arkaplanıyla uyumlu ton
            ann_bg = QColor(t.row_bg_odd)
            painter.fillRect(QRectF(0, 0, total_w, ann_h), QBrush(ann_bg))

            # Alt çizgi (annotation şeridini ayıran ince çizgi)
            painter.setPen(QPen(t.border_normal, 0))
            painter.drawLine(
                int(0), int(ann_h) - 1,
                int(total_w), int(ann_h) - 1,
            )

        # ---- Alt bölge: gerçek header satırı ----
        text_top = ann_h
        text_rect_full = QRectF(0, text_top, total_w, row_h)

        bg = self._resolve_bg_color()
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(bg))
        painter.drawRect(text_rect_full)

        # Drag kenarlığı
        if self._dragging:
            painter.setPen(QPen(t.border_drag, 1, Qt.DashLine))
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(text_rect_full.adjusted(0, 0, -1, -1))
        else:
            # Sadece alt çizgi
            painter.setPen(QPen(t.border_normal, 0))
            painter.drawLine(
                int(0),      int(text_top + row_h) - 1,
                int(total_w), int(text_top + row_h) - 1,
            )

        # Seçim göstergesi: sol kenar çubuğu 2px
        if self._selected:
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(t.drop_indicator))
            painter.drawRect(QRectF(0, text_top, 2, row_h))

        # Metin
        painter.setFont(self.font)
        metrics     = QFontMetrics(self.font)
        avail_width = self._model.compute_available_width(int(total_w))
        display_txt = self._model.choose_display_text(metrics, avail_width)

        painter.setPen(QPen(self._resolve_text_color()))
        draw_rect = QRectF(
            self._model.left_padding + (3 if self._selected else 0),
            text_top,
            total_w - self._model.left_padding - self._model.right_padding,
            row_h,
        )
        painter.drawText(draw_rect, Qt.AlignVCenter | Qt.AlignLeft, display_txt)

        painter.restore()