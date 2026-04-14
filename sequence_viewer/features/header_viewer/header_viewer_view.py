# sequence_viewer/features/header_viewer/header_viewer_view.py
from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QBrush, QFontMetrics, QPainter
from PyQt5.QtWidgets import QGraphicsScene, QGraphicsView

from sequence_viewer.features.header_viewer.header_drag_controller import HeaderDragController
from sequence_viewer.features.header_viewer.header_inline_editor import HeaderInlineEditor
from sequence_viewer.features.header_viewer.header_layout_calculator import HeaderLayoutCalculator
from sequence_viewer.features.header_viewer.header_selection_handler import (
    HeaderSelectionHandler,
)
from sequence_viewer.graphics.header_item.header_item import HeaderRowItem
from sequence_viewer.model.row_selection_model import RowSelectionModel
from sequence_viewer.settings.mouse_binding_manager import MouseAction, mouse_binding_manager
from sequence_viewer.settings.theme import theme_manager

if TYPE_CHECKING:
    from sequence_viewer.workspace.row_layout import RowLayout


class HeaderViewerView(QGraphicsView):
    def __init__(self, parent=None, *, row_height=18.0, initial_width=160.0):
        super().__init__(parent)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
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
        self.setMinimumWidth(60)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)

        self._selection = RowSelectionModel()
        self._selection_handler = HeaderSelectionHandler(self._selection)
        self._layout_calc = HeaderLayoutCalculator(self)
        self._editor = HeaderInlineEditor(self)
        self._drag = HeaderDragController(self, self._layout_calc)

        theme_manager.themeChanged.connect(self._on_theme_changed)
        from sequence_viewer.settings.display_settings_manager import display_settings_manager

        display_settings_manager.displaySettingsChanged.connect(self._on_display_settings_changed)
        self._apply_scene_background()

    @property
    def selection(self):
        return self._selection

    @property
    def _row_stride_uniform(self):
        return self._annot_height + self._char_height

    def apply_row_layout(self, layout):
        self._row_layout = layout
        self._annot_height = 0
        for index, item in enumerate(self.header_items):
            if index < layout.row_count:
                item.set_annot_height(layout.per_row_above_heights[index])
                item.set_below_ann_height(layout.per_row_below_heights[index])
                item.setPos(0, float(layout.y_offsets[index]))
        self._update_scene_rect()

    def set_annot_height(self, height):
        if self._row_layout is not None:
            return
        if self._annot_height == height:
            return
        self._annot_height = height
        self.row_height = height + self._char_height
        stride = height + self._char_height
        for index, item in enumerate(self.header_items):
            item.set_annot_height(height)
            item.setPos(0, float(index * stride))
        self._update_scene_rect()

    def _row_at_viewport_y(self, y):
        return self._layout_calc.row_at_viewport_y(y)

    def _insert_pos_at_viewport_y(self, y):
        return self._layout_calc.insert_pos_at_viewport_y(y)

    def _item_viewport_rect(self, row_index):
        return self._layout_calc.item_viewport_rect(row_index)

    def add_header_item(self, display_text):
        row_index = len(self.header_items)
        item_width = self.viewport().width() or self.header_width
        layout = self._row_layout
        if layout is not None and row_index < layout.row_count:
            annot_height = layout.per_row_annot_heights[row_index]
            y_start = float(layout.y_offsets[row_index])
            below_height = layout.per_row_below_heights[row_index]
        else:
            annot_height = self._annot_height
            y_start = float(row_index * self._row_stride_uniform)
            below_height = 0
        item = HeaderRowItem(
            text=display_text,
            width=item_width,
            row_height=self._char_height,
            annot_height=annot_height,
            row_index=row_index,
        )
        item.set_below_ann_height(below_height)
        item.setPos(0, y_start)
        self.scene.addItem(item)
        self.header_items.append(item)
        self._update_scene_rect()
        return item

    def clear_items(self):
        self._editor.cancel_edit()
        self._drag.reset()
        self.header_items.clear()
        self.scene.clear()
        self._row_layout = None
        self._update_scene_rect()

    def apply_selection_to_items(self, changed_rows):
        for row in changed_rows:
            if 0 <= row < len(self.header_items):
                self.header_items[row].set_selected(self._selection.is_selected(row))

    def _update_scene_rect(self):
        layout = self._row_layout
        if layout is not None and layout.row_count > 0:
            height = float(layout.total_height)
        else:
            height = float(len(self.header_items) * self._row_stride_uniform)
        width = self.viewport().width() or self.header_width
        self.scene.setSceneRect(0, 0, float(width), height)

    def compute_required_width(self):
        if not self.header_items:
            return 100
        metrics = QFontMetrics(self.header_items[0].font)
        max_px = max(metrics.horizontalAdvance(item.full_text) for item in self.header_items)
        return max_px + 6 + 4 + 4

    def resizeEvent(self, event):
        super().resizeEvent(event)
        width = self.viewport().width()
        for item in self.header_items:
            item.set_width(width)
        self._update_scene_rect()
        if self.header_items:
            required = self.compute_required_width()
            self.setMaximumWidth(required if width >= required else 16_777_215)
        else:
            self.setMaximumWidth(16_777_215)

    def _apply_scene_background(self):
        self.scene.setBackgroundBrush(QBrush(theme_manager.current.row_bg_even))

    def drawBackground(self, painter, rect):
        painter.fillRect(rect, theme_manager.current.row_bg_even)

    def _on_theme_changed(self, _theme):
        self._apply_scene_background()
        self._editor.refresh_style(self.header_items)
        self.scene.invalidate()
        self.viewport().update()

    def _on_display_settings_changed(self):
        from sequence_viewer.settings.display_settings_manager import display_settings_manager

        new_char_height = display_settings_manager.sequence_char_height
        if self._char_height == new_char_height:
            return
        self._char_height = new_char_height
        for item in self.header_items:
            item.set_row_height(new_char_height)
        self._update_scene_rect()
        self.scene.invalidate()
        self.viewport().update()

    def _start_edit(self, row_index):
        if row_index < 0 or row_index >= len(self.header_items):
            return
        item = self.header_items[row_index]
        self._editor.start_edit(
            row_index,
            item,
            self._layout_calc.text_top_viewport_y(row_index),
            self.viewport().width(),
            self._char_height,
        )

    def _handle_selection(self, row, modifiers):
        item_count = len(self.header_items)
        if item_count == 0:
            return
        changed = self._selection_handler.handle_click(row, modifiers, item_count)
        self.apply_selection_to_items(changed)
        self._on_selection_changed(self._selection.selected_rows())

    def _clear_selection(self):
        changed = self._selection_handler.clear()
        self.apply_selection_to_items(changed)
        self._on_selection_changed(self._selection.selected_rows())

    def _on_edit_committed(self, row_index, new_text):
        pass

    def _on_row_move_requested(self, from_index, to_index):
        pass

    def _on_selection_changed(self, selected_rows):
        pass

    def _on_rows_delete_requested(self, rows):
        pass

    def mousePressEvent(self, event):
        click_action = mouse_binding_manager.resolve_header_click(event.modifiers(), event.button())
        if click_action == MouseAction.NONE:
            super().mousePressEvent(event)
            return

        row = self._layout_calc.row_at_viewport_y(event.pos().y())
        if self._editor.is_editing() and not self._editor.is_editing(row):
            self._editor.commit_edit()

        if 0 <= row < len(self.header_items):
            self._drag.begin_press(event.pos(), row)
            self._handle_selection(row, event.modifiers())
        else:
            self._clear_selection()
        self.setFocus()
        event.accept()

    def mouseMoveEvent(self, event):
        if self._drag.handle_move(event):
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() != Qt.LeftButton:
            super().mouseReleaseEvent(event)
            return

        reorder = self._drag.handle_release()
        if reorder is not None:
            from_index, to_index = reorder
            self._on_row_move_requested(from_index, to_index)
        else:
            self._drag.clear_press()
        event.accept()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            row = self._layout_calc.row_at_viewport_y(event.pos().y())
            if 0 <= row < len(self.header_items):
                self._drag.clear_press()
                self._start_edit(row)
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def keyPressEvent(self, event):
        key = event.key()
        ctrl = bool(event.modifiers() & Qt.ControlModifier)
        item_count = len(self.header_items)

        if ctrl and key == Qt.Key_A:
            changed = self._selection_handler.select_all(item_count)
            self.apply_selection_to_items(changed)
            self._on_selection_changed(self._selection.selected_rows())
            event.accept()
            return

        if key == Qt.Key_Escape:
            if self._editor.is_editing():
                self._editor.cancel_edit()
            else:
                self._clear_selection()
            event.accept()
            return

        if key in (Qt.Key_Delete, Qt.Key_Backspace):
            rows = self._selection.selected_rows()
            if rows:
                self._on_rows_delete_requested(rows)
            event.accept()
            return

        super().keyPressEvent(event)

    def drawForeground(self, painter, rect):
        super().drawForeground(painter, rect)
        self._drag.draw_drop_indicator(painter)
