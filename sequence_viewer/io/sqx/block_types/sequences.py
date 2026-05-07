# io/sqx/block_types/sequences.py
from __future__ import annotations

import struct
import uuid as _uuid_mod
from dataclasses import dataclass, field
from typing import Any

from sequence_viewer.io.sqx.spec import (
    ENCODING_IUPAC4,
    SEQ_TYPE_NUCLEOTIDE,
    encode_sequence,
)
from sequence_viewer.model.annotation import Annotation, AnnotationType
from sequence_viewer.model.sequence_record import SequenceRecord

# ── annotation type ↔ file integer mapping ────────────────────────────────────

_ANN_TYPE_TO_INT: dict[AnnotationType, int] = {
    AnnotationType.PRIMER:          0,
    AnnotationType.PROBE:           1,
    AnnotationType.REPEATED_REGION: 2,
    AnnotationType.MISMATCH_MARKER: 3,
}
_INT_TO_ANN_TYPE: dict[int, AnnotationType] = {v: k for k, v in _ANN_TYPE_TO_INT.items()}

# ── helpers ───────────────────────────────────────────────────────────────────

def _uuid_to_bytes(uid: str) -> bytes:
    return _uuid_mod.UUID(uid).bytes

def _bytes_to_uuid(b: bytes) -> str:
    return str(_uuid_mod.UUID(bytes=bytes(b)))

def _make_color(r: int, g: int, b: int):
    """Return a QColor(r, g, b) or None if PyQt5 is unavailable."""
    try:
        from PyQt5.QtGui import QColor
        return QColor(r, g, b)
    except ImportError:
        return None


# ── annotation serialisation ──────────────────────────────────────────────────

def serialize_annotation(ann: Annotation) -> bytes:
    """Serialise one Annotation to bytes."""
    buf = bytearray()
    buf += _uuid_to_bytes(ann.id)
    buf += struct.pack('<B', _ANN_TYPE_TO_INT.get(ann.type, 0))
    buf += struct.pack('<ii', ann.start, ann.end)
    buf += struct.pack('<B', 0x2B if ann.strand == '+' else 0x2D)

    label = ann.label.encode('utf-8')
    buf += struct.pack('<H', len(label)) + label
    notes = ann.notes.encode('utf-8')
    buf += struct.pack('<H', len(notes)) + notes

    if ann.color is not None:
        buf += struct.pack('<BBBB', 1, ann.color.red(), ann.color.green(), ann.color.blue())
    else:
        buf += struct.pack('<B', 0)

    if ann.score is not None:
        buf += struct.pack('<Bd', 1, ann.score)
    else:
        buf += struct.pack('<B', 0)

    if ann.tm is not None:
        buf += struct.pack('<Bd', 1, ann.tm)
    else:
        buf += struct.pack('<B', 0)

    if ann.gc_percent is not None:
        buf += struct.pack('<Bd', 1, ann.gc_percent)
    else:
        buf += struct.pack('<B', 0)

    parent_bytes = ann.parent_id.encode('utf-8') if ann.parent_id else b''
    buf += struct.pack('<H', len(parent_bytes)) + parent_bytes

    if ann.mismatch_base is not None:
        mb = ann.mismatch_base[0].encode('ascii') if ann.mismatch_base else b'\x00'
        eb = (ann.expected_base[0].encode('ascii') if ann.expected_base else b'\x00')
        buf += struct.pack('<BBB', 1, mb[0], eb[0])
    else:
        buf += struct.pack('<B', 0)

    buf += struct.pack('<B', 0)  # view_hidden — always visible for now
    return bytes(buf)


def deserialize_annotation(buf: Any, offset: int) -> tuple[Annotation, int]:
    """Parse one Annotation from *buf* at *offset*; return (annotation, new_offset)."""
    ann_id = _bytes_to_uuid(buf[offset:offset + 16])
    offset += 16
    ann_type = _INT_TO_ANN_TYPE.get(struct.unpack_from('<B', buf, offset)[0], AnnotationType.PRIMER)
    offset += 1
    start, end = struct.unpack_from('<ii', buf, offset)
    offset += 8
    strand = '+' if struct.unpack_from('<B', buf, offset)[0] == 0x2B else '-'
    offset += 1

    label_len = struct.unpack_from('<H', buf, offset)[0]; offset += 2
    label = bytes(buf[offset:offset + label_len]).decode('utf-8'); offset += label_len
    notes_len = struct.unpack_from('<H', buf, offset)[0]; offset += 2
    notes = bytes(buf[offset:offset + notes_len]).decode('utf-8'); offset += notes_len

    has_color = struct.unpack_from('<B', buf, offset)[0]; offset += 1
    color = None
    if has_color:
        r, g, b = struct.unpack_from('<BBB', buf, offset); offset += 3
        color = _make_color(r, g, b)

    has_score = struct.unpack_from('<B', buf, offset)[0]; offset += 1
    score = None
    if has_score:
        score = struct.unpack_from('<d', buf, offset)[0]; offset += 8

    has_tm = struct.unpack_from('<B', buf, offset)[0]; offset += 1
    tm = None
    if has_tm:
        tm = struct.unpack_from('<d', buf, offset)[0]; offset += 8

    has_gc = struct.unpack_from('<B', buf, offset)[0]; offset += 1
    gc_percent = None
    if has_gc:
        gc_percent = struct.unpack_from('<d', buf, offset)[0]; offset += 8

    parent_id_len = struct.unpack_from('<H', buf, offset)[0]; offset += 2
    parent_id: str | None = None
    if parent_id_len:
        parent_id = bytes(buf[offset:offset + parent_id_len]).decode('utf-8')
    offset += parent_id_len

    has_mismatch = struct.unpack_from('<B', buf, offset)[0]; offset += 1
    mismatch_base: str | None = None
    expected_base: str | None = None
    if has_mismatch:
        mismatch_base = chr(struct.unpack_from('<B', buf, offset)[0]); offset += 1
        expected_base = chr(struct.unpack_from('<B', buf, offset)[0]); offset += 1

    offset += 1  # view_hidden — consumed but not stored

    return Annotation(
        type=ann_type, start=start, end=end, label=label, strand=strand,
        color=color, score=score, tm=tm, gc_percent=gc_percent, notes=notes,
        parent_id=parent_id, mismatch_base=mismatch_base, expected_base=expected_base,
        id=ann_id,
    ), offset


