# features/consensus_row/consensus_row_model.py
"""
Konsensüs satırının model katmanı.

Sorumluluklar
-------------
* Hesaplama yöntemini (method, threshold) tutmak
* Konsensüs dizisini cache'lemek ve gerektiğinde geçersiz kılmak
* Cache geçersiz olduğunda yeniden hesaplamak
"""

from __future__ import annotations

from typing import Optional, Sequence

from model.consensus_calculator import ConsensusCalculator, ConsensusMethod


class ConsensusRowModel:
    """
    ConsensusRowWidget için model katmanı.

    Kullanım
    --------
        model = ConsensusRowModel()
        model.set_method(ConsensusMethod.THRESHOLD, threshold=0.75)
        model.invalidate()                     # veri değiştiğinde
        seq = model.get_consensus(sequences)   # lazy hesaplama
    """

    def __init__(
        self,
        method: ConsensusMethod = ConsensusMethod.PLURALITY,
        threshold: float = ConsensusCalculator.DEFAULT_THRESHOLD,
    ) -> None:
        self._method:    ConsensusMethod = method
        self._threshold: float           = threshold

        self._cached_consensus: Optional[str]  = None
        self._cache_valid:      bool           = False

        self._calculator = ConsensusCalculator(method, threshold)

    # ------------------------------------------------------------------
    # Ayar API'si
    # ------------------------------------------------------------------

    @property
    def method(self) -> ConsensusMethod:
        return self._method

    @property
    def threshold(self) -> float:
        return self._threshold

    def set_method(
        self,
        method: ConsensusMethod,
        threshold: Optional[float] = None,
    ) -> None:
        """
        Hesaplama yöntemini değiştirir ve cache'i geçersiz kılar.
        threshold verilmezse mevcut değer korunur.
        """
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

    # ------------------------------------------------------------------
    # Cache yönetimi
    # ------------------------------------------------------------------

    def invalidate(self) -> None:
        """
        Veri değiştiğinde (AlignmentDataModel sinyali) çağrılır.
        Bir sonraki get_consensus() çağrısında yeniden hesaplanır.
        """
        self._cache_valid      = False
        self._cached_consensus = None

    def get_consensus(self, sequences: Sequence[str]) -> str:
        """
        Konsensüs dizisini döner.
        Cache geçerliyse hesaplama yapmaz; geçersizse lazy hesaplar.
        """
        if self._cache_valid and self._cached_consensus is not None:
            return self._cached_consensus

        self._cached_consensus = self._calculator.compute(sequences)
        self._cache_valid      = True
        return self._cached_consensus