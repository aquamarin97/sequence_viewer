# io/export/fasta_exporter.py
from __future__ import annotations

from pathlib import Path

from sequence_viewer.io.sqx.reader import SQXReader

_LINE_WIDTH = 70


class FASTAExporter:
    """Exports sequences from an SQX file to standard FASTA format."""

    def export(self, reader: SQXReader, output_path: str | Path) -> None:
        """Write all sequences from *reader* to *output_path* as FASTA."""
        output_path = Path(output_path)
        with open(output_path, 'w', encoding='utf-8') as fh:
            for i in range(reader.sequence_count()):
                record = reader.read_sequence_record(i)
                seq = record.sequence
                seq_str: str = seq.to_str() if hasattr(seq, 'to_str') else str(seq)
                fh.write(f'>{record.header}\n')
                for start in range(0, len(seq_str), _LINE_WIDTH):
                    fh.write(seq_str[start:start + _LINE_WIDTH] + '\n')