# ── record metadata serialisation ─────────────────────────────────────────────

def serialize_record_meta(record: SequenceRecord, source_file: str = "") -> bytes:
    """Serialise the metadata portion of a SEQ RECORD (everything except encoded_data)."""
    buf = bytearray()
    hdr = record.header.encode('utf-8')
    buf += struct.pack('<H', len(hdr)) + hdr
    sf = source_file.encode('utf-8')
    buf += struct.pack('<H', len(sf)) + sf
    buf += struct.pack('<BB', SEQ_TYPE_NUCLEOTIDE, ENCODING_IUPAC4)
    buf += struct.pack('<I', len(record.annotations))
    for ann in record.annotations:
        buf += serialize_annotation(ann)
    return bytes(buf)


def deserialize_record_meta(buf: Any, offset: int) -> tuple[dict, int]:
    """Parse SEQ RECORD metadata (not encoded_data) from *buf* at *offset*."""
    header_len = struct.unpack_from('<H', buf, offset)[0]; offset += 2
    header = bytes(buf[offset:offset + header_len]).decode('utf-8'); offset += header_len
    sf_len = struct.unpack_from('<H', buf, offset)[0]; offset += 2
    source_file = bytes(buf[offset:offset + sf_len]).decode('utf-8'); offset += sf_len
    seq_type, encoding = struct.unpack_from('<BB', buf, offset); offset += 2
    ann_count = struct.unpack_from('<I', buf, offset)[0]; offset += 4
    annotations: list[Annotation] = []
    for _ in range(ann_count):
        ann, offset = deserialize_annotation(buf, offset)
        annotations.append(ann)
    return {
        'header': header,
        'source_file': source_file,
        'seq_type': seq_type,
        'encoding': encoding,
        'annotations': annotations,
    }, offset


# ── full SEQUENCES block ───────────────────────────────────────────────────────

@dataclass
class SequenceBlockEntry:
    """All parsed info for one sequence from the SEQUENCES block."""
    seq_id: str
    header: str
    source_file: str
    seq_type: int
    encoding: int
    annotations: list[Annotation] = field(default_factory=list)
    data_offset: int = 0   # byte offset within SEQUENCES block content to encoded_data
    data_length: int = 0   # number of encoded bytes
    base_count: int = 0    # number of decoded bases


def serialize_sequences_block(
    records: list[SequenceRecord],
    source_file: str = "",
) -> bytes:
    """Build the complete SEQUENCES block content (directory + records)."""
    n = len(records)
    dir_header_size = 4 + n * 40  # seq_count(4) + n × (uuid16 + offset8 + length8 + bases8)

    dir_entries: list[tuple[bytes, int, int, int]] = []
    record_chunks: list[bytes] = []
    current_offset = dir_header_size  # running offset within block content

    for rec in records:
        meta_bytes = serialize_record_meta(rec, source_file)
        seq_str: str = rec.sequence if isinstance(rec.sequence, str) else rec.sequence.to_str()  # type: ignore[union-attr]
        encoded = encode_sequence(seq_str)
        base_count = len(seq_str)
        data_offset_in_block = current_offset + len(meta_bytes)
        dir_entries.append((_uuid_to_bytes(rec.id), data_offset_in_block, len(encoded), base_count))
        record_chunks.append(meta_bytes + encoded)
        current_offset += len(meta_bytes) + len(encoded)

    buf = bytearray()
    buf += struct.pack('<I', n)
    for uid_b, data_off, data_len, base_cnt in dir_entries:
        buf += uid_b
        buf += struct.pack('<QQQ', data_off, data_len, base_cnt)
    for chunk in record_chunks:
        buf += chunk
    return bytes(buf)
