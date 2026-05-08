# sequence_viewer/model/consensus_calculator.py
from __future__ import annotations

from enum import Enum, auto

import numpy as np

_IUPAC: dict[frozenset, str] = {
    frozenset("AG"): "R", frozenset("CT"): "Y", frozenset("GC"): "S",
    frozenset("AT"): "W", frozenset("GT"): "K", frozenset("AC"): "M",
    frozenset("CGT"): "B", frozenset("AGT"): "D", frozenset("ACT"): "H",
    frozenset("ACG"): "V", frozenset("ACGT"): "N",
}
_PLURALITY_PRIORITY: list[str] = ["A", "C", "G", "T", "-", "N"]

# Plurality priority as ordinal values (A > C > G > T > - > N).
# np.argmax returns the FIRST maximum, so ordering here encodes tie-breaking.
_PL_ORD = np.array([65, 67, 71, 84, 45, 78], dtype=np.uint8)

# Lookup table: valid_lut[byte] = True iff byte is one of A C G T - N (after uppercase)
_VALID_LUT = np.zeros(256, dtype=bool)
for _v in _PL_ORD:
    _VALID_LUT[_v] = True


class ConsensusMethod(Enum):
    PLURALITY = auto()
    THRESHOLD = auto()


class ConsensusCalculator:
    DEFAULT_THRESHOLD = 0.70

    def __init__(self, method=ConsensusMethod.PLURALITY, threshold=DEFAULT_THRESHOLD):
        self.method = method
        self.threshold = max(0.0, min(1.0, threshold))

    # ── Public API ────────────────────────────────────────────────────────

    def compute(self, sequences) -> str:
        if not sequences:
            return ""
        max_len = max(len(s) for s in sequences)
        if max_len == 0:
            return ""
        return self.compute_range(sequences, 0, max_len)

    def compute_range(self, sequences, col_start: int, col_end: int) -> str:
        """Compute consensus for columns [col_start, col_end) only."""
        if not sequences or col_start >= col_end:
            return ""
        max_len = max(len(s) for s in sequences)
        col_end = min(col_end, max_len)
        if col_start >= col_end:
            return ""
        arr = self._build_arr(sequences, max_len)
        if col_start > 0 or col_end < max_len:
            arr = arr[:, col_start:col_end]
        if self.method == ConsensusMethod.PLURALITY:
            return self._plurality_numpy(arr)
        return self._threshold_numpy(arr, len(sequences))

    # ── numpy helpers ────────────────────────────────────────────────────

    @staticmethod
    def _build_arr(sequences, max_len: int) -> np.ndarray:
        n = len(sequences)
        # Fast path: all sequences same length (typical for aligned data)
        if all(len(s) == max_len for s in sequences):
            combined = "".join(sequences)
            arr = (
                np.frombuffer(combined.encode("latin-1"), dtype=np.uint8)
                .reshape(n, max_len)
                .copy()
            )
        else:
            arr = np.full((n, max_len), ord("-"), dtype=np.uint8)
            for i, seq in enumerate(sequences):
                enc = np.frombuffer(seq.encode("latin-1"), dtype=np.uint8)
                arr[i, : len(enc)] = enc
        # Uppercase in-place: a-z (97-122) → subtract 32
        lc = (arr >= 97) & (arr <= 122)
        arr[lc] -= 32
        # Normalize: any char not in ACGT-N → N(78)
        arr[~_VALID_LUT[arr]] = 78
        return arr

    @staticmethod
    def _plurality_numpy(arr: np.ndarray) -> str:
        # Count each char in priority order; argmax picks first (= highest priority) on ties.
        counts = np.stack([(arr == v).sum(axis=0) for v in _PL_ORD])  # (6, cols)
        best_idx = counts.argmax(axis=0)                               # (cols,)
        return _PL_ORD[best_idx].tobytes().decode("latin-1")

    def _threshold_numpy(self, arr: np.ndarray, total: int) -> str:
        # Pre-compute per-column counts for all 6 chars; resolve per-column in Python.
        counts_np = {chr(int(v)): (arr == v).sum(axis=0) for v in _PL_ORD}
        cols = arr.shape[1]
        result = []
        for j in range(cols):
            col_counts = {ch: int(counts_np[ch][j]) for ch in counts_np}
            result.append(self._threshold_resolve(col_counts, total))
        return "".join(result)

    # ── Column resolution (kept for threshold's IUPAC logic) ────────────

    def _threshold_resolve(self, counts: dict, total: int) -> str:
        for ch, n in counts.items():
            if n / total >= self.threshold:
                return ch
        present_bases = frozenset(
            ch for ch in counts if ch in "ACGT" and counts[ch] > 0
        )
        if not present_bases:
            return "-"
        iupac = _IUPAC.get(present_bases)
        return iupac if iupac else "N"
