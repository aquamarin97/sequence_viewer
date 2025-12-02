"""
Factory for constructing repositories based on configuration.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from settings.config import AppConfig

from .base_repository import AbstractSequenceRepository
from .database_repository import DatabaseRepository
from .file_based_repository import FileBasedRepository


class RepositoryFactory:
    """Instantiate repository implementations based on ``AppConfig`` settings."""

    def __init__(self, config: AppConfig):
        self.config = config

    def create_repository(self) -> AbstractSequenceRepository:
        source_type = self.config.data_source.type
        source_config: Dict[str, Any] = self.config.data_source.config

        if source_type == "file":
            return FileBasedRepository(
                fasta_path=Path(source_config.get("fasta_path", "")),
                feature_path=Path(source_config.get("feature_path")) if source_config.get("feature_path") else None,
            )
        if source_type == "database":
            return DatabaseRepository(connection_string=source_config.get("connection_string", ""))

        raise ValueError(f"Unsupported repository type '{source_type}'")