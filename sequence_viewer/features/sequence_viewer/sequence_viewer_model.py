# sequence_viewer/features/sequence_viewer/sequence_viewer_model.py
# features/sequence_viewer/sequence_viewer_model.py
from typing import List, Optional, Tuple

class SequenceViewerModel:
    def __init__(self):
        self._sequences = []
        self.max_sequence_length = 0
        self.selection_start_row = None
        self.selection_start_col = None
        self.current_selection_cols = None

    def add_sequence(self, sequence):
        self._sequences.append(sequence)
        if len(sequence) > self.max_sequence_length:
            self.max_sequence_length = len(sequence)
        return len(self._sequences) - 1

    def clear_sequences(self):
        self._sequences.clear(); self.max_sequence_length = 0; self.clear_selection()

    def recalc_max_sequence_length(self):
        self.max_sequence_length = max((len(s) for s in self._sequences), default=0)
        return self.max_sequence_length

    def get_sequences(self): return list(self._sequences)
    def get_row_count(self): return len(self._sequences)
    def get_sequence(self, row_index): return self._sequences[row_index]

    def clear_selection(self):
        self.selection_start_row = None; self.selection_start_col = None; self.current_selection_cols = None

    def start_selection(self, row, col):
        if self.get_row_count() == 0: self.clear_selection(); return False
        if row < 0 or row >= self.get_row_count() or col < 0: self.clear_selection(); return False
        self.selection_start_row = row; self.selection_start_col = col; return True

    def update_selection(self, current_row, current_col):
        if self.selection_start_row is None or self.selection_start_col is None: return None
        clamped_start = self._clamp_column_index(self.selection_start_col)
        clamped_current = self._clamp_column_index(current_col)
        if clamped_start is None or clamped_current is None: self.clear_selection(); return None
        row_count = self.get_row_count()
        if row_count == 0: self.clear_selection(); return None
        row_start = max(0, min(self.selection_start_row, current_row))
        row_end = min(row_count - 1, max(self.selection_start_row, current_row))
        col_start = min(clamped_start, clamped_current)
        col_end = max(clamped_start, clamped_current)
        if col_start >= 0 and col_end >= 0: self.current_selection_cols = (col_start, col_end)
        else: self.current_selection_cols = None
        return row_start, row_end, col_start, col_end

    def get_selection_column_range(self): return self.current_selection_cols

    def get_selection_center_nt(self):
        if self.current_selection_cols is None or self.max_sequence_length <= 0: return None
        s, e = self.current_selection_cols
        if s > e: s, e = e, s
        center_nt = (s + e + 1) / 2.0
        return max(0.0, min(center_nt, float(self.max_sequence_length)))

    def _clamp_column_index(self, col):
        if self.max_sequence_length <= 0: return None
        return max(0, min(col, self.max_sequence_length - 1))


