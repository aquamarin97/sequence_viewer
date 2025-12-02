"""
Placeholder database-backed repository implementation.

This class demonstrates how future database integrations can adhere to the
``AbstractSequenceRepository`` interface without impacting consumers.
"""
from __future__ import annotations

from typing import Iterable, Mapping

from .base_repository import AbstractSequenceRepository, SequenceRecord


class DatabaseRepository(AbstractSequenceRepository):
    def __init__(self, connection_string: str):
        self.connection_string = connection_string

    def get_sequence_by_id(self, sequence_id: str) -> SequenceRecord:
        raise NotImplementedError("Database access not yet implemented")

    def list_sequences(self) -> Iterable[SequenceRecord]:
        raise NotImplementedError("Database access not yet implemented")

    def get_features_in_region(self, sequence_id: str, start: int, end: int) -> Iterable[Mapping[str, object]]:
        raise NotImplementedError("Database access not yet implemented")

    def save_sequence(self, sequence: SequenceRecord) -> None:
        raise NotImplementedError("Database access not yet implemented")