from dataclasses import dataclass
from typing import Optional, List, Tuple
import math

@dataclass
class PositionRulerLayout:
    max_len: int
    first_pos: int
    last_pos: int
    visible_span: int
    step: int
    sel_start_pos: Optional[int]
    sel_end_pos: Optional[int]
    special_positions: List[int]

class PositionRulerModel:
    def __init__(self) -> None:
        self.max_sequence_length: int = 0
        self.view_left:  float = 0.0
        self.view_width: float = 0.0
        self.char_width: float = 1.0
        self.selection_cols: Optional[Tuple[int, int]] = None

    def set_state(self, *, max_len, view_left, view_width, char_width, selection_cols) -> None:
        self.max_sequence_length = max_len
        self.view_left   = max(view_left, 0.0)
        self.view_width  = max(view_width, 0.0)
        self.char_width  = max(char_width, 0.0)
        self.selection_cols = selection_cols

    def compute_layout(self) -> Optional[PositionRulerLayout]:
        max_len = self.max_sequence_length
        if max_len <= 0 or self.view_width <= 0 or self.char_width <= 0:
            return None
        first_col = max(0, int(math.floor(self.view_left / self.char_width)))
        last_col  = min(max_len, int(math.ceil((self.view_left + self.view_width) / self.char_width)))
        if last_col <= first_col: return None
        first_pos    = first_col + 1
        last_pos     = last_col
        visible_span = last_pos - first_pos + 1
        if visible_span <= 0: return None
        step = self._choose_step(self.char_width, visible_span)
        sel_start = sel_end = None
        if self.selection_cols is not None:
            s, e = self.selection_cols
            if s > e: s, e = e, s
            sel_start, sel_end = s + 1, e + 1
        specials: List[int] = []
        if sel_start is not None:
            specials.append(sel_start)
            if sel_end != sel_start: specials.append(sel_end)
        return PositionRulerLayout(max_len=max_len, first_pos=first_pos, last_pos=last_pos,
                                   visible_span=visible_span, step=step,
                                   sel_start_pos=sel_start, sel_end_pos=sel_end,
                                   special_positions=specials)

    def _choose_step(self, char_width, visible_span) -> int:
        if visible_span <= 0: return 1
        raw  = visible_span / 10.0
        if raw <= 1: return 1
        power = 10 ** int(math.floor(math.log10(raw)))
        base  = raw / power
        nice  = 1 if base <= 1.5 else 2 if base <= 3 else 5 if base <= 7 else 10
        cand  = int(nice * power)
        if visible_span >= 1_000_000: cand = self._nice_large(cand)
        elif visible_span >= 100_000: cand = max(cand, 10_000)
        elif visible_span <= 100:     cand = min(cand, 10)
        return max(cand, 1)

    @staticmethod
    def _nice_large(step) -> int:
        for threshold, value in [(200_000, 100_000), (500_000, 200_000),
                                  (1_000_000, 500_000), (2_000_000, 1_000_000),
                                  (5_000_000, 2_000_000)]:
            if step <= threshold: return value
        power = 10 ** int(math.log10(step))
        b = step // power
        return (2 if b <= 2 else 5 if b <= 5 else 10) * power