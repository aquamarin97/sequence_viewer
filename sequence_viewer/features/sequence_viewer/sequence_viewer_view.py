# sequence_viewer/features/sequence_viewer/sequence_viewer_view.py
from __future__ import annotations
from typing import TYPE_CHECKING
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPainter
from PyQt5.QtWidgets import QGraphicsView, QGraphicsScene
from sequence_viewer.graphics.sequence_item.sequence_item import SequenceGraphicsItem
from settings.sequence_viewer.theme import theme_manager
from settings.sequence_viewer.display_settings_manager import display_settings_manager
from .sequence_viewer_zoom import ZoomMixin
from .sequence_viewer_overlay import OverlayMixin
from .sequence_viewer_interaction import InteractionMixin
from .sequence_viewer_scroll_inertia import ScrollInertiaMixin

if TYPE_CHECKING:
    from sequence_viewer.workspace.row_layout import RowLayout


def _remap_row(row: int, from_idx: int, to_idx: int) -> int:
    if row == from_idx:
        return to_idx
    if from_idx < to_idx:
        if from_idx < row <= to_idx:
            return row - 1
    elif to_idx <= row < from_idx:
        return row + 1
    return row


class SequenceViewerView(ZoomMixin, OverlayMixin, InteractionMixin, ScrollInertiaMixin, QGraphicsView):
    _POOL_BUFFER: int = 8

    def __init__(self, parent=None, *, char_width=12.0, char_height=18.0):
        super().__init__(parent)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.char_width = float(char_width)
        self._base_char_width = float(char_width)
        self.char_height = int(round(char_height))
        self._per_row_annot_h = 0
        self._row_layout = None
        self.trailing_padding_line_px = 80.0
        self.trailing_padding_text_px = 30.0
        self.max_sequence_length = 0
        self.sequence_items: list[SequenceGraphicsItem] = []   # item pool
        self._total_row_count: int = 0
        self._pool_first_row: int = 0
        self._selection_range = None    # (row_s, row_e, col_s, col_e) or None
        self._controller = None

        self._init_zoom()
        self._init_overlay()
        self._init_scroll_inertia()

        self.setRenderHint(QPainter.Antialiasing, False)
        self.setRenderHint(QPainter.TextAntialiasing, True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setDragMode(QGraphicsView.NoDrag)
        self.setMouseTracking(True)
        self.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        from PyQt5.QtWidgets import QFrame
        self.setFrameShape(QFrame.NoFrame)

        self.viewport().setCursor(Qt.IBeamCursor)
        theme_manager.themeChanged.connect(self._on_theme_changed)
        display_settings_manager.displaySettingsChanged.connect(self._on_display_settings_changed)
        self._apply_scene_background()

    # ── Theme ──────────────────────────────────────────────────────────────

    def _apply_scene_background(self):
        from PyQt5.QtGui import QBrush
        self.scene.setBackgroundBrush(QBrush(theme_manager.current.seq_bg))

    def _on_theme_changed(self, _theme):
        self._apply_scene_background()
        self.scene.invalidate()
        self.viewport().update()

    def _on_display_settings_changed(self):
        new_ch = display_settings_manager.sequence_char_height
        self.char_height = new_ch
        for item in self.sequence_items:
            item.refresh_display_settings()
        self._reposition_items()
        self._update_scene_rect()
        self.scene.invalidate()
        self.viewport().update()

    # ── Row layout ─────────────────────────────────────────────────────────

    def apply_row_layout(self, layout):
        self._row_layout = layout
        self._per_row_annot_h = 0
        self._full_pool_remount()
        self._update_scene_rect()

    @property
    def row_stride(self):
        if self._row_layout and self._row_layout.row_count > 0:
            return self._row_layout.row_strides[0]
        return self._per_row_annot_h + self.char_height

    def set_per_row_annot_height(self, h):
        if self._row_layout is not None:
            return
        if self._per_row_annot_h == h:
            return
        self._per_row_annot_h = h
        self._reposition_items()
        self._update_scene_rect()

    def _reposition_items(self):
        layout = self._row_layout
        for item in self.sequence_items:
            if not item.isVisible():
                continue
            row_idx = item.row_index
            if layout is not None and row_idx < layout.row_count:
                item.setPos(0, float(layout.seq_y_offsets[row_idx]))
            else:
                stride = self._per_row_annot_h + self.char_height
                item.setPos(0, float(row_idx * stride + self._per_row_annot_h))

    # ── Controller ─────────────────────────────────────────────────────────

    def set_controller(self, controller):
        self._controller = controller

    # ── Pool internals ─────────────────────────────────────────────────────

    def _desired_pool_window(self) -> tuple[int, int]:
        if self._total_row_count == 0:
            return 0, -1
        scroll_y = float(self.verticalScrollBar().value())
        vp_h = float(max(1, self.viewport().height()))
        layout = self._row_layout
        if layout is not None and layout.row_count > 0:
            vis_first = layout.row_at_y(scroll_y)
            vis_last = layout.row_at_y(scroll_y + vp_h)
        else:
            stride = max(1, self._per_row_annot_h + self.char_height)
            vis_first = int(scroll_y / stride)
            vis_last = int((scroll_y + vp_h) / stride)
        first = max(0, vis_first - self._POOL_BUFFER)
        last = min(self._total_row_count - 1, vis_last + self._POOL_BUFFER)
        return first, last

    def _y_for_row(self, row_idx: int) -> float:
        layout = self._row_layout
        if layout is not None and row_idx < layout.row_count:
            return float(layout.seq_y_offsets[row_idx])
        stride = self._per_row_annot_h + self.char_height
        return float(row_idx * stride + self._per_row_annot_h)

    def _get_sequence_for_row(self, row_idx: int) -> str:
        return ''

    def _ensure_pool_size(self, needed: int) -> None:
        while len(self.sequence_items) < needed:
            item = SequenceGraphicsItem(
                sequence='',
                char_width=self.char_width,
                char_height=self.char_height,
                row_index=0,
                base_char_width=self._base_char_width,
            )
            item.setVisible(False)
            self.scene.addItem(item)
            self.sequence_items.append(item)

    def _mount_item(self, item: SequenceGraphicsItem, row_idx: int) -> None:
        if row_idx < 0 or row_idx >= self._total_row_count:
            item.setVisible(False)
            return
        seq = self._get_sequence_for_row(row_idx)
        item.prepareGeometryChange()
        item._model.sequence = seq
        item._model.length = len(seq)
        item.row_index = row_idx
        item.setPos(0, self._y_for_row(row_idx))
        item.setVisible(True)
        item.set_row_highlighted(row_idx in self._h_guide_rows)
        sel = self._selection_range
        if sel and sel[0] <= row_idx <= sel[1] and sel[2] >= 0 and sel[3] >= 0:
            item._model.set_selection(sel[2], sel[3])
        else:
            item._model.clear_selection()
        item.update()

    def _sync_pool(self) -> None:
        if self._total_row_count == 0:
            return
        first, last = self._desired_pool_window()
        if last < first:
            return
        needed = last - first + 1
        self._ensure_pool_size(needed)
        desired: set[int] = set(range(first, last + 1))
        mounted: dict[int, SequenceGraphicsItem] = {}
        free: list[SequenceGraphicsItem] = []
        for item in self.sequence_items:
            r = item.row_index
            if item.isVisible() and 0 <= r < self._total_row_count and r in desired:
                mounted[r] = item
            else:
                free.append(item)
        for row in sorted(desired - set(mounted.keys())):
            if not free:
                break
            self._mount_item(free.pop(), row)
        self._pool_first_row = first

    def _full_pool_remount(self) -> None:
        if self._total_row_count == 0:
            for item in self.sequence_items:
                item.setVisible(False)
            return
        first, last = self._desired_pool_window()
        needed = max(last - first + 1, 0)
        self._ensure_pool_size(needed)
        for i, item in enumerate(self.sequence_items):
            row_idx = first + i
            if row_idx <= last:
                self._mount_item(item, row_idx)
            else:
                item.setVisible(False)
        self._pool_first_row = first

    # ── Sequence items (public API) ────────────────────────────────────────

    def add_sequence_item(self, sequence_string: str) -> None:
        self._total_row_count += 1
        seq_len = len(sequence_string)
        if seq_len > self.max_sequence_length:
            self.max_sequence_length = seq_len
        row_idx = self._total_row_count - 1
        _, last = self._desired_pool_window()
        if row_idx <= last:
            self._ensure_pool_size(len(self.sequence_items) + 1)
            self._mount_item(self.sequence_items[-1], row_idx)
        self._update_scene_rect(invalidate=False)

    def clear_items(self):
        self.sequence_items.clear()
        self.scene.clear()
        self._total_row_count = 0
        self._pool_first_row = 0
        self._selection_range = None
        self.max_sequence_length = 0
        self._row_layout = None
        self._selection_dim_ranges = []
        self.scene.setSceneRect(0, 0, 0, 0)
        self.scene.invalidate()

    def clear_visual_selection(self):
        self._selection_range = None
        for item in self.sequence_items:
            item._model.clear_selection()
            item.update()
        self.scene.invalidate()
        self.viewport().update()

    def remap_visual_selection(self, from_index: int, to_index: int) -> None:
        """Remap _selection_range row indices after a row move, before pool remount."""
        sel = self._selection_range
        if sel is None:
            return
        rs, re, cs, ce = sel
        self._selection_range = (
            _remap_row(rs, from_index, to_index),
            _remap_row(re, from_index, to_index),
            cs, ce,
        )

    def set_visual_selection(self, row_start, row_end, col_start, col_end):
        self._selection_range = (row_start, row_end, col_start, col_end)
        for item in self.sequence_items:
            if not item.isVisible():
                continue
            r = item.row_index
            if row_start <= r <= row_end and col_start >= 0 and col_end >= 0:
                item.set_selection(col_start, col_end)
            else:
                item._model.clear_selection()
                item.update()
        self.scene.invalidate()
        self.viewport().update()

    # ── Scene rect ─────────────────────────────────────────────────────────

    def _update_scene_rect(self, *, invalidate: bool = True):
        if self._total_row_count == 0:
            self.scene.setSceneRect(0, 0, 0, 0)
            self.max_sequence_length = 0
            if invalidate:
                self.scene.invalidate()
            return
        trailing = self._current_trailing_padding()
        width = self.max_sequence_length * self.char_width + trailing
        layout = self._row_layout
        if layout is not None and layout.row_count > 0:
            height = float(layout.total_height)
        else:
            stride = self._per_row_annot_h + self.char_height
            height = float(self._total_row_count * stride)
        self.scene.setSceneRect(0, 0, width, height)
        if invalidate:
            self.scene.invalidate()

    # ── Coordinate conversion ──────────────────────────────────────────────

    def scene_pos_to_row_col(self, scene_pos):
        layout = self._row_layout
        if layout is not None and layout.row_count > 0:
            raw_row = layout.row_at_y(scene_pos.y())
        else:
            stride = self._per_row_annot_h + self.char_height
            raw_row = int(scene_pos.y() // stride) if stride > 0 else 0
        cw = self._get_current_char_width()
        if cw <= 0:
            cw = max(self.char_width, 0.000001)
        col = int(scene_pos.x() // cw)
        return raw_row, col

    def selection_viewport_anchor(self, row_end: int, col_end: int):
        from PyQt5.QtCore import QPoint, QPointF
        cw = self._effective_char_width()
        scene_x = (col_end + 1) * cw
        layout = self._row_layout
        if layout is not None and 0 <= row_end < layout.row_count:
            scene_y = float(layout.seq_y_offsets[row_end]) + float(self.char_height)
        else:
            stride = self._per_row_annot_h + self.char_height
            scene_y = float(row_end * stride + self._per_row_annot_h + self.char_height)
        vp = self.mapFromScene(QPointF(scene_x, scene_y))
        return QPoint(int(vp.x()), int(vp.y()))

    # ── Scroll / resize overrides ──────────────────────────────────────────

    def scrollContentsBy(self, dx: int, dy: int) -> None:
        super().scrollContentsBy(dx, dy)
        if dy != 0:
            self._sync_pool()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._total_row_count > 0:
            self._sync_pool()
