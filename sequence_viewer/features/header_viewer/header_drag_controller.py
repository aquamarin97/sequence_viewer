from __future__ import annotations

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QBrush, QPen

from sequence_viewer.settings.mouse_binding_manager import mouse_binding_manager
from sequence_viewer.settings.theme import theme_manager

_DROP_LINE_WIDTH = 2


class HeaderDragController:
    def __init__(self, view, layout_calculator) -> None:
        self._view = view
        self._layout_calculator = layout_calculator
        self._press_pos = None
        self._drag_source_row = None
        self._drag_insert_pos = None
        self._dragging = False

    def begin_press(self, pos, row: int) -> None:
        self._press_pos = pos
        self._drag_source_row = row

    def clear_press(self) -> None:
        self._press_pos = None
        self._drag_source_row = None

    def reset(self) -> None:
        if self._drag_source_row is not None:
            row = self._drag_source_row
            if 0 <= row < len(self._view.header_items):
                self._view.header_items[row].set_dragging(False)
        self._drag_source_row = None
        self._drag_insert_pos = None
        self._dragging = False
        self._press_pos = None
        self._view.viewport().update()

    def handle_move(self, event) -> bool:
        if (
            not (event.buttons() & Qt.LeftButton)
            or self._press_pos is None
            or self._drag_source_row is None
            or not mouse_binding_manager.is_header_reorder_event(event.modifiers(), Qt.LeftButton)
        ):
            return False
        delta = (event.pos() - self._press_pos).manhattanLength()
        if not self._dragging and delta >= mouse_binding_manager.drag_threshold("header_viewer"):
            self._dragging = True
            self._view.header_items[self._drag_source_row].set_dragging(True)
            self._view.viewport().setCursor(Qt.SizeVerCursor)
        if self._dragging:
            self._drag_insert_pos = self._layout_calculator.insert_pos_at_viewport_y(event.pos().y())
            self._view.viewport().update()
        return self._dragging

    def handle_release(self):
        if not self._dragging or self._drag_source_row is None:
            self.clear_press()
            return None
        source = self._drag_source_row
        insert = self._drag_insert_pos if self._drag_insert_pos is not None else source
        target = insert if insert <= source else insert - 1
        self.reset()
        self._view.viewport().unsetCursor()
        if target == source:
            return None
        return source, target

    def draw_drop_indicator(self, painter) -> None:
        if not self._dragging or self._drag_insert_pos is None:
            return
        layout = self._view._row_layout
        if layout is not None and self._drag_insert_pos <= layout.row_count:
            if self._drag_insert_pos < layout.row_count:
                insert_y_scene = float(layout.y_offsets[self._drag_insert_pos])
            else:
                insert_y_scene = float(layout.total_height)
        else:
            insert_y_scene = float(self._drag_insert_pos * self._view._row_stride_uniform)
        viewport_y = self._view.mapFromScene(0, insert_y_scene).y()
        viewport_width = self._view.viewport().width()
        theme = theme_manager.current
        painter.save()
        painter.resetTransform()
        pen = QPen(theme.drop_indicator, _DROP_LINE_WIDTH)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawLine(8, viewport_y, viewport_width - 4, viewport_y)
        radius = 4
        painter.setBrush(QBrush(theme.drop_indicator))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(4, viewport_y - radius, radius * 2, radius * 2)
        painter.restore()
