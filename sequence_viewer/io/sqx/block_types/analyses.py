# io/sqx/block_types/analyses.py
from __future__ import annotations

import hashlib
import json
import struct
import time
from dataclasses import dataclass, field
from typing import Any

from sequence_viewer.model.sequence_record import SequenceRecord

ANALYSIS_CONSENSUS: int    = 0x00000001
ANALYSIS_MOTIF_RESULT: int = 0x00000002


@dataclass
class AnalysisEntry:
    """One cached analysis result stored in the ANALYSES block."""
    analysis_type: int
    input_hash: bytes           # 32-byte SHA-256 of the input sequences
    data: bytes                 # JSON-encoded result
    timestamp: int = field(default_factory=lambda: int(time.time()))

    def serialize(self) -> bytes:
        buf = bytearray()
        buf += struct.pack('<I', self.analysis_type)
        buf += self.input_hash                          # 32 bytes
        buf += struct.pack('<q', self.timestamp)
        buf += struct.pack('<Q', len(self.data))
        buf += self.data
        return bytes(buf)

    @staticmethod
    def deserialize(buf: Any, offset: int) -> tuple[AnalysisEntry, int]:
        """Parse one AnalysisEntry from *buf* at *offset*; return (entry, new_offset)."""
        analysis_type = struct.unpack_from('<I', buf, offset)[0]; offset += 4
        input_hash = bytes(buf[offset:offset + 32]); offset += 32
        timestamp = struct.unpack_from('<q', buf, offset)[0]; offset += 8
        data_len = struct.unpack_from('<Q', buf, offset)[0]; offset += 8
        data = bytes(buf[offset:offset + data_len]); offset += data_len
        return AnalysisEntry(
            analysis_type=analysis_type,
            input_hash=input_hash,
            data=data,
            timestamp=timestamp,
        ), offset


def compute_input_hash(records: list[SequenceRecord]) -> bytes:
    """Return SHA-256 of all record IDs + encoded sequence data, sorted by ID for stability."""
    from sequence_viewer.io.sqx.spec import encode_sequence
    h = hashlib.sha256()
    for rec in sorted(records, key=lambda r: r.id):
        h.update(rec.id.encode('utf-8'))
        seq_str: str = rec.sequence if isinstance(rec.sequence, str) else rec.sequence.to_str()  # type: ignore[union-attr]
        h.update(encode_sequence(seq_str))
    return h.digest()


def serialize_analyses_block(entries: list[AnalysisEntry]) -> bytes:
    """Build the complete ANALYSES block content."""
    buf = bytearray()
    buf += struct.pack('<I', len(entries))
    for entry in entries:
        buf += entry.serialize()
    return bytes(buf)


def deserialize_analyses_block(buf: Any, offset: int) -> list[AnalysisEntry]:
    """Parse all AnalysisEntry objects from the ANALYSES block."""
    count = struct.unpack_from('<I', buf, offset)[0]; offset += 4
    entries: list[AnalysisEntry] = []
    for _ in range(count):
        entry, offset = AnalysisEntry.deserialize(buf, offset)
        entries.append(entry)
    return entries
