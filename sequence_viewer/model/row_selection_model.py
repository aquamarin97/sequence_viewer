# model/row_selection_model.py
from __future__ import annotations
from typing import FrozenSet, Optional, Set

class RowSelectionModel:
    def __init__(self):
        self._selected: Set[int] = set()
        self._anchor: Optional[int] = None

    def is_selected(self, row): return row in self._selected
    def selected_rows(self): return frozenset(self._selected)
    def count(self): return len(self._selected)
    def is_empty(self): return not self._selected
    @property
    def anchor(self): return self._anchor

    def handle_click(self, row, row_count):
        changed = self._selected.symmetric_difference({row})
        self._selected = {row}
        self._anchor = row
        return frozenset(changed | {row})

    def handle_ctrl_click(self, row, row_count):
        if row in self._selected: self._selected.discard(row)
        else: self._selected.add(row)
        self._anchor = row
        return frozenset({row})

    def handle_shift_click(self, row, row_count):
        anchor = self._anchor if self._anchor is not None else row
        lo, hi = min(anchor, row), max(anchor, row)
        old = frozenset(self._selected)
        new_range = set(range(lo, hi + 1))
        self._selected = new_range
        return frozenset(old.symmetric_difference(new_range))

    def select_all(self, row_count):
        old = frozenset(self._selected)
        self._selected = set(range(row_count))
        self._anchor = 0 if row_count > 0 else None
        return frozenset(self._selected.symmetric_difference(old))

    def clear(self):
        changed = frozenset(self._selected)
        self._selected = set()
        self._anchor = None
        return changed

    def remove_row(self, removed_index):
        new_selected = set()
        for r in self._selected:
            if r < removed_index: new_selected.add(r)
            elif r > removed_index: new_selected.add(r - 1)
        self._selected = new_selected
        if self._anchor is not None:
            if self._anchor == removed_index: self._anchor = None
            elif self._anchor > removed_index: self._anchor -= 1

    def move_row(self, from_index, to_index):
        was_selected = from_index in self._selected
        new_selected = set()
        for r in self._selected:
            if r == from_index: continue
            new_selected.add(_shift_for_move(r, from_index, to_index))
        if was_selected: new_selected.add(to_index)
        self._selected = new_selected
        if self._anchor is not None:
            if self._anchor == from_index: self._anchor = to_index
            else: self._anchor = _shift_for_move(self._anchor, from_index, to_index)

def _shift_for_move(row, from_idx, to_idx):
    if from_idx < to_idx:
        if from_idx < row <= to_idx: return row - 1
    else:
        if to_idx <= row < from_idx: return row + 1
    return row


