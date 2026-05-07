# io/sqx/spec.py
from __future__ import annotations

MAGIC: bytes = b'SQX\x00\x01\x00\x00\x00'
FORMAT_VERSION: int = 1
APP_VERSION: str = "0.1.0"

BLOCK_PROJECT_META: int = 0x00000001
BLOCK_SEQUENCES: int    = 0x00000002
BLOCK_ANALYSES: int     = 0x00000003

BLOCK_DIR_ENTRY_SIZE: int = 22  # 4 (type) + 8 (offset) + 8 (length) + 2 (version)

SEQ_TYPE_UNKNOWN: int    = 0x00
SEQ_TYPE_NUCLEOTIDE: int = 0x01
SEQ_TYPE_PROTEIN: int    = 0x02

ENCODING_RAW_ASCII: int = 0x00
ENCODING_IUPAC4: int    = 0x01
ENCODING_IUPAC5: int    = 0x02

IUPAC4: dict[str, int] = {
    '-': 0x0, 'A': 0x1, 'C': 0x2, 'G': 0x3, 'T': 0x4,
    'R': 0x5, 'Y': 0x6, 'M': 0x7, 'K': 0x8, 'S': 0x9,
    'W': 0xA, 'H': 0xB, 'B': 0xC, 'V': 0xD, 'D': 0xE, 'N': 0xF,
}
IUPAC4_DECODE: dict[int, str] = {v: k for k, v in IUPAC4.items()}


class SQXFormatError(Exception):
    """Raised when an SQX file has an unrecognisable or corrupt structure."""

class SQXVersionError(Exception):
    """Raised when the SQX format version is newer than this reader supports."""


def encode_sequence(seq: str) -> bytes:
    """Pack a nucleotide string into 4-bit IUPAC bytes (2 bases per byte, big-nibble first)."""
    seq = seq.upper()
    n = len(seq)
    buf = bytearray((n + 1) // 2)
    for i, ch in enumerate(seq):
        nibble = IUPAC4.get(ch, 0xF)   # unknown bases → N
        if i % 2 == 0:
            buf[i // 2] = nibble << 4
        else:
            buf[i // 2] |= nibble
    return bytes(buf)


def decode_sequence(data: bytes | bytearray | memoryview, base_count: int) -> str:
    """Unpack 4-bit IUPAC bytes back into a nucleotide string."""
    chars: list[str] = []
    for i in range(base_count):
        byte = data[i // 2]
        nibble = (byte >> 4) & 0xF if i % 2 == 0 else byte & 0xF
        chars.append(IUPAC4_DECODE.get(nibble, 'N'))
    return ''.join(chars)
