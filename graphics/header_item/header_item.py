# graphics/header_item/header_item.py
"""
Header satır item'ı — v4: seçim durumunda annotation boşluklarını da
row_band_highlight ile boyar.
"""
from __future__ import annotations
import weakref
from typing import Optional
from PyQt5.QtCore import Qt, QRectF
from PyQt5.QtGui import QPainter, QFont, QPen, QBrush, QFontMetrics, QColor
from PyQt5.QtWidgets import QGraphicsItem, QStyleOptionGraphicsItem
from graphics.header_item.header_item_model import HeaderRowModel
from settings.theme import theme_manager

class HeaderRowItem(QGraphicsItem):
    def __init__(self, text, width, row_height, annot_height=0, row_index=0, parent=None):
        super().__init__(parent)
        self._model = HeaderRowModel(full_text=text, row_height=int(round(row_height)))
        self.width = float(width)
        self.row_height = int(round(row_height))
        self.annot_height = int(annot_height)
        self.below_ann_height = 0
        self.row_index = row_index
        self.font = QFont("Arial")
        self.font.setPointSizeF(self._model.compute_font_point_size())
        self._hovered = False
        self._selected = False
        self._dragging = False
        self.setAcceptHoverEvents(True)
        _ref = weakref.ref(self)
        theme_manager.themeChanged.connect(lambda theme, r=_ref: (s := r()) and s._on_theme_changed(theme))

    @property
    def total_height(self): return self.annot_height + self.row_height + self.below_ann_height
    @property
    def full_text(self): return self._model.full_text

    def set_annot_height(self, h):
        if self.annot_height == h: return
        self.prepareGeometryChange(); self.annot_height = h; self.update()
    def set_below_ann_height(self, h):
        if self.below_ann_height == h: return
        self.prepareGeometryChange(); self.below_ann_height = h; self.update()
    def set_hovered(self, hovered):
        if self._hovered == hovered: return
        self._hovered = hovered; self.update()
    def set_selected(self, selected):
        if self._selected == selected: return
        self._selected = selected; self.update()
    def set_dragging(self, dragging):
        if self._dragging == dragging: return
        self._dragging = dragging; self.update()
    def set_row_index(self, index):
        if self.row_index == index: return
        self.row_index = index; self.update()
    def set_width(self, width):
        if abs(width - self.width) < 0.5: return
        self.prepareGeometryChange(); self.width = float(width); self.update()
    def set_row_height(self, height):
        h = int(round(height))
        if self.row_height == h: return
        self.prepareGeometryChange()
        self.row_height = h
        self._model.row_height = h
        self.font.setPointSizeF(self._model.compute_font_point_size())
        self.update()
    def _on_theme_changed(self, _theme): self.update()

    def _resolve_bg_color(self):
        t = theme_manager.current
        if self._dragging: return t.row_bg_dragging
        if self._selected: return t.row_bg_selected_hover if self._hovered else t.row_bg_selected
        if self._hovered: return t.row_bg_hover
        return t.row_bg_even if self.row_index % 2 == 0 else t.row_bg_odd

    def _resolve_text_color(self):
        t = theme_manager.current
        return t.text_selected if self._selected else t.text_primary

    def boundingRect(self): return QRectF(0, 0, self.width, self.total_height)
    def hoverEnterEvent(self, event): self.set_hovered(True); super().hoverEnterEvent(event)
    def hoverLeaveEvent(self, event): self.set_hovered(False); super().hoverLeaveEvent(event)

    def paint(self, painter, option, widget=None):
        painter.save()
        t = theme_manager.current
        total_w = self.width
        ann_h = float(self.annot_height)
        row_h = float(self.row_height)

        # ---- Üst annotation bölgesi ----
        if ann_h > 0:
            if self._selected:
                ann_bg = QColor(t.row_band_highlight)
            elif self._hovered:
                ann_bg = t.row_bg_hover
            else:
                ann_bg = t.row_bg_even if self.row_index % 2 == 0 else t.row_bg_odd
            painter.fillRect(QRectF(0, 0, total_w, ann_h), QBrush(ann_bg))

        # ---- Header metin bölgesi ----
        text_top = ann_h
        text_rect_full = QRectF(0, text_top, total_w, row_h)
        bg = self._resolve_bg_color()
        painter.setPen(Qt.NoPen); painter.setBrush(QBrush(bg))
        painter.drawRect(text_rect_full)

        if self._dragging:
            painter.setPen(QPen(t.border_drag, 1, Qt.DashLine))
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(text_rect_full.adjusted(0, 0, -1, -1))
        elif self.below_ann_height == 0:
            painter.setPen(QPen(t.border_normal, 0))
            painter.drawLine(int(0), int(text_top + row_h) - 1, int(total_w), int(text_top + row_h) - 1)

        if self._selected:
            painter.setPen(Qt.NoPen); painter.setBrush(QBrush(t.drop_indicator))
            painter.drawRect(QRectF(0, text_top, 2, row_h))

        # Metin
        painter.setFont(self.font)
        metrics = QFontMetrics(self.font)
        avail_width = self._model.compute_available_width(int(total_w))
        display_txt = self._model.choose_display_text(metrics, avail_width)
        painter.setPen(QPen(self._resolve_text_color()))
        draw_rect = QRectF(self._model.left_padding + (3 if self._selected else 0), text_top, total_w - self._model.left_padding - self._model.right_padding, row_h)
        painter.drawText(draw_rect, Qt.AlignVCenter | Qt.AlignLeft, display_txt)

        # ---- Alt annotation bölgesi ----
        below_h = float(self.below_ann_height)
        if below_h > 0:
            below_top = ann_h + row_h
            if self._selected:
                below_bg = QColor(t.row_band_highlight)
            elif self._hovered:
                below_bg = t.row_bg_hover
            else:
                below_bg = t.row_bg_even if self.row_index % 2 == 0 else t.row_bg_odd
            painter.fillRect(QRectF(0, below_top, total_w, below_h), QBrush(below_bg))
            painter.setPen(QPen(t.border_normal, 0))
            painter.drawLine(int(0), int(below_top + below_h) - 1, int(total_w), int(below_top + below_h) - 1)

        painter.restore()