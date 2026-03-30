# model/motif_finder.py
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Sequence

_COMPLEMENT = {'A':'T','T':'A','G':'C','C':'G','a':'t','t':'a','g':'c','c':'g','N':'N','n':'n','-':'-'}

def reverse_complement(seq):
    return "".join(_COMPLEMENT.get(b, 'N') for b in reversed(seq))

@dataclass
class MotifHit:
    seq_index: int
    start: int
    end: int
    strand: str
    mismatches: int
    def length(self): return self.end - self.start + 1

class MotifFinder:
    def __init__(self, query, max_mismatches=0):
        self.query = query.upper().replace("-","").replace(" ","")
        self.max_mismatches = max(0, max_mismatches)
        self._rc_query = reverse_complement(self.query)

    def search(self, sequences, search_forward=True, search_reverse=False):
        hits = []
        for seq_idx, seq in enumerate(sequences):
            if search_forward:
                hits.extend(self._search_in_sequence(seq, seq_idx, "+", self.query))
            if search_reverse:
                hits.extend(self._search_in_sequence(seq, seq_idx, "-", self._rc_query))
        return hits

    def _search_in_sequence(self, alignment_seq, seq_idx, strand, pattern):
        hits = []
        pat_len = len(pattern)
        seq_len = len(alignment_seq)
        if pat_len == 0 or seq_len < pat_len: return hits
        bases = [(i, alignment_seq[i].upper()) for i in range(seq_len) if alignment_seq[i] != '-']
        n_bases = len(bases)
        if n_bases < pat_len: return hits
        for start_b in range(n_bases - pat_len + 1):
            window = bases[start_b:start_b + pat_len]
            mm = sum(1 for (_, b), p in zip(window, pattern) if b != p and p not in ('N','n'))
            if mm <= self.max_mismatches:
                hits.append(MotifHit(seq_index=seq_idx, start=window[0][0], end=window[-1][0], strand=strand, mismatches=mm))
        return hits
