# model/motif_finder.py
"""
Fuzzy motif arama motoru — Hamming mesafesi tabanlı.

Özellikler
----------
* Forward strand araması
* Reverse complement strand araması
* Mismatch toleransı (max_mismatches)
* MSA gap karakterleri ('-') arama sırasında atlanır

Kullanım
--------
    finder  = MotifFinder(query="ATCGATCG", max_mismatches=1)
    results = finder.search(sequences, search_forward=True, search_reverse=True)
    for hit in results:
        print(hit.seq_index, hit.start, hit.end, hit.strand, hit.mismatches)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Sequence


# ---------------------------------------------------------------------------
# Reverse complement
# ---------------------------------------------------------------------------

_COMPLEMENT: dict[str, str] = {
    'A': 'T', 'T': 'A', 'G': 'C', 'C': 'G',
    'a': 't', 't': 'a', 'g': 'c', 'c': 'g',
    'N': 'N', 'n': 'n', '-': '-',
}


def reverse_complement(seq: str) -> str:
    return "".join(_COMPLEMENT.get(b, 'N') for b in reversed(seq))


# ---------------------------------------------------------------------------
# Sonuç dataclass'ı
# ---------------------------------------------------------------------------

@dataclass
class MotifHit:
    seq_index:  int     # hangi dizide (0-based)
    start:      int     # alignment pozisyonu (0-based, inclusive)
    end:        int     # alignment pozisyonu (0-based, inclusive)
    strand:     str     # "+" veya "-"
    mismatches: int     # kaç uyumsuzluk

    def length(self) -> int:
        return self.end - self.start + 1


# ---------------------------------------------------------------------------
# Arama motoru
# ---------------------------------------------------------------------------

class MotifFinder:
    """
    Hizalanmış dizi listesinde fuzzy motif arar.

    Parametreler
    ------------
    query : str
        Aranacak motif (gap olmadan).
    max_mismatches : int
        Kabul edilen maksimum Hamming mesafesi.
    """

    def __init__(self, query: str, max_mismatches: int = 0) -> None:
        # Gap ve boşlukları temizle
        self.query         = query.upper().replace("-", "").replace(" ", "")
        self.max_mismatches = max(0, max_mismatches)
        self._rc_query     = reverse_complement(self.query)

    def search(
        self,
        sequences: Sequence[str],
        search_forward: bool = True,
        search_reverse: bool = False,
    ) -> List[MotifHit]:
        """
        Tüm dizilerde arama yapar, MotifHit listesi döner.
        Aynı pozisyonda hem forward hem reverse eşleşme olabilir.
        """
        hits: List[MotifHit] = []

        for seq_idx, seq in enumerate(sequences):
            if search_forward:
                hits.extend(
                    self._search_in_sequence(seq, seq_idx, "+", self.query)
                )
            if search_reverse:
                hits.extend(
                    self._search_in_sequence(seq, seq_idx, "-", self._rc_query)
                )

        return hits

    # ------------------------------------------------------------------
    # İç arama
    # ------------------------------------------------------------------

    def _search_in_sequence(
        self,
        alignment_seq: str,
        seq_idx: int,
        strand: str,
        pattern: str,
    ) -> List[MotifHit]:
        """
        Tek bir hizalanmış dizide sliding window ile arama.

        Gap karakterleri ('-') pencereden dışlanır:
        Pencere, `pattern` uzunluğunda *gap-olmayan* karakter içerecek
        şekilde genişletilir.
        """
        hits: List[MotifHit] = []
        pat_len = len(pattern)
        seq_len = len(alignment_seq)

        if pat_len == 0 or seq_len < pat_len:
            return hits

        # Gap-free pozisyon listesi: (alignment_pos, base)
        bases = [
            (i, alignment_seq[i].upper())
            for i in range(seq_len)
            if alignment_seq[i] != '-'
        ]

        n_bases = len(bases)
        if n_bases < pat_len:
            return hits

        for start_b in range(n_bases - pat_len + 1):
            window = bases[start_b : start_b + pat_len]

            # Hamming mesafesi
            mm = sum(
                1 for (_, b), p in zip(window, pattern)
                if b != p and p not in ('N', 'n')
            )

            if mm <= self.max_mismatches:
                aln_start = window[0][0]
                aln_end   = window[-1][0]
                hits.append(MotifHit(
                    seq_index  = seq_idx,
                    start      = aln_start,
                    end        = aln_end,
                    strand     = strand,
                    mismatches = mm,
                ))

        return hits