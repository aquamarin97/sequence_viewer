# file_io/parsers/fasta_parser.py
from __future__ import annotations

from pathlib import Path
from typing import Iterator

from file_io.parsers.parser_base import SequenceParser


class FASTAParser(SequenceParser):
    """Streaming FASTA parser; uses BioPython when available, falls back to custom parser."""

    def parse(self, path: str | Path) -> Iterator[tuple[str, str]]:
        """Yield (header, sequence) pairs without loading the whole file into RAM."""
        path = Path(path)
        try:
            from Bio import SeqIO
            for record in SeqIO.parse(str(path), 'fasta'):
                yield record.description, str(record.seq).upper()
        except ImportError:
            yield from self._parse_custom(path)

    def _parse_custom(self, path: Path) -> Iterator[tuple[str, str]]:
        """Minimal FASTA parser that streams line-by-line without BioPython."""
        header: str | None = None
        parts: list[str] = []
        with open(path, 'r', encoding='utf-8', errors='replace') as fh:
            for raw_line in fh:
                line = raw_line.rstrip('\n\r')
                if line.startswith('>'):
                    if header is not None:
                        yield header, ''.join(parts).upper()
                    header = line[1:].strip()
                    parts = []
                elif line:
                    parts.append(line)
            if header is not None:
                yield header, ''.join(parts).upper()
