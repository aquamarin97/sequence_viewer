# repositories/base_repository.py
from abc import ABC, abstractmethod
from typing import Iterable, Mapping, Protocol

class SequenceRecord(Protocol):
    id: str
    sequence: str

class AbstractSequenceRepository(ABC):
    @abstractmethod
    def get_sequence_by_id(self, sequence_id): pass
    @abstractmethod
    def list_sequences(self): pass
    @abstractmethod
    def get_features_in_region(self, sequence_id, start, end): pass
    @abstractmethod
    def save_sequence(self, sequence): pass
