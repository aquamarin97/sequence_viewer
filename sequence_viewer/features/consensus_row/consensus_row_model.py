# sequence_viewer/features/consensus_row/consensus_row_model.py
from __future__ import annotations

import threading
from typing import Optional

from PyQt5.QtCore import QObject, Qt, pyqtSignal

from sequence_viewer.model.consensus_calculator import ConsensusCalculator, ConsensusMethod


class ConsensusRowModel(QObject):
    """
    Holds the consensus state for a single alignment view.

    get_consensus()          — non-blocking; returns cached result or None while
                               a background thread computes it. Connect consensusReady
                               to widget.update() to refresh when done.
    get_consensus_blocking() — blocks until the result is available; used for
                               clipboard operations that need the full string.
    """

    consensusReady = pyqtSignal()

    def __init__(
        self,
        method=ConsensusMethod.PLURALITY,
        threshold=ConsensusCalculator.DEFAULT_THRESHOLD,
        parent=None,
    ):
        super().__init__(parent)
        self._method = method
        self._threshold = threshold
        self._calculator = ConsensusCalculator(method, threshold)

        self._cached_consensus: str | None = None
        self._cache_valid = False

        # Single-entry range cache for get_consensus_range()
        self._range_key: tuple | None = None
        self._range_result: str = ""

        # Background thread state
        self._lock = threading.Lock()
        self._computing = False
        self._compute_gen = 0          # incremented on invalidate to discard stale results
        self._compute_done = threading.Event()
        self._compute_done.set()       # initially "done" (nothing running)

    # ── Properties ───────────────────────────────────────────────────────

    @property
    def method(self):
        return self._method

    @property
    def threshold(self):
        return self._threshold

    # ── Configuration ────────────────────────────────────────────────────

    def set_method(self, method, threshold=None):
        changed = False
        if method != self._method:
            self._method = method
            changed = True
        if threshold is not None:
            t = max(0.0, min(1.0, threshold))
            if t != self._threshold:
                self._threshold = t
                changed = True
        if changed:
            self._calculator = ConsensusCalculator(self._method, self._threshold)
            self.invalidate()

    # ── Cache management ─────────────────────────────────────────────────

    def invalidate(self):
        with self._lock:
            self._compute_gen += 1    # marks any in-flight thread as stale
            self._cache_valid = False
            self._cached_consensus = None
            self._computing = False
            self._range_key = None
            self._range_result = ""
        self._compute_done.set()      # unblock any blocking waiter

    def cached_consensus(self) -> str | None:
        return self._cached_consensus if self._cache_valid else None

    # ── Consensus fetch ───────────────────────────────────────────────────

    def get_consensus(self, sequences) -> str | None:
        """
        Non-blocking.  Returns the cached consensus string, or None if still
        computing.  Starts a background thread on the first call after invalidation.
        Connect consensusReady (Qt.QueuedConnection) to trigger a repaint when done.
        """
        if self._cache_valid and self._cached_consensus is not None:
            return self._cached_consensus
        with self._lock:
            if self._computing:
                return None
            self._computing = True
            self._compute_done.clear()
            gen = self._compute_gen
        seq_copy = list(sequences)
        t = threading.Thread(target=self._run_compute, args=(seq_copy, gen), daemon=True)
        t.start()
        return None

    def get_consensus_blocking(self, sequences) -> str | None:
        """
        Blocking.  Waits for any background thread then returns the full consensus.
        Used for clipboard operations that require the complete string immediately.
        """
        if self._cache_valid and self._cached_consensus is not None:
            return self._cached_consensus
        if not sequences:
            return None
        # Wait for an in-progress background compute (up to 30 s)
        self._compute_done.wait(timeout=30.0)
        # Re-check after wait
        if self._cache_valid and self._cached_consensus is not None:
            return self._cached_consensus
        # Not cached yet (e.g. invalidated mid-flight) — compute synchronously
        result = self._calculator.compute(list(sequences)) or None
        if result:
            with self._lock:
                self._cached_consensus = result
                self._cache_valid = True
        return result

    def get_consensus_range(self, sequences, col_start: int, col_end: int) -> str:
        """Return consensus for [col_start, col_end) with a single-entry cache."""
        if self._range_key == (col_start, col_end):
            return self._range_result
        result = self._calculator.compute_range(sequences, col_start, col_end)
        self._range_key = (col_start, col_end)
        self._range_result = result
        return result

    # ── Background worker ────────────────────────────────────────────────

    def _run_compute(self, sequences: list, gen: int) -> None:
        result = self._calculator.compute(sequences)
        emit = False
        with self._lock:
            if self._compute_gen == gen:
                self._cached_consensus = result
                self._cache_valid = True
                self._computing = False
                emit = True
        self._compute_done.set()
        if emit:
            # Emitting from a background thread: PyQt5 auto-queues to the main
            # thread when the receiver lives there (QueuedConnection behaviour).
            self.consensusReady.emit()
