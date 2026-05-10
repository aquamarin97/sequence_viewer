# io/sqx/reader.py
from __future__ import annotations

import mmap
import struct
from pathlib import Path
from types import TracebackType

from sequence_viewer.io.sqx.spec import (
    BLOCK_ANALYSES,
    BLOCK_PROJECT_META,
    BLOCK_SEQUENCES,
    FORMAT_VERSION,
    MAGIC,
    SQXFormatError,
    SQXVersionError,
)
from sequence_viewer.io.sqx.block_types.analyses import AnalysisEntry, deserialize_analyses_block
from sequence_viewer.io.sqx.block_types.project_meta import ProjectMeta
from sequence_viewer.io.sqx.block_types.sequences import SequenceBlockEntry, deserialize_record_meta
from sequence_viewer.model.lazy_sequence import LazySequence
from sequence_viewer.model.sequence_record import SequenceRecord


class SQXReader:
    """
    Opens an SQX file with mmap for lazy sequence access.
    Use as a context manager: ``with SQXReader(path) as r: ...``
    """

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._file = None
        self._mmap: mmap.mmap | None = None
        # block_type → (file_offset, byte_length, version)
        self._block_dir: dict[int, tuple[int, int, int]] = {}
        self._seq_entries: list[SequenceBlockEntry] = []
        self._seq_block_offset: int = 0

    # ------------------------------------------------------------------ lifecycle

    def open(self) -> SQXReader:
        self._file = open(self._path, 'rb')
        self._mmap = mmap.mmap(self._file.fileno(), 0, access=mmap.ACCESS_READ)
        self._parse_header()
        self._load_sequence_directory()
        return self

    def close(self) -> None:
        if self._mmap is not None:
            self._mmap.close()
            self._mmap = None
        if self._file is not None:
            self._file.close()
            self._file = None

    def __enter__(self) -> SQXReader:
        return self.open()

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.close()

    # ------------------------------------------------------------------ public API

    def read_meta(self) -> ProjectMeta:
        """Return the PROJECT_META block, or a default if the block is absent."""
        if BLOCK_PROJECT_META not in self._block_dir:
            return ProjectMeta()
        offset, length, _ = self._block_dir[BLOCK_PROJECT_META]
        return ProjectMeta.deserialize(self._mmap[offset:offset + length])  # type: ignore[arg-type]

    def sequence_count(self) -> int:
        return len(self._seq_entries)

    def read_sequence_record(self, index: int) -> SequenceRecord:
        """Return a SequenceRecord whose .sequence is a LazySequence (or str for short seqs)."""
        entry = self._seq_entries[index]
        abs_data_offset = self._seq_block_offset + entry.data_offset
        sequence: str | LazySequence = LazySequence(
            self._mmap,  # type: ignore[arg-type]
            abs_data_offset,
            entry.base_count,
            entry.encoding,
        )
        return SequenceRecord(
            header=entry.header,
            sequence=sequence,
            id=entry.seq_id,
            annotations=list(entry.annotations),
        )

    def read_analyses(self) -> list[AnalysisEntry]:
        """Return all cached analysis entries, or [] if the block is absent."""
        if BLOCK_ANALYSES not in self._block_dir:
            return []
        offset, length, _ = self._block_dir[BLOCK_ANALYSES]
        return deserialize_analyses_block(self._mmap, offset)  # type: ignore[arg-type]

    # ------------------------------------------------------------------ internal

    def _parse_header(self) -> None:
        mm = self._mmap
        pos = 0
        magic = bytes(mm[pos:pos + 8]); pos += 8
        if magic != MAGIC:
            raise SQXFormatError(f"Not an SQX file — bad magic: {magic!r}")
        fmt_ver = struct.unpack_from('<H', mm, pos)[0]; pos += 2
        if fmt_ver > FORMAT_VERSION:
            raise SQXVersionError(
                f"SQX format version {fmt_ver} is newer than supported ({FORMAT_VERSION})"
            )
        av_len = struct.unpack_from('<H', mm, pos)[0]; pos += 2
        pos += av_len  # skip app_version string
        block_count = struct.unpack_from('<I', mm, pos)[0]; pos += 4
        for _ in range(block_count):
            btype   = struct.unpack_from('<I', mm, pos)[0]; pos += 4
            boffset = struct.unpack_from('<Q', mm, pos)[0]; pos += 8
            blength = struct.unpack_from('<Q', mm, pos)[0]; pos += 8
            bver    = struct.unpack_from('<H', mm, pos)[0]; pos += 2
            self._block_dir[btype] = (boffset, blength, bver)

    def _load_sequence_directory(self) -> None:
        if BLOCK_SEQUENCES not in self._block_dir:
            return
        block_file_offset, _block_length, _ = self._block_dir[BLOCK_SEQUENCES]
        self._seq_block_offset = block_file_offset
        mm = self._mmap
        pos = block_file_offset

        seq_count = struct.unpack_from('<I', mm, pos)[0]; pos += 4

        # Read SEQ DIRECTORY (one entry per sequence: uuid + data_offset + data_length + base_count)
        raw_dir: list[tuple[str, int, int, int]] = []
        for _ in range(seq_count):
            seq_id = str(__import__('uuid').UUID(bytes=bytes(mm[pos:pos + 16]))); pos += 16
            data_off, data_len, base_cnt = struct.unpack_from('<QQQ', mm, pos); pos += 24
            raw_dir.append((seq_id, data_off, data_len, base_cnt))

        # Parse record metadata sequentially (pos now at first SEQ RECORD)
        self._seq_entries = []
        for seq_id, data_off_in_block, data_len, base_cnt in raw_dir:
            meta, pos = deserialize_record_meta(mm, pos)
            pos += data_len  # skip encoded_data bytes
            self._seq_entries.append(SequenceBlockEntry(
                seq_id=seq_id,
                header=meta['header'],
                source_file=meta['source_file'],
                seq_type=meta['seq_type'],
                encoding=meta['encoding'],
                annotations=meta['annotations'],
                data_offset=data_off_in_block,
                data_length=data_len,
                base_count=base_cnt,
            ))
