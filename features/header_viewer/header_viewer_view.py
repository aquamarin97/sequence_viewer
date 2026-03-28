# features/header_viewer/header_viewer_view.py

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
_DROP_LINE_WIDTH   = 2


class HeaderViewerView(QGraphicsView):
    """
    Header satırlarını çizen view — Adım 2.

    Değişiklik
    ----------
    apply_row_layout(layout)  — per-row değişken yükseklik.
    set_annot_height(h)       — geriye dönük shim (uniform yükseklik).
    """

    def __init__(
        self,
        parent=None,
        *,
        row_height: float = 18.0,
        initial_width: float = 160.0,
    ) -> None:
        super().__init__(parent)

        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)

        self._char_height:  int   = int(round(row_height))
        self._annot_height: int   = 0       # uniform shim
        self._row_layout: Optional["RowLayout"] = None

        self.row_height:   int   = self._char_height
        self.header_width: float = float(initial_width)

        self.header_items: List[HeaderRowItem] = []

        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.setMinimumWidth(60)
        self.setMaximumWidth(400)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)

        self._selection = RowSelectionModel()

        self._edit_widget: Optional[QLineEdit] = None
        self._editing_row: Optional[int]       = None

        self._press_pos:       Optional[QPoint] = None
        self._drag_source_row: Optional[int]    = None
        self._drag_insert_pos: Optional[int]    = None
        self._dragging:        bool             = False

        theme_manager.themeChanged.connect(self._on_theme_changed)

    # ------------------------------------------------------------------
    # Layout API — yeni
    # ------------------------------------------------------------------

    def apply_row_layout(self, layout: "RowLayout") -> None:
        """
        Per-row değişken yükseklik uygular.
        Workspace her annotation değişiminde çağırır.
        """
        self._row_layout   = layout
        self._annot_height = 0

        for i, item in enumerate(self.header_items):
            if i < layout.row_count:
                item.set_annot_height(layout.per_row_annot_heights[i])
                item.setPos(0, float(layout.y_offsets[i]))

        self._update_scene_rect()

    # ------------------------------------------------------------------
    # Layout API — geriye dönük shim
    # ------------------------------------------------------------------

    def set_annot_height(self, h: int) -> None:
        """Uniform annotation yüksekliği (shim). Layout varken yoksayılır."""
        if self._row_layout is not None:
            return
        if self._annot_height == h:
            return
        self._annot_height = h
        self.row_height    = h + self._char_height

        stride = h + self._char_height
        for i, item in enumerate(self.header_items):
            item.set_annot_height(h)
            item.setPos(0, float(i * stride))

        self._update_scene_rect()

    @property
    def _row_stride_uniform(self) -> int:
        return self._annot_height + self._char_height

    # ------------------------------------------------------------------
    # Row index ↔ Y  (variable stride destekli)
    # ------------------------------------------------------------------

    def _row_at_viewport_y(self, y: int) -> int:
        scene_y = self.mapToScene(0, y).y()
        layout  = self._row_layout
        if layout is not None and layout.row_count > 0:
            return layout.row_at_y(scene_y)
        stride = self._row_stride_uniform
        if stride <= 0:
            return 0
        return int(math.floor(scene_y / stride))

    def _insert_pos_at_viewport_y(self, y: int) -> int:
        scene_y = self.mapToScene(0, y).y()
        layout  = self._row_layout
        if layout is not None and layout.row_count > 0:
            return layout.insert_pos_at_y(scene_y)
        stride = self._row_stride_uniform
        if stride <= 0:
            return 0
        insert = int(round(scene_y / stride))
        return max(0, min(insert, len(self.header_items)))

    def _item_viewport_rect(self, row_index: int) -> QRectF:
        layout = self._row_layout
        if layout is not None and row_index < layout.row_count:
            y_start = float(layout.y_offsets[row_index])
            height  = float(layout.row_strides[row_index])
        else:
            stride  = self._row_stride_uniform
            y_start = float(row_index * stride)
            height  = float(stride)
        scene_rect = QRectF(0, y_start, self.viewport().width(), height)
        tl = self.mapFromScene(scene_rect.topLeft())
        br = self.mapFromScene(scene_rect.bottomRight())
        return QRectF(tl, br)

    # ------------------------------------------------------------------
    # Public API: item yönetimi
    # ------------------------------------------------------------------

    def add_header_item(self, display_text: str) -> HeaderRowItem:
        row_index  = len(self.header_items)
        item_width = self.viewport().width() or self.header_width

        layout = self._row_layout
        if layout is not None and row_index < layout.row_count:
            ann_h   = layout.per_row_annot_heights[row_index]
            y_start = float(layout.y_offsets[row_index])
        else:
            ann_h   = self._annot_height
            stride  = self._row_stride_uniform
            y_start = float(row_index * stride)

        item = HeaderRowItem(
            text=display_text,
            width=item_width,
            row_height=self._char_height,
            annot_height=ann_h,
            row_index=row_index,
        )
        item.setPos(0, y_start)
        self.scene.addItem(item)
        self.header_items.append(item)
        self._update_scene_rect()
        return item

    def clear_items(self) -> None:
        self._cancel_edit()
        self._reset_drag_state()
        self.header_items.clear()
        self.scene.clear()
        self._row_layout = None
        self._update_scene_rect()

    def apply_selection_to_items(self, changed_rows: FrozenSet[int]) -> None:
        for row in changed_rows:
            if 0 <= row < len(self.header_items):
                self.header_items[row].set_selected(
                    self._selection.is_selected(row)
                )

    # ------------------------------------------------------------------
    # Geometri
    # ------------------------------------------------------------------

    def _update_scene_rect(self) -> None:
        layout = self._row_layout
        if layout is not None and layout.row_count > 0:
            height = float(layout.total_height)
        else:
            height = float(len(self.header_items) * self._row_stride_uniform)
        width = self.viewport().width() or self.header_width
        self.scene.setSceneRect(0, 0, float(width), height)

    def compute_required_width(self) -> int:
        if not self.header_items:
            return 100
        metrics = QFontMetrics(self.header_items[0].font)
        max_px  = max(
            metrics.horizontalAdvance(item.full_text)
            for item in self.header_items
        )
        return max_px + 6 + 4 + 4

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        w = self.viewport().width()
        for item in self.header_items:
            item.set_width(w)
        self._update_scene_rect()
        required = self.compute_required_width() if self.header_items else 10
        self.setMaximumWidth(required if w >= required else 16_777_215)

    def _on_theme_changed(self, _theme) -> None:
        self.viewport().update()

    # ------------------------------------------------------------------
    # Inline edit
    # ------------------------------------------------------------------

    def _start_edit(self, row_index: int) -> None:
        if row_index < 0 or row_index >= len(self.header_items):
            return
        self._cancel_edit()

        item    = self.header_items[row_index]
        layout  = self._row_layout
        if layout is not None and row_index < layout.row_count:
            text_top_scene = float(layout.y_offsets[row_index]
                                   + layout.per_row_annot_heights[row_index])
        else:
            text_top_scene = float(row_index * self._row_stride_uniform
                                   + self._annot_height)
        vp_top = self.mapFromScene(0, text_top_scene).y()

        t      = theme_manager.current
        editor = QLineEdit(self.viewport())

        full_text  = item.full_text
        raw_header = full_text.split(". ", 1)[1] if ". " in full_text else full_text
        editor.setText(raw_header)
        editor.selectAll()

        margin = 2
        vp_w   = self.viewport().width()
        editor.setGeometry(
            margin, int(vp_top) + margin,
            vp_w - margin * 2,
            self._char_height - margin * 2,
        )
        editor.setStyleSheet(
            f"QLineEdit {{"
            f"  background: {t.editor_bg};"
            f"  border: 1.5px solid {t.editor_border};"
            f"  border-radius: 2px;"
            f"  padding: 0px 4px;"
            f"  font-family: Arial;"
            f"  font-size: {int(item._model.compute_font_point_size())}pt;"
            f"}}"
        )
        editor.show()
        editor.setFocus()
        editor.returnPressed.connect(lambda: self._commit_edit(row_index))
        editor.editingFinished.connect(lambda: self._commit_edit(row_index))

        self._edit_widget = editor
        self._editing_row = row_index
        item.set_hovered(True)

    def _commit_edit(self, row_index: int) -> None:
        if self._edit_widget is None or self._editing_row != row_index:
            return
        new_text = self._edit_widget.text().strip()
        self._cancel_edit()
        if not new_text:
            return
        self._on_edit_committed(row_index, new_text)

    def _cancel_edit(self) -> None:
        widget = self._edit_widget
        self._edit_widget = None
        if widget is not None:
            widget.blockSignals(True)
            widget.hide()
            widget.deleteLater()
        if self._editing_row is not None:
            idx = self._editing_row
            self._editing_row = None
            if 0 <= idx < len(self.header_items):
                self.header_items[idx].set_hovered(False)

    # ------------------------------------------------------------------
    # Drag & drop
    # ------------------------------------------------------------------

    def _reset_drag_state(self) -> None:
        if self._drag_source_row is not None:
            idx = self._drag_source_row
            if 0 <= idx < len(self.header_items):
                self.header_items[idx].set_dragging(False)
        self._drag_source_row = None
        self._drag_insert_pos = None
        self._dragging        = False
        self._press_pos       = None
        self.viewport().update()

    def _update_drag(self, vp_pos: QPoint) -> None:
        self._drag_insert_pos = self._insert_pos_at_viewport_y(vp_pos.y())
        self.viewport().update()

    # ------------------------------------------------------------------
    # Seçim
    # ------------------------------------------------------------------

    def _handle_selection(self, row: int, modifiers) -> None:
        n = len(self.header_items)
        if n == 0:
            return
        ctrl  = bool(modifiers & Qt.ControlModifier)
        shift = bool(modifiers & Qt.ShiftModifier)
        if ctrl and shift:
            changed = self._selection.handle_shift_click(row, n)
        elif ctrl:
            changed = self._selection.handle_ctrl_click(row, n)
        elif shift:
            changed = self._selection.handle_shift_click(row, n)
        else:
            changed = self._selection.handle_click(row, n)
        self.apply_selection_to_items(changed)
        self._on_selection_changed(self._selection.selected_rows())

    # ------------------------------------------------------------------
    # Hook'lar
    # ------------------------------------------------------------------

    def _on_edit_committed(self, row_index: int, new_text: str) -> None:
        pass

    def _on_row_move_requested(self, from_index: int, to_index: int) -> None:
        pass

    def _on_selection_changed(self, selected_rows: FrozenSet[int]) -> None:
        pass

    def _on_rows_delete_requested(self, rows: FrozenSet[int]) -> None:
        pass

    # ------------------------------------------------------------------
    # Mouse
    # ------------------------------------------------------------------

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            row = self._row_at_viewport_y(event.pos().y())
            if self._editing_row is not None and self._editing_row != row:
                self._commit_edit(self._editing_row)
            if 0 <= row < len(self.header_items):
                self._press_pos       = event.pos()
                self._drag_source_row = row
                self._handle_selection(row, event.modifiers())
            else:
                changed = self._selection.clear()
                self.apply_selection_to_items(changed)
                self._on_selection_changed(self._selection.selected_rows())
            self.setFocus()
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if (
            event.buttons() & Qt.LeftButton
            and self._press_pos is not None
            and self._drag_source_row is not None
        ):
            delta = (event.pos() - self._press_pos).manhattanLength()
            if not self._dragging and delta >= _DRAG_THRESHOLD_PX:
                self._dragging = True
                self.header_items[self._drag_source_row].set_dragging(True)
                self.viewport().setCursor(Qt.SizeVerCursor)
            if self._dragging:
                self._update_drag(event.pos())
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            if self._dragging and self._drag_source_row is not None:
                src    = self._drag_source_row
                insert = self._drag_insert_pos if self._drag_insert_pos is not None else src
                to_idx = insert if insert <= src else insert - 1
                self._reset_drag_state()
                self.viewport().unsetCursor()
                if to_idx != src:
                    self._on_row_move_requested(src, to_idx)
            else:
                self._press_pos       = None
                self._drag_source_row = None
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            row = self._row_at_viewport_y(event.pos().y())
            if 0 <= row < len(self.header_items):
                self._press_pos       = None
                self._drag_source_row = None
                self._start_edit(row)
            event.accept()
        else:
            super().mouseDoubleClickEvent(event)

    # ------------------------------------------------------------------
    # Klavye
    # ------------------------------------------------------------------

    def keyPressEvent(self, event) -> None:
        key  = event.key()
        ctrl = bool(event.modifiers() & Qt.ControlModifier)
        n    = len(self.header_items)

        if ctrl and key == Qt.Key_A:
            changed = self._selection.select_all(n)
            self.apply_selection_to_items(changed)
            self._on_selection_changed(self._selection.selected_rows())
            event.accept()
        elif key == Qt.Key_Escape:
            if self._edit_widget is not None:
                self._cancel_edit()
            else:
                changed = self._selection.clear()
                self.apply_selection_to_items(changed)
                self._on_selection_changed(self._selection.selected_rows())
            event.accept()
        elif key in (Qt.Key_Delete, Qt.Key_Backspace):
            rows = self._selection.selected_rows()
            if rows:
                self._on_rows_delete_requested(rows)
            event.accept()
        else:
            super().keyPressEvent(event)

    # ------------------------------------------------------------------
    # Drop indicator
    # ------------------------------------------------------------------

    def drawForeground(self, painter: QPainter, rect: QRectF) -> None:
        super().drawForeground(painter, rect)
        if not self._dragging or self._drag_insert_pos is None:
            return

        layout = self._row_layout
        if layout is not None and self._drag_insert_pos <= layout.row_count:
            if self._drag_insert_pos < layout.row_count:
                insert_y_scene = float(layout.y_offsets[self._drag_insert_pos])
            else:
                insert_y_scene = float(layout.total_height)
        else:
            stride         = self._row_stride_uniform
            insert_y_scene = float(self._drag_insert_pos * stride)

        vp_y     = self.mapFromScene(0, insert_y_scene).y()
        vp_width = self.viewport().width()
        t        = theme_manager.current

        painter.save()
        painter.resetTransform()
        pen = QPen(t.drop_indicator, _DROP_LINE_WIDTH)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawLine(8, vp_y, vp_width - 4, vp_y)
        from PyQt5.QtGui import QBrush as _B
        r = 4
        painter.setBrush(_B(t.drop_indicator))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(4, vp_y - r, r * 2, r * 2)
        painter.restore()