from __future__ import annotations
import math
from typing import TYPE_CHECKING, FrozenSet, List, Optional
from PyQt5.QtCore import Qt, QRectF, QPoint
from PyQt5.QtGui import QPainter, QFontMetrics, QPen, QBrush, QColor
from PyQt5.QtWidgets import QGraphicsView, QGraphicsScene, QLineEdit
from graphics.header_item.header_item import HeaderRowItem
from model.row_selection_model import RowSelectionModel
from settings.theme import theme_manager

if TYPE_CHECKING:
    from widgets.row_layout import RowLayout

_DRAG_THRESHOLD_PX = 6
_DROP_LINE_WIDTH = 2

class HeaderViewerView(QGraphicsView):
    def __init__(self, parent=None, *, row_height=18.0, initial_width=160.0):
        super().__init__(parent)
        self.scene = QGraphicsScene(self); self.setScene(self.scene)
        self._char_height = int(round(row_height))
        self._annot_height = 0
        self._row_layout = None
        self.row_height = self._char_height
        self.header_width = float(initial_width)
        self.header_items = []
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        from PyQt5.QtWidgets import QFrame
        self.setFrameShape(QFrame.NoFrame)
        self.setMinimumWidth(60); self.setMouseTracking(True); self.setFocusPolicy(Qt.StrongFocus)
        self._selection = RowSelectionModel()
        self._edit_widget = None; self._editing_row = None
        self._press_pos = None; self._drag_source_row = None
        self._drag_insert_pos = None; self._dragging = False
        theme_manager.themeChanged.connect(self._on_theme_changed)
        self._apply_scene_background()

    def apply_row_layout(self, layout):
        self._row_layout = layout; self._annot_height = 0
        for i, item in enumerate(self.header_items):
            if i < layout.row_count:
                item.set_annot_height(layout.per_row_above_heights[i])
                item.set_below_ann_height(layout.per_row_below_heights[i])
                item.setPos(0, float(layout.y_offsets[i]))
        self._update_scene_rect()

    def set_annot_height(self, h):
        if self._row_layout is not None: return
        if self._annot_height == h: return
        self._annot_height = h; self.row_height = h + self._char_height
        stride = h + self._char_height
        for i, item in enumerate(self.header_items):
            item.set_annot_height(h); item.setPos(0, float(i * stride))
        self._update_scene_rect()

    @property
    def _row_stride_uniform(self): return self._annot_height + self._char_height

    def _row_at_viewport_y(self, y):
        scene_y = self.mapToScene(0, y).y()
        layout = self._row_layout
        if layout is not None and layout.row_count > 0: return layout.row_at_y(scene_y)
        stride = self._row_stride_uniform
        if stride <= 0: return 0
        return int(math.floor(scene_y / stride))

    def _insert_pos_at_viewport_y(self, y):
        scene_y = self.mapToScene(0, y).y()
        layout = self._row_layout
        if layout is not None and layout.row_count > 0: return layout.insert_pos_at_y(scene_y)
        stride = self._row_stride_uniform
        if stride <= 0: return 0
        insert = int(round(scene_y / stride))
        return max(0, min(insert, len(self.header_items)))

    def _item_viewport_rect(self, row_index):
        layout = self._row_layout
        if layout is not None and row_index < layout.row_count:
            y_start = float(layout.y_offsets[row_index]); height = float(layout.row_strides[row_index])
        else:
            stride = self._row_stride_uniform
            y_start = float(row_index * stride); height = float(stride)
        scene_rect = QRectF(0, y_start, self.viewport().width(), height)
        tl = self.mapFromScene(scene_rect.topLeft()); br = self.mapFromScene(scene_rect.bottomRight())
        return QRectF(tl, br)

    def add_header_item(self, display_text):
        row_index = len(self.header_items)
        item_width = self.viewport().width() or self.header_width
        layout = self._row_layout
        if layout is not None and row_index < layout.row_count:
            ann_h = layout.per_row_annot_heights[row_index]; y_start = float(layout.y_offsets[row_index])
        else:
            ann_h = self._annot_height; y_start = float(row_index * self._row_stride_uniform)
        below_h = 0
        if layout is not None and row_index < layout.row_count:
            below_h = layout.per_row_below_heights[row_index]
        item = HeaderRowItem(text=display_text, width=item_width, row_height=self._char_height, annot_height=ann_h, row_index=row_index)
        item.set_below_ann_height(below_h)
        item.setPos(0, y_start); self.scene.addItem(item)
        self.header_items.append(item); self._update_scene_rect()
        return item

    def clear_items(self):
        self._cancel_edit(); self._reset_drag_state()
        self.header_items.clear(); self.scene.clear()
        self._row_layout = None; self._update_scene_rect()

    def apply_selection_to_items(self, changed_rows):
        for row in changed_rows:
            if 0 <= row < len(self.header_items):
                self.header_items[row].set_selected(self._selection.is_selected(row))

    def _update_scene_rect(self):
        layout = self._row_layout
        if layout is not None and layout.row_count > 0: height = float(layout.total_height)
        else: height = float(len(self.header_items) * self._row_stride_uniform)
        width = self.viewport().width() or self.header_width
        self.scene.setSceneRect(0, 0, float(width), height)

    def compute_required_width(self):
        if not self.header_items: return 100
        metrics = QFontMetrics(self.header_items[0].font)
        max_px = max(metrics.horizontalAdvance(item.full_text) for item in self.header_items)
        return max_px + 6 + 4 + 4

    def resizeEvent(self, event):
        super().resizeEvent(event)
        w = self.viewport().width()
        for item in self.header_items: item.set_width(w)
        self._update_scene_rect()
        if self.header_items:
            required = self.compute_required_width()
            self.setMaximumWidth(required if w >= required else 16_777_215)
        else: self.setMaximumWidth(16_777_215)

    def _apply_scene_background(self):
        from PyQt5.QtGui import QBrush as _B
        self.scene.setBackgroundBrush(_B(theme_manager.current.row_bg_even))

    def drawBackground(self, painter, rect):
        painter.fillRect(rect, theme_manager.current.row_bg_even)

    def _on_theme_changed(self, _theme):
        self._apply_scene_background(); self._refresh_active_editor_style()
        self.scene.invalidate(); self.viewport().update()

    def _start_edit(self, row_index):
        if row_index < 0 or row_index >= len(self.header_items): return
        self._cancel_edit()
        item = self.header_items[row_index]
        layout = self._row_layout
        if layout is not None and row_index < layout.row_count:
            text_top_scene = float(layout.y_offsets[row_index] + layout.per_row_annot_heights[row_index])
        else:
            text_top_scene = float(row_index * self._row_stride_uniform + self._annot_height)
        vp_top = self.mapFromScene(0, text_top_scene).y()
        t = theme_manager.current
        editor = QLineEdit(self.viewport())
        full_text = item.full_text
        raw_header = full_text.split(". ", 1)[1] if ". " in full_text else full_text
        editor.setText(raw_header); editor.selectAll()
        margin = 2; vp_w = self.viewport().width()
        min_editor_h = max(self._char_height - margin * 2, 22)
        editor.setGeometry(margin, int(vp_top) + margin, vp_w - margin * 2, min_editor_h)
        self._apply_editor_style(editor, item)
        editor.show(); editor.setFocus()
        editor.returnPressed.connect(lambda: self._commit_edit(row_index))
        editor.editingFinished.connect(lambda: self._commit_edit(row_index))
        self._edit_widget = editor; self._editing_row = row_index
        item.set_hovered(True)

    def _apply_editor_style(self, editor, item):
        t = theme_manager.current
        editor.setStyleSheet(
            f"QLineEdit {{color:{t.text_primary.name()};background:{t.editor_bg};"
            f"border:1.5px solid {t.editor_border};border-radius:2px;padding:0px 4px;"
            f"font-family:Arial;font-size:{int(item._model.compute_font_point_size())}pt;}}")

    def _refresh_active_editor_style(self):
        if self._edit_widget is None or self._editing_row is None: return
        row = self._editing_row
        if 0 <= row < len(self.header_items):
            self._apply_editor_style(self._edit_widget, self.header_items[row])

    def _commit_edit(self, row_index):
        if self._edit_widget is None or self._editing_row != row_index: return
        new_text = self._edit_widget.text().strip(); self._cancel_edit()
        if not new_text: return
        self._on_edit_committed(row_index, new_text)

    def _cancel_edit(self):
        widget = self._edit_widget; self._edit_widget = None
        if widget is not None:
            widget.blockSignals(True); widget.hide(); widget.deleteLater()
        if self._editing_row is not None:
            idx = self._editing_row; self._editing_row = None
            if 0 <= idx < len(self.header_items): self.header_items[idx].set_hovered(False)

    def _reset_drag_state(self):
        if self._drag_source_row is not None:
            idx = self._drag_source_row
            if 0 <= idx < len(self.header_items): self.header_items[idx].set_dragging(False)
        self._drag_source_row = None; self._drag_insert_pos = None
        self._dragging = False; self._press_pos = None; self.viewport().update()

    def _update_drag(self, vp_pos):
        self._drag_insert_pos = self._insert_pos_at_viewport_y(vp_pos.y()); self.viewport().update()

    def _handle_selection(self, row, modifiers):
        n = len(self.header_items)
        if n == 0: return
        ctrl = bool(modifiers & Qt.ControlModifier); shift = bool(modifiers & Qt.ShiftModifier)
        if ctrl and shift: changed = self._selection.handle_shift_click(row, n)
        elif ctrl: changed = self._selection.handle_ctrl_click(row, n)
        elif shift: changed = self._selection.handle_shift_click(row, n)
        else: changed = self._selection.handle_click(row, n)
        self.apply_selection_to_items(changed)
        self._on_selection_changed(self._selection.selected_rows())

    def _on_edit_committed(self, row_index, new_text): pass
    def _on_row_move_requested(self, from_index, to_index): pass
    def _on_selection_changed(self, selected_rows): pass
    def _on_rows_delete_requested(self, rows): pass

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            row = self._row_at_viewport_y(event.pos().y())
            if self._editing_row is not None and self._editing_row != row:
                self._commit_edit(self._editing_row)
            if 0 <= row < len(self.header_items):
                self._press_pos = event.pos(); self._drag_source_row = row
                self._handle_selection(row, event.modifiers())
            else:
                changed = self._selection.clear()
                self.apply_selection_to_items(changed)
                self._on_selection_changed(self._selection.selected_rows())
            self.setFocus(); event.accept()
        else: super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if (event.buttons() & Qt.LeftButton and self._press_pos is not None and self._drag_source_row is not None):
            delta = (event.pos() - self._press_pos).manhattanLength()
            if not self._dragging and delta >= _DRAG_THRESHOLD_PX:
                self._dragging = True; self.header_items[self._drag_source_row].set_dragging(True)
                self.viewport().setCursor(Qt.SizeVerCursor)
            if self._dragging: self._update_drag(event.pos())
            event.accept()
        else: super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self._dragging and self._drag_source_row is not None:
                src = self._drag_source_row
                insert = self._drag_insert_pos if self._drag_insert_pos is not None else src
                to_idx = insert if insert <= src else insert - 1
                self._reset_drag_state(); self.viewport().unsetCursor()
                if to_idx != src: self._on_row_move_requested(src, to_idx)
            else: self._press_pos = None; self._drag_source_row = None
            event.accept()
        else: super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            row = self._row_at_viewport_y(event.pos().y())
            if 0 <= row < len(self.header_items):
                self._press_pos = None; self._drag_source_row = None; self._start_edit(row)
            event.accept()
        else: super().mouseDoubleClickEvent(event)

    def keyPressEvent(self, event):
        key = event.key(); ctrl = bool(event.modifiers() & Qt.ControlModifier)
        n = len(self.header_items)
        if ctrl and key == Qt.Key_A:
            changed = self._selection.select_all(n)
            self.apply_selection_to_items(changed)
            self._on_selection_changed(self._selection.selected_rows()); event.accept()
        elif key == Qt.Key_Escape:
            if self._edit_widget: self._cancel_edit()
            else:
                changed = self._selection.clear()
                self.apply_selection_to_items(changed)
                self._on_selection_changed(self._selection.selected_rows())
            event.accept()
        elif key in (Qt.Key_Delete, Qt.Key_Backspace):
            rows = self._selection.selected_rows()
            if rows: self._on_rows_delete_requested(rows)
            event.accept()
        else: super().keyPressEvent(event)

    def drawForeground(self, painter, rect):
        super().drawForeground(painter, rect)
        if not self._dragging or self._drag_insert_pos is None: return
        layout = self._row_layout
        if layout is not None and self._drag_insert_pos <= layout.row_count:
            if self._drag_insert_pos < layout.row_count:
                insert_y_scene = float(layout.y_offsets[self._drag_insert_pos])
            else: insert_y_scene = float(layout.total_height)
        else: insert_y_scene = float(self._drag_insert_pos * self._row_stride_uniform)
        vp_y = self.mapFromScene(0, insert_y_scene).y()
        vp_width = self.viewport().width(); t = theme_manager.current
        painter.save(); painter.resetTransform()
        pen = QPen(t.drop_indicator, _DROP_LINE_WIDTH); pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen); painter.setBrush(Qt.NoBrush)
        painter.drawLine(8, vp_y, vp_width-4, vp_y)
        from PyQt5.QtGui import QBrush as _B
        r = 4; painter.setBrush(_B(t.drop_indicator)); painter.setPen(Qt.NoPen)
        painter.drawEllipse(4, vp_y-r, r*2, r*2); painter.restore()