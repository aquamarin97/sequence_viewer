# features/navigation_ruler/navigation_ruler_model.py
from dataclasses import dataclass
from typing import List, Sequence, Optional
import math

@dataclass
class NavigationTickLayout:
    max_len: int; tick_step: int; major_ticks: List[int]; minor_ticks: List[int]

class NavigationRulerModel:
    def __init__(self): self._cached_max_len = 0; self._last_seq_count = 0
    @property
    def cached_max_len(self): return self._cached_max_len

    def recompute_max_len_if_needed(self, sequence_items):
        seq_count = len(sequence_items)
        new_max_len = max((len(getattr(it,"sequence","")) for it in sequence_items), default=0)
        if seq_count != self._last_seq_count or new_max_len != self._cached_max_len:
            self._last_seq_count = seq_count; self._cached_max_len = new_max_len
        return self._cached_max_len

    def compute_tick_layout(self, pixel_width, target_px=60):
        max_nt = self._cached_max_len
        if max_nt <= 0 or pixel_width <= 0: return None
        step = self._nice_tick_step(max_nt, pixel_width, target_px)
        minor_step = max(step//5, 1)
        minor_ticks = list(range(0, max_nt+1, minor_step))
        major_ticks = list(range(0, max_nt+1, step))
        if major_ticks:
            delta = max_nt - major_ticks[-1]
            if delta != 0:
                if delta < step*0.5: major_ticks[-1] = max_nt
                else: major_ticks.append(max_nt)
        return NavigationTickLayout(max_len=max_nt, tick_step=step, major_ticks=major_ticks, minor_ticks=minor_ticks)

    def format_label(self, value):
        if value == 1: return "1"
        if self._cached_max_len > 1_000_000: return f"{int(round(value/1000))}K"
        return str(value)

    def x_to_nt(self, x, pixel_width):
        if self._cached_max_len <= 0 or pixel_width <= 0: return 0.0
        return min(max(x/float(pixel_width), 0.0), 1.0) * self._cached_max_len

    @staticmethod
    def _nice_tick_step(max_nt, pixel_width, target_px=60):
        if max_nt <= 0 or pixel_width <= 0: return max(max_nt, 1)
        raw = (max_nt*target_px)/float(pixel_width)
        if raw <= 0: return 1
        power = 10**int(math.floor(math.log10(raw)))
        base = raw/power
        nice = 1 if base <= 1 else 2 if base <= 2 else 5 if base <= 5 else 10
        return int(nice*power)


