# Native IO Backend

The sequence viewer can convert FASTA files to SQX through a native helper before
loading them in Python.

## Files

- `native_tools/fasta_to_sqx.cpp`: C++ FASTA to SQX converter.
- `sequence_viewer/io/native_backend.py`: Python wrapper that finds and runs the
  converter.
- `sequence_viewer/app/sqx_conversion_worker.py`: background worker that tries
  the native converter first and falls back to the Python SQX writer if the
  native tool is unavailable.

## Build

On Windows with `g++` available:

```powershell
New-Item -ItemType Directory -Force build/native | Out-Null
g++ -O3 -std=c++17 native_tools/fasta_to_sqx.cpp -o build/native/fasta_to_sqx.exe
```

## Lookup Order

`find_fasta_to_sqx()` checks:

1. `SEQUENCE_VIEWER_FASTA_TO_SQX`
2. `build/native/fasta_to_sqx.exe`
3. `native_tools/fasta_to_sqx.exe`
4. `PATH`

If no converter is found, the application keeps using the existing Python
conversion path.

## Current Scope

The converter writes SQX `PROJECT_META` and `SEQUENCES` blocks for FASTA
nucleotide records. Annotation and analysis blocks are intentionally not part of
this first native import path.
