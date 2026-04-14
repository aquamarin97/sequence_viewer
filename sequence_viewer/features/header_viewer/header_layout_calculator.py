from __future__ import annotations

import math

from PyQt5.QtCore import QRectF


class HeaderLayoutCalculator:
    def __init__(self, view) -> None:
        self._view = view

    def row_at_viewport_y(self, y):
        scene_y = self._view.mapToScene(0, y).y()
        layout = self._view._row_layout
        if layout is not None and layout.row_count > 0:
            return layout.row_at_y(scene_y)
        stride = self._view._row_stride_uniform
        if stride <= 0:
            return 0
        return int(math.floor(scene_y / stride))

    def insert_pos_at_viewport_y(self, y):
        scene_y = self._view.mapToScene(0, y).y()
        layout = self._view._row_layout
        if layout is not None and layout.row_count > 0:
            return layout.insert_pos_at_y(scene_y)
        stride = self._view._row_stride_uniform
        if stride <= 0:
            return 0
        insert = int(round(scene_y / stride))
        return max(0, min(insert, len(self._view.header_items)))

    def item_viewport_rect(self, row_index):
        layout = self._view._row_layout
        if layout is not None and row_index < layout.row_count:
            y_start = float(layout.y_offsets[row_index])
            height = float(layout.row_strides[row_index])
        else:
            stride = self._view._row_stride_uniform
            y_start = float(row_index * stride)
            height = float(stride)
        scene_rect = QRectF(0, y_start, self._view.viewport().width(), height)
        top_left = self._view.mapFromScene(scene_rect.topLeft())
        bottom_right = self._view.mapFromScene(scene_rect.bottomRight())
        return QRectF(top_left, bottom_right)

    def text_top_viewport_y(self, row_index: int) -> float:
        layout = self._view._row_layout
        if layout is not None and row_index < layout.row_count:
            text_top_scene = float(
                layout.y_offsets[row_index] + layout.per_row_annot_heights[row_index]
            )
        else:
            text_top_scene = float(row_index * self._view._row_stride_uniform + self._view._annot_height)
        return float(self._view.mapFromScene(0, text_top_scene).y())
