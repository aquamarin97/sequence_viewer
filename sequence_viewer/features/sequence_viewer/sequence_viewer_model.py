# sequence_viewer/features/sequence_viewer/sequence_viewer_model.py
# features/sequence_viewer/sequence_viewer_model.py
from typing import List, Optional, Tuple

class SequenceViewerModel:
    def __init__(self):
        self._sequences = []
        self._sequence_provider = None
        self._provider_row_count = 0
        self.max_sequence_length = 0
        self.selection_start_row = None
        self.selection_start_col = None
        self.current_selection_cols = None

    def _using_provider(self):
        return self._sequence_provider is not None

    def add_sequence(self, sequence):
        if self._using_provider():
            self._provider_row_count += 1
            if len(sequence) > self.max_sequence_length:
                self.max_sequence_length = len(sequence)
            return self._provider_row_count - 1
        self._sequences.append(sequence)
        if len(sequence) > self.max_sequence_length:
            self.max_sequence_length = len(sequence)
        return len(self._sequences) - 1

    def set_sequences(self, sequences):
        self._sequence_provider = None
        self._provider_row_count = 0
        self._sequences = list(sequences)
        self.recalc_max_sequence_length()
        self.clear_selection()

    def set_sequence_source(self, row_count, max_sequence_length, sequence_provider):
        self._sequences.clear()
        self._sequence_provider = sequence_provider
        self._provider_row_count = int(row_count)
        self.max_sequence_length = int(max_sequence_length)
        self.clear_selection()

    def remove_sequence(self, index):
        if self._using_provider():
            if index < 0 or index >= self._provider_row_count:
                raise IndexError(f"Sequence index {index} out of range")
            self._provider_row_count -= 1
            self.clear_selection()
            return
        if index < 0 or index >= len(self._sequences):
            raise IndexError(f"Sequence index {index} out of range")
        del self._sequences[index]
        self.recalc_max_sequence_length()
        self.clear_selection()

    def move_sequence(self, from_index, to_index):
        n = self.get_row_count()
        if not (0 <= from_index < n and 0 <= to_index < n):
            raise IndexError("move_sequence out of range")
        if from_index == to_index:
            return
        if self._using_provider():
            self.clear_selection()
            return
        sequence = self._sequences.pop(from_index)
        self._sequences.insert(to_index, sequence)
        self.clear_selection()

    def clear_sequences(self):
        self._sequences.clear(); self._sequence_provider = None; self._provider_row_count = 0; self.max_sequence_length = 0; self.clear_selection()

    def recalc_max_sequence_length(self):
        if self._using_provider():
            return self.max_sequence_length
        self.max_sequence_length = max((len(s) for s in self._sequences), default=0)
        return self.max_sequence_length

    def get_sequences(self):
        if self._using_provider():
            return [self._sequence_provider(i) for i in range(self._provider_row_count)]
        return list(self._sequences)
    def get_row_count(self): return self._provider_row_count if self._using_provider() else len(self._sequences)
    def get_sequence(self, row_index):
        if self._using_provider():
            return self._sequence_provider(row_index)
        return self._sequences[row_index]

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
