"""
File-backed repository implementation.

This repository reads sequence data from FASTA files and feature annotations
from BED/VCF-like tabular files. It intentionally keeps parsing light-weight to
serve as an example backend that respects the ``AbstractSequenceRepository``
interface.
"""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable, List, Mapping

from Bio import SeqIO

from .base_repository import AbstractSequenceRepository, SequenceRecord


class FileSequenceRecord:
    def __init__(self, record_id: str, sequence: str):
        self.id = record_id
        self.sequence = sequence


class FileBasedRepository(AbstractSequenceRepository):
    """Repository that loads data from local files."""

    def __init__(self, fasta_path: Path, feature_path: Path | None = None):
        self.fasta_path = Path(fasta_path)
        self.feature_path = Path(feature_path) if feature_path else None
        self._cache: List[FileSequenceRecord] = []
        self._load_sequences()

    def _load_sequences(self) -> None:
        if not self.fasta_path.exists():
            raise FileNotFoundError(f"FASTA path not found: {self.fasta_path}")

        self._cache = [FileSequenceRecord(record.id, str(record.seq)) for record in SeqIO.parse(str(self.fasta_path), "fasta")]

    def _load_features(self) -> List[Mapping[str, object]]:
        if not self.feature_path or not self.feature_path.exists():
            return []

        features: List[Mapping[str, object]] = []
        with self.feature_path.open("r", encoding="utf-8") as handle:
            reader = csv.DictReader(handle, delimiter="\t")
            for row in reader:
                features.append(row)
        return features

    def get_sequence_by_id(self, sequence_id: str) -> SequenceRecord:
        for record in self._cache:
            if record.id == sequence_id:
                return record
        raise KeyError(f"Sequence '{sequence_id}' not found")

    def list_sequences(self) -> Iterable[SequenceRecord]:
        return list(self._cache)

    def get_features_in_region(self, sequence_id: str, start: int, end: int) -> Iterable[Mapping[str, object]]:
        features = self._load_features()
        filtered = []
        for feature in features:
            if feature.get("sequence_id") != sequence_id:
                continue
            try:
                f_start = int(feature.get("start", 0))
                f_end = int(feature.get("end", 0))
            except ValueError:
                continue
            if f_start <= end and f_end >= start:
                filtered.append(feature)
        return filtered

    def save_sequence(self, sequence: SequenceRecord) -> None:
        # Simple in-memory update; persistence can be added as needed.
        for idx, record in enumerate(self._cache):
            if record.id == sequence.id:
                self._cache[idx] = FileSequenceRecord(sequence.id, sequence.sequence)
                break
        else:
            self._cache.append(FileSequenceRecord(sequence.id, sequence.sequence))