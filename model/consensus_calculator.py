# model/consensus_calculator.py
"""
Saf Python konsensüs hesaplama motoru — Qt bağımlılığı yok.

Desteklenen modlar
------------------
ConsensusMethod.PLURALITY
    Her kolon için en sık görülen karakteri döner.
    Eşitlik durumunda öncelik sırası: A > C > G > T > - > N

ConsensusMethod.THRESHOLD
    Bir karakter kolonun `threshold` (0‒1) oranından fazlasını
    oluşturuyorsa o karakter döner; aksi hâlde mevcut
    baz kombinasyonuna karşılık gelen IUPAC ambiguity kodu döner.

Gap işleme
----------
Gap'ler ('-') her zaman sayıma dahil edilir.
Bir kolonda '-' baskınsa konsensüs karakteri '-' olarak gösterilir.

Örnek
-----
    seqs = ["ATCG-", "ATCG-", "ATGG-"]
    calc = ConsensusCalculator(method=ConsensusMethod.PLURALITY)
    result = calc.compute(seqs)
    # → "ATCG-"
"""

from __future__ import annotations

from enum import Enum, auto
from typing import List, Sequence


# ---------------------------------------------------------------------------
# IUPAC ambiguity kodu tablosu
# ---------------------------------------------------------------------------

_IUPAC: dict[frozenset, str] = {
    frozenset("AG"):    "R",
    frozenset("CT"):    "Y",
    frozenset("GC"):    "S",
    frozenset("AT"):    "W",
    frozenset("GT"):    "K",
    frozenset("AC"):    "M",
    frozenset("CGT"):   "B",
    frozenset("AGT"):   "D",
    frozenset("ACT"):   "H",
    frozenset("ACG"):   "V",
    frozenset("ACGT"):  "N",
}

# Eşitlik durumunda öncelik sırası
_PLURALITY_PRIORITY: list[str] = ["A", "C", "G", "T", "-", "N"]


# ---------------------------------------------------------------------------
# Mod enum'u
# ---------------------------------------------------------------------------

class ConsensusMethod(Enum):
    PLURALITY = auto()
    THRESHOLD = auto()


# ---------------------------------------------------------------------------
# Hesaplayıcı
# ---------------------------------------------------------------------------

class ConsensusCalculator:
    """
    Dizi listesinden konsensüs dizisi hesaplar.

    Parametreler
    ------------
    method : ConsensusMethod
        Hesaplama yöntemi.
    threshold : float
        THRESHOLD modunda kullanılır (varsayılan 0.70).
        Bir karakter bu orandan fazla görülürse direkt o karakter döner;
        aksi hâlde IUPAC kodu hesaplanır.
    """

    DEFAULT_THRESHOLD = 0.70

    def __init__(
        self,
        method: ConsensusMethod = ConsensusMethod.PLURALITY,
        threshold: float = DEFAULT_THRESHOLD,
    ) -> None:
        self.method    = method
        self.threshold = max(0.0, min(1.0, threshold))

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def compute(self, sequences: Sequence[str]) -> str:
        """
        Hizalanmış dizi listesinden konsensüs dizisi üretir.

        Tüm diziler aynı uzunlukta olmalıdır (MSA formatı).
        Farklı uzunluktaysa kısa olanlar sağdan '-' ile dolgulanmış
        kabul edilir.
        """
        if not sequences:
            return ""

        max_len = max(len(s) for s in sequences)
        if max_len == 0:
            return ""

        result = []
        for col in range(max_len):
            chars = [
                seq[col].upper() if col < len(seq) else "-"
                for seq in sequences
            ]
            result.append(self._resolve_column(chars))

        return "".join(result)

    # ------------------------------------------------------------------
    # İç hesaplama
    # ------------------------------------------------------------------

    def _resolve_column(self, chars: List[str]) -> str:
        """Tek bir kolondaki karakterlerden konsensüs karakteri belirler."""
        if not chars:
            return "N"

        # Sayım — bilinmeyen karakterler 'N' olarak kabul edilir
        counts: dict[str, int] = {}
        for ch in chars:
            if ch not in "ACGT-":
                ch = "N"
            counts[ch] = counts.get(ch, 0) + 1

        total = len(chars)

        if self.method == ConsensusMethod.PLURALITY:
            return self._plurality(counts)
        else:
            return self._threshold(counts, total)

    def _plurality(self, counts: dict[str, int]) -> str:
        """En sık karakteri döner; eşitlikte öncelik sırasını kullanır."""
        max_count = max(counts.values())
        candidates = [ch for ch, n in counts.items() if n == max_count]

        if len(candidates) == 1:
            return candidates[0]

        # Öncelik sırasına göre tiebreak
        for ch in _PLURALITY_PRIORITY:
            if ch in candidates:
                return ch

        return candidates[0]

    def _threshold(self, counts: dict[str, int], total: int) -> str:
        """
        Bir karakter eşiği geçiyorsa onu döner.
        Geçmiyorsa mevcut bazlardan IUPAC kodu türetir.
        """
        for ch, n in counts.items():
            if n / total >= self.threshold:
                return ch

        # Eşik geçilmedi → hangi bazlar var?
        present_bases = frozenset(
            ch for ch in counts if ch in "ACGT" and counts[ch] > 0
        )

        if not present_bases:
            # Sadece gap varsa
            return "-"

        # IUPAC tablosunda ara
        iupac = _IUPAC.get(present_bases)
        if iupac:
            return iupac

        # 5+ farklı baz (N dahil) → N
        return "N"