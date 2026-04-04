# repositories/database_repository.py
from .base_repository import AbstractSequenceRepository
class DatabaseRepository(AbstractSequenceRepository):
    def __init__(self, connection_string): self.connection_string = connection_string
    def get_sequence_by_id(self, sid): raise NotImplementedError
    def list_sequences(self): raise NotImplementedError
    def get_features_in_region(self, sid, start, end): raise NotImplementedError
    def save_sequence(self, seq): raise NotImplementedError
