from __future__ import annotations
import bisect
from dataclasses import dataclass, field
from typing import List

PAD_FAR = 10; PAD_NEAR = 0; LANE_GAP = 2

def _lane_h(lane_height):
    if lane_height is not None:
        return int(lane_height)
    from settings.annotation_styles import annotation_style_manager
    return annotation_style_manager.get_lane_height()

def strip_height(n_lanes, lane_height=None):
    if n_lanes == 0: return 0
    lh = _lane_h(lane_height)
    return PAD_FAR + n_lanes * lh + (n_lanes - 1) * LANE_GAP + PAD_NEAR

def above_lane_y(lane, lane_height=None):
    lh = _lane_h(lane_height)
    return PAD_FAR + lane * (lh + LANE_GAP)

def below_lane_y(lane, lane_height=None):
    lh = _lane_h(lane_height)
    return PAD_NEAR + lane * (lh + LANE_GAP)

@dataclass
class RowLayout:
    char_height: int
    per_row_above_heights: List[int]
    per_row_below_heights: List[int]
    row_strides: List[int] = field(default_factory=list)
    y_offsets: List[int] = field(default_factory=list)
    seq_y_offsets: List[int] = field(default_factory=list)
    below_y_offsets: List[int] = field(default_factory=list)
    total_height: int = 0

    @property
    def per_row_annot_heights(self): return self.per_row_above_heights

    @staticmethod
    def build(char_height, per_row_above_heights, per_row_below_heights):
        row_strides=[]; y_offsets=[]; seq_y_offsets=[]; below_y_offsets=[]; cum=0
        for above_h, below_h in zip(per_row_above_heights, per_row_below_heights):
            stride = above_h + char_height + below_h
            y_offsets.append(cum); seq_y_offsets.append(cum + above_h)
            below_y_offsets.append(cum + above_h + char_height)
            row_strides.append(stride); cum += stride
        return RowLayout(char_height=char_height, per_row_above_heights=per_row_above_heights,
            per_row_below_heights=per_row_below_heights, row_strides=row_strides,
            y_offsets=y_offsets, seq_y_offsets=seq_y_offsets, below_y_offsets=below_y_offsets, total_height=cum)

    @staticmethod
    def empty(char_height): return RowLayout(char_height=char_height, per_row_above_heights=[], per_row_below_heights=[])

    @property
    def row_count(self): return len(self.per_row_above_heights)

    def row_at_y(self, scene_y):
        if not self.y_offsets: return 0
        idx = bisect.bisect_right(self.y_offsets, scene_y) - 1
        return max(0, min(idx, self.row_count - 1))

    def y_in_row(self, scene_y, row):
        if row < 0 or row >= self.row_count: return 0.0
        return scene_y - self.y_offsets[row]

    def is_in_annot_strip(self, scene_y, row):
        if row < 0 or row >= self.row_count: return False
        local_y = self.y_in_row(scene_y, row)
        above_h = self.per_row_above_heights[row]
        below_start = above_h + self.char_height
        stride = self.row_strides[row]
        return (0.0 <= local_y < above_h) or (below_start <= local_y < stride)

    def insert_pos_at_y(self, scene_y):
        if not self.y_offsets: return 0
        midpoints = [self.y_offsets[i] + self.row_strides[i]/2.0 for i in range(self.row_count)]
        pos = bisect.bisect_left(midpoints, scene_y)
        return max(0, min(pos, self.row_count))
