# widgets/row_layout.py
from __future__ import annotations
import bisect
from dataclasses import dataclass, field
from typing import List

@dataclass
class RowLayout:
    char_height:            int
    per_row_annot_heights:  List[int]
    row_strides:            List[int]  = field(default_factory=list)
    y_offsets:              List[int]  = field(default_factory=list)
    seq_y_offsets:          List[int]  = field(default_factory=list)
    total_height:           int        = 0

    @staticmethod
    def build(char_height: int, per_row_annot_heights: List[int]) -> "RowLayout":
        row_strides: List[int] = []
        y_offsets:   List[int] = []
        seq_y_offsets: List[int] = []
        cum = 0
        for ann_h in per_row_annot_heights:
            stride = ann_h + char_height
            y_offsets.append(cum)
            seq_y_offsets.append(cum + ann_h)
            row_strides.append(stride)
            cum += stride
        return RowLayout(
            char_height=char_height,
            per_row_annot_heights=per_row_annot_heights,
            row_strides=row_strides,
            y_offsets=y_offsets,
            seq_y_offsets=seq_y_offsets,
            total_height=cum,
        )

    @staticmethod
    def empty(char_height: int) -> "RowLayout":
        return RowLayout(char_height=char_height, per_row_annot_heights=[])

    @property
    def row_count(self) -> int:
        return len(self.per_row_annot_heights)

    def row_at_y(self, scene_y: float) -> int:
        if not self.y_offsets:
            return 0
        idx = bisect.bisect_right(self.y_offsets, scene_y) - 1
        return max(0, min(idx, self.row_count - 1))

    def y_in_row(self, scene_y: float, row: int) -> float:
        if row < 0 or row >= self.row_count:
            return 0.0
        return scene_y - self.y_offsets[row]

    def is_in_annot_strip(self, scene_y: float, row: int) -> bool:
        if row < 0 or row >= self.row_count:
            return False
        local_y = self.y_in_row(scene_y, row)
        return 0.0 <= local_y < self.per_row_annot_heights[row]

    def insert_pos_at_y(self, scene_y: float) -> int:
        if not self.y_offsets:
            return 0
        midpoints = [
            self.y_offsets[i] + self.row_strides[i] / 2.0
            for i in range(self.row_count)
        ]
        pos = bisect.bisect_left(midpoints, scene_y)
        return max(0, min(pos, self.row_count))