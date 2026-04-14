# sequence_viewer/repositories/repository_factory.py
# repositories/repository_factory.py
from pathlib import Path
from .base_repository import AbstractSequenceRepository
from .database_repository import DatabaseRepository
from .file_based_repository import FileBasedRepository

class RepositoryFactory:
    def __init__(self, config): self.config = config
    def create_repository(self):
        source_type = self.config.data_source.type
        source_config = self.config.data_source.config
        if source_type == "file":
            return FileBasedRepository(fasta_path=Path(source_config.get("fasta_path","")),
                feature_path=Path(source_config.get("feature_path")) if source_config.get("feature_path") else None)
        if source_type == "database":
            return DatabaseRepository(connection_string=source_config.get("connection_string",""))
        raise ValueError(f"Unsupported: {source_type}")


