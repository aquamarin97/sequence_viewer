# sequence_viewer/model/lazy_sequence.py
from __future__ import annotations

import mmap
from copy import deepcopy


class LazySequence:
    """
    Wraps a 4-bit IUPAC-encoded region of an mmap and exposes a str-like interface.
    Sequences shorter than EAGER_THRESHOLD are decoded immediately and cached.
    """

    EAGER_THRESHOLD: int = 50_000

    _IUPAC4_DECODE: dict[int, str] = {
        0x0: '-', 0x1: 'A', 0x2: 'C', 0x3: 'G', 0x4: 'T',
        0x5: 'R', 0x6: 'Y', 0x7: 'M', 0x8: 'K', 0x9: 'S',
        0xA: 'W', 0xB: 'H', 0xC: 'B', 0xD: 'V', 0xE: 'D', 0xF: 'N',
    }

    def __init__(self, mmap_obj: mmap.mmap, offset: int, base_count: int, encoding: int) -> None:
        self._mmap = mmap_obj
        self._offset = offset
        self._base_count = base_count
        self._encoding = encoding
        self._cache: str | None = None
        if base_count < self.EAGER_THRESHOLD:
            self._cache = self._decode_raw(0, base_count)

    # ------------------------------------------------------------------ str-like interface

    def __len__(self) -> int:
        return self._base_count

    def __getitem__(self, key: int | slice) -> str:
        if isinstance(key, int):
            if key < 0:
                key += self._base_count
            if not 0 <= key < self._base_count:
                raise IndexError("LazySequence index out of range")
            if self._cache is not None:
                return self._cache[key]
            return self._decode_raw(key, key + 1)
        if isinstance(key, slice):
            start, stop, step = key.indices(self._base_count)
            s = self.decode_range(start, stop)
            return s if step == 1 else s[::step]
        raise TypeError(f"indices must be int or slice, not {type(key).__name__}")

    def __iter__(self):
        if self._cache is not None:
            yield from self._cache
            return
        for i in range(self._base_count):
            yield self._decode_raw(i, i + 1)

    def __str__(self) -> str:
        return self.to_str()

    def __repr__(self) -> str:
        return f"LazySequence(base_count={self._base_count})"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, str):
            return self.to_str() == other
        if isinstance(other, LazySequence):
            return self._base_count == other._base_count and self.to_str() == other.to_str()
        return NotImplemented

    # ------------------------------------------------------------------ deepcopy for undo/redo

    def __deepcopy__(self, memo: dict) -> str:
        # Snapshots store a plain str so mmap lifetime doesn't constrain undo history.
        result = self.to_str()
        memo[id(self)] = result
        return result

    # ------------------------------------------------------------------ public API

    def decode_range(self, start: int, end: int) -> str:
        """Decode bases [start, end) — the hot path for viewport rendering."""
        if self._cache is not None:
            return self._cache[start:end]
        return self._decode_raw(start, end)

    def to_str(self) -> str:
        """Return the full sequence as a plain str (decodes if not cached)."""
        if self._cache is not None:
            return self._cache
        return self._decode_raw(0, self._base_count)

    # ------------------------------------------------------------------ internal

    def _decode_raw(self, start: int, end: int) -> str:
        if start >= end:
            return ''
        byte_start = start // 2
        byte_end = (end - 1) // 2 + 1
        raw = self._mmap[self._offset + byte_start:self._offset + byte_end]
        chars: list[str] = []
        decode = self._IUPAC4_DECODE
        for i in range(start, end):
            raw_byte_idx = i // 2 - byte_start
            byte = raw[raw_byte_idx]
            nibble = (byte >> 4) & 0xF if i % 2 == 0 else byte & 0xF
            chars.append(decode.get(nibble, 'N'))
        return ''.join(chars)
