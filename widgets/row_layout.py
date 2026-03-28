# widgets/row_layout.py
"""
Per-row değişken yükseklik hesabı.

Adım 2+ değişikliği
-------------------
Her satırın hem üst (above) hem alt (below) annotation şerit yükseklikleri
ayrı ayrı tutulur.

Satır geometrisi
----------------
    ┌─────────────────────────────────┐  ← y_offsets[i]
    │  above_ann  (primer / probe)    │  per_row_above_heights[i] px
    ├─────────────────────────────────┤  ← seq_y_offsets[i]
    │  sequence text                  │  char_height px
    ├─────────────────────────────────┤  ← below_y_offsets[i]
    │  below_ann  (region, vb.)       │  per_row_below_heights[i] px
    └─────────────────────────────────┘  stride = above + char + below

Padding kuralı
--------------
Annotation item'ları sequence'a YAKTAN az (_PAD_NEAR), uzak taraftan
fazla (_PAD_FAR) boşluk alır — bu sayede annotation görsel olarak
ait olduğu dizi satırına bağlı hissettiriri.

    _PAD_FAR  = 4 px   (üst annotation'da top, alt annotation'da bottom)
    _PAD_NEAR = 2 px   (üst annotation'da bottom, alt annotation'da top)
"""
from __future__ import annotations
import bisect
from dataclasses import dataclass, field
from typing import List

# Padding sabitleri — workspace ve header_item bu modülü import eder
PAD_FAR  = 10   # şerit → dış kenar
PAD_NEAR = 0   # şerit → sequence kenarı
LANE_GAP = 2   # lane'ler arası boşluk


def strip_height(n_lanes: int) -> int:
    """n_lanes lane'lik şerit için toplam piksel yüksekliği."""
    if n_lanes == 0:
        return 0
    return PAD_FAR + n_lanes * 16 + (n_lanes - 1) * LANE_GAP + PAD_NEAR


def above_lane_y(lane: int) -> int:
    """Üst şeritteki lane'in y ofseti (şerit içinde)."""
    return PAD_FAR + lane * (16 + LANE_GAP)


def below_lane_y(lane: int) -> int:
    """Alt şeritteki lane'in y ofseti (şerit içinde)."""
    return PAD_NEAR + lane * (16 + LANE_GAP)


@dataclass
class RowLayout:
    char_height:              int
    per_row_above_heights:    List[int]
    per_row_below_heights:    List[int]
    row_strides:              List[int]   = field(default_factory=list)
    y_offsets:                List[int]   = field(default_factory=list)
    seq_y_offsets:            List[int]   = field(default_factory=list)
    below_y_offsets:          List[int]   = field(default_factory=list)
    total_height:             int         = 0

    # Geriye dönük uyumluluk — header_viewer yalnızca üst şeridi okuyordu
    @property
    def per_row_annot_heights(self) -> List[int]:
        return self.per_row_above_heights

    @staticmethod
    def build(
        char_height: int,
        per_row_above_heights: List[int],
        per_row_below_heights: List[int],
    ) -> "RowLayout":
        row_strides:    List[int] = []
        y_offsets:      List[int] = []
        seq_y_offsets:  List[int] = []
        below_y_offsets: List[int] = []
        cum = 0
        for above_h, below_h in zip(per_row_above_heights, per_row_below_heights):
            stride = above_h + char_height + below_h
            y_offsets.append(cum)
            seq_y_offsets.append(cum + above_h)
            below_y_offsets.append(cum + above_h + char_height)
            row_strides.append(stride)
            cum += stride
        return RowLayout(
            char_height=char_height,
            per_row_above_heights=per_row_above_heights,
            per_row_below_heights=per_row_below_heights,
            row_strides=row_strides,
            y_offsets=y_offsets,
            seq_y_offsets=seq_y_offsets,
            below_y_offsets=below_y_offsets,
            total_height=cum,
        )

    @staticmethod
    def empty(char_height: int) -> "RowLayout":
        return RowLayout(
            char_height=char_height,
            per_row_above_heights=[],
            per_row_below_heights=[],
        )

    @property
    def row_count(self) -> int:
        return len(self.per_row_above_heights)

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
        """Hem üst hem alt annotation şeridini kapsayacak şekilde kontrol eder."""
        if row < 0 or row >= self.row_count:
            return False
        local_y = self.y_in_row(scene_y, row)
        above_h = self.per_row_above_heights[row]
        below_start = above_h + self.char_height
        stride = self.row_strides[row]
        # Üst şerit: [0, above_h)  veya  Alt şerit: [below_start, stride)
        return (0.0 <= local_y < above_h) or (below_start <= local_y < stride)

    def insert_pos_at_y(self, scene_y: float) -> int:
        if not self.y_offsets:
            return 0
        midpoints = [
            self.y_offsets[i] + self.row_strides[i] / 2.0
            for i in range(self.row_count)
        ]
        pos = bisect.bisect_left(midpoints, scene_y)
        return max(0, min(pos, self.row_count))