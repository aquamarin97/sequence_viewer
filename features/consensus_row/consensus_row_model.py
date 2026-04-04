# features/consensus_row/consensus_row_model.py
from __future__ import annotations
from typing import Optional, Sequence
from model.consensus_calculator import ConsensusCalculator, ConsensusMethod

class ConsensusRowModel:
    def __init__(self, method=ConsensusMethod.PLURALITY, threshold=ConsensusCalculator.DEFAULT_THRESHOLD):
        self._method = method; self._threshold = threshold
        self._cached_consensus = None; self._cache_valid = False
        self._calculator = ConsensusCalculator(method, threshold)

    @property
    def method(self): return self._method
    @property
    def threshold(self): return self._threshold

    def set_method(self, method, threshold=None):
        changed = False
        if method != self._method: self._method = method; changed = True
        if threshold is not None:
            t = max(0.0, min(1.0, threshold))
            if t != self._threshold: self._threshold = t; changed = True
        if changed:
            self._calculator = ConsensusCalculator(self._method, self._threshold)
            self.invalidate()

    def invalidate(self): self._cache_valid = False; self._cached_consensus = None

    def get_consensus(self, sequences):
        if self._cache_valid and self._cached_consensus is not None: return self._cached_consensus
        self._cached_consensus = self._calculator.compute(sequences)
        self._cache_valid = True
        return self._cached_consensus
