from pathlib import Path
from typing import List, Mapping, Iterable
from .base_repository import AbstractSequenceRepository

class FileSequenceRecord:
    def __init__(self, record_id, sequence): self.id = record_id; self.sequence = sequence

class FileBasedRepository(AbstractSequenceRepository):
    def __init__(self, fasta_path, feature_path=None):
        self.fasta_path = Path(fasta_path); self.feature_path = Path(feature_path) if feature_path else None
        self._cache = []; self._load_sequences()
    def _load_sequences(self):
        if not self.fasta_path.exists(): raise FileNotFoundError(f"FASTA path not found: {self.fasta_path}")
        from Bio import SeqIO
        self._cache = [FileSequenceRecord(r.id, str(r.seq)) for r in SeqIO.parse(str(self.fasta_path), "fasta")]
    def get_sequence_by_id(self, sid):
        for r in self._cache:
            if r.id == sid: return r
        raise KeyError(f"Not found: {sid}")
    def list_sequences(self): return list(self._cache)
    def get_features_in_region(self, sid, start, end): return []
    def save_sequence(self, seq): pass
