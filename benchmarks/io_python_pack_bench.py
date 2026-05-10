from __future__ import annotations

import sys
import time
from pathlib import Path


IUPAC4 = {
    "-": 0x0,
    "A": 0x1,
    "C": 0x2,
    "G": 0x3,
    "T": 0x4,
    "R": 0x5,
    "Y": 0x6,
    "M": 0x7,
    "K": 0x8,
    "S": 0x9,
    "W": 0xA,
    "H": 0xB,
    "B": 0xC,
    "V": 0xD,
    "D": 0xE,
    "N": 0xF,
}


def pack_fasta(path: Path) -> tuple[int, int, int]:
    bases = 0
    encoded_bytes = 0
    checksum = 2166136261
    pending = -1

    with path.open("rb") as fh:
        for raw_line in fh:
            if not raw_line or raw_line.startswith(b">"):
                continue
            for byte in raw_line:
                if byte in (10, 13, 32, 9):
                    continue
                ch = chr(byte).upper()
                nibble = IUPAC4.get(ch, 0xF)
                if pending < 0:
                    pending = nibble
                else:
                    packed = (pending << 4) | nibble
                    checksum = ((checksum ^ packed) * 16777619) & 0xFFFFFFFF
                    encoded_bytes += 1
                    pending = -1
                bases += 1

    if pending >= 0:
        packed = pending << 4
        checksum = ((checksum ^ packed) * 16777619) & 0xFFFFFFFF
        encoded_bytes += 1

    return bases, encoded_bytes, checksum


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: python io_python_pack_bench.py <input.fasta>")
        return 2

    path = Path(sys.argv[1])
    start = time.perf_counter()
    bases, encoded_bytes, checksum = pack_fasta(path)
    elapsed = time.perf_counter() - start

    print(f"python_seconds={elapsed:.6f}")
    print(f"bases={bases}")
    print(f"encoded_bytes={encoded_bytes}")
    print(f"checksum={checksum:08x}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
