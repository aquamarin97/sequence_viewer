"""
Abstract interfaces for sequence data repositories.

Repositories encapsulate data access for the sequence_viewer package, keeping
UI components decoupled from concrete storage implementations.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterable, Mapping, Protocol


class SequenceRecord(Protocol):
    id: str
    sequence: str


class AbstractSequenceRepository(ABC):
    """Base class for all sequence repositories."""

    @abstractmethod
    def get_sequence_by_id(self, sequence_id: str) -> SequenceRecord:
        """Fetch a single sequence by its identifier."""

    @abstractmethod
    def list_sequences(self) -> Iterable[SequenceRecord]:
        """Return an iterable of all sequences available in the repository."""

    @abstractmethod
    def get_features_in_region(self, sequence_id: str, start: int, end: int) -> Iterable[Mapping[str, object]]:
        """Return feature annotations for a region on a sequence."""

    @abstractmethod
    def save_sequence(self, sequence: SequenceRecord) -> None:
        """Persist or update a sequence record."""