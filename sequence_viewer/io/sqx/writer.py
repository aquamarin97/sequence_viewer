# io/sqx/writer.py
from __future__ import annotations

import struct
from pathlib import Path

from sequence_viewer.io.sqx.spec import (
    APP_VERSION,
    BLOCK_ANALYSES,
    BLOCK_DIR_ENTRY_SIZE,
    BLOCK_PROJECT_META,
    BLOCK_SEQUENCES,
    FORMAT_VERSION,
    MAGIC,
)
from sequence_viewer.io.sqx.block_types.analyses import AnalysisEntry, serialize_analyses_block
from sequence_viewer.io.sqx.block_types.project_meta import ProjectMeta
from sequence_viewer.io.sqx.block_types.sequences import serialize_sequences_block
from sequence_viewer.model.sequence_record import SequenceRecord


class SQXWriter:
    """Writes a collection of SequenceRecords to a binary SQX file."""

    def write(
        self,
        path: str | Path,
        records: list[SequenceRecord],
        meta: ProjectMeta,
        analyses: list[AnalysisEntry] | None = None,
        source_file: str = "",
    ) -> None:
        """Serialise *records* + *meta* (and optionally *analyses*) to *path*."""
        analyses = analyses or []
        path = Path(path)

        blocks: list[tuple[int, int, bytes]] = [
            (BLOCK_PROJECT_META, 1, meta.serialize()),
            (BLOCK_SEQUENCES,    1, serialize_sequences_block(records, source_file)),
        ]
        if analyses:
            blocks.append((BLOCK_ANALYSES, 1, serialize_analyses_block(analyses)))

        n_blocks = len(blocks)
        av_bytes = APP_VERSION.encode('utf-8')

        with open(path, 'wb') as fh:
            fh.write(MAGIC)
            fh.write(struct.pack('<H', FORMAT_VERSION))
            fh.write(struct.pack('<H', len(av_bytes)) + av_bytes)
            fh.write(struct.pack('<I', n_blocks))

            # Reserve space for the block directory; fill it in after writing blocks.
            dir_pos = fh.tell()
            fh.write(b'\x00' * (n_blocks * BLOCK_DIR_ENTRY_SIZE))

            # Write blocks, collecting their offsets and lengths.
            dir_entries: list[tuple[int, int, int, int]] = []
            for btype, bver, bdata in blocks:
                offset = fh.tell()
                fh.write(bdata)
                dir_entries.append((btype, offset, len(bdata), bver))

            # Seek back and write the real directory.
            fh.seek(dir_pos)
            for btype, offset, blength, bver in dir_entries:
                fh.write(struct.pack('<I', btype))
                fh.write(struct.pack('<Q', offset))
                fh.write(struct.pack('<Q', blength))
                fh.write(struct.pack('<H', bver))
