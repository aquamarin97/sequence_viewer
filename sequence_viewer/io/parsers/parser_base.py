# io/parsers/parser_base.py
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Iterator


class SequenceParser(ABC):
    """Abstract base for all sequence-file parsers."""

    @abstractmethod
    def parse(self, path: str | Path) -> Iterator[tuple[str, str]]:
        """Yield (header, sequence) pairs from *path* without loading the full file."""
