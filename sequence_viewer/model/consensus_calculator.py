# model/consensus_calculator.py
from __future__ import annotations
from enum import Enum, auto
from typing import List, Sequence

_IUPAC: dict[frozenset, str] = {
    frozenset("AG"): "R", frozenset("CT"): "Y", frozenset("GC"): "S",
    frozenset("AT"): "W", frozenset("GT"): "K", frozenset("AC"): "M",
    frozenset("CGT"): "B", frozenset("AGT"): "D", frozenset("ACT"): "H",
    frozenset("ACG"): "V", frozenset("ACGT"): "N",
}
_PLURALITY_PRIORITY: list[str] = ["A", "C", "G", "T", "-", "N"]

class ConsensusMethod(Enum):
    PLURALITY = auto()
    THRESHOLD = auto()

class ConsensusCalculator:
    DEFAULT_THRESHOLD = 0.70

    def __init__(self, method=ConsensusMethod.PLURALITY, threshold=DEFAULT_THRESHOLD):
        self.method = method
        self.threshold = max(0.0, min(1.0, threshold))

    def compute(self, sequences):
        if not sequences: return ""
        max_len = max(len(s) for s in sequences)
        if max_len == 0: return ""
        result = []
        for col in range(max_len):
            chars = [seq[col].upper() if col < len(seq) else "-" for seq in sequences]
            result.append(self._resolve_column(chars))
        return "".join(result)

    def _resolve_column(self, chars):
        if not chars: return "N"
        counts = {}
        for ch in chars:
            if ch not in "ACGT-": ch = "N"
            counts[ch] = counts.get(ch, 0) + 1
        total = len(chars)
        if self.method == ConsensusMethod.PLURALITY:
            return self._plurality(counts)
        return self._threshold_resolve(counts, total)

    def _plurality(self, counts):
        max_count = max(counts.values())
        candidates = [ch for ch, n in counts.items() if n == max_count]
        if len(candidates) == 1: return candidates[0]
        for ch in _PLURALITY_PRIORITY:
            if ch in candidates: return ch
        return candidates[0]

    def _threshold_resolve(self, counts, total):
        for ch, n in counts.items():
            if n / total >= self.threshold: return ch
        present_bases = frozenset(ch for ch in counts if ch in "ACGT" and counts[ch] > 0)
        if not present_bases: return "-"
        iupac = _IUPAC.get(present_bases)
        if iupac: return iupac
        return "N"


