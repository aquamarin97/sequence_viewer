# features/sequence_viewer/sequence_viewer_view.py
from __future__ import annotations
from typing import TYPE_CHECKING
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPainter
from PyQt5.QtWidgets import QGraphicsView, QGraphicsScene
from graphics.sequence_item.sequence_item import SequenceGraphicsItem
from settings.theme import theme_manager
from settings.display_settings_manager import display_settings_manager
from .sequence_viewer_zoom import ZoomMixin
from .sequence_viewer_overlay import OverlayMixin
from .sequence_viewer_interaction import InteractionMixin

if TYPE_CHECKING:
    from widgets.row_layout import RowLayout


class SequenceViewerView(ZoomMixin, OverlayMixin, InteractionMixin, QGraphicsView):
    def __init__(self, parent=None, *, char_width=12.0, char_height=18.0):
        super().__init__(parent)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.char_width = float(char_width)
        self.char_height = int(round(char_height))
        self._per_row_annot_h = 0
        self._row_layout = None
        self.trailing_padding_line_px = 80.0
        self.trailing_padding_text_px = 30.0
        self.max_sequence_length = 0
        self.sequence_items = []
        self._controller = None

        # Mixin state
        self._init_zoom()
        self._init_overlay()

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

    # ------------------------------------------------------------------
    # Theme
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Row layout
    # ------------------------------------------------------------------

    def apply_row_layout(self, layout):
        self._row_layout = layout
        self._per_row_annot_h = 0
        self._reposition_items()
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
        if layout is not None:
            for i, item in enumerate(self.sequence_items):
                if i < layout.row_count:
                    item.setPos(0, float(layout.seq_y_offsets[i]))
        else:
            stride = self._per_row_annot_h + self.char_height
            for i, item in enumerate(self.sequence_items):
                item.setPos(0, float(i * stride + self._per_row_annot_h))

    # ------------------------------------------------------------------
    # Controller
    # ------------------------------------------------------------------

    def set_controller(self, controller):
        self._controller = controller

    # ------------------------------------------------------------------
    # Sequence items
    # ------------------------------------------------------------------

    def add_sequence_item(self, sequence_string):
        row_index = len(self.sequence_items)
        item = SequenceGraphicsItem(
            sequence=sequence_string,
            char_width=self.char_width,
            char_height=self.char_height,
            row_index=row_index,
        )
        layout = self._row_layout
        if layout is not None and row_index < layout.row_count:
            y = float(layout.seq_y_offsets[row_index])
        else:
            y = float(row_index * (self._per_row_annot_h + self.char_height) + self._per_row_annot_h)
        item.setPos(0, y)
        item.set_row_highlighted(row_index in self._h_guide_rows)
        self.scene.addItem(item)
        self.sequence_items.append(item)
        self._update_scene_rect()
        return item

    def clear_items(self):
        self.sequence_items.clear()
        self.scene.clear()
        self.max_sequence_length = 0
        self._row_layout = None
        self._selection_dim_ranges = []
        self.scene.setSceneRect(0, 0, 0, 0)
        self.scene.invalidate()

    def clear_visual_selection(self):
        for item in self.sequence_items:
            item.clear_selection()
        self.scene.invalidate()
        self.viewport().update()

    def set_visual_selection(self, row_start, row_end, col_start, col_end):
        for i, item in enumerate(self.sequence_items):
            if row_start <= i <= row_end and col_start >= 0 and col_end >= 0:
                item.set_selection(col_start, col_end)
            else:
                item.clear_selection()
        self.scene.invalidate()
        self.viewport().update()

    # ------------------------------------------------------------------
    # Scene rect
    # ------------------------------------------------------------------

    def _update_scene_rect(self):
        if not self.sequence_items:
            self.scene.setSceneRect(0, 0, 0, 0)
            self.max_sequence_length = 0
            return
        max_len = max(len(item.sequence) for item in self.sequence_items)
        self.max_sequence_length = max_len
        trailing = self._current_trailing_padding()
        width = max_len * self.char_width + trailing
        layout = self._row_layout
        if layout is not None and layout.row_count > 0:
            height = float(layout.total_height)
        else:
            stride = self._per_row_annot_h + self.char_height
            height = float(len(self.sequence_items) * stride)
        self.scene.setSceneRect(0, 0, width, height)
        self.scene.invalidate()

    # ------------------------------------------------------------------
    # Coordinate conversion
    # ------------------------------------------------------------------

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
