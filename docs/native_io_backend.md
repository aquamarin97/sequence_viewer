# Native IO Backend

The sequence viewer runs native C++ work as isolated subprocesses. Python owns
the GUI, project state, monitoring, and fallback behavior; native tools own
stateless compute-heavy jobs.

## Current Tools

- `native_tools/fasta_to_sqx.cpp`: current C++ source for FASTA to SQX
  conversion and the first central native CLI commands.
- `sequence_viewer/io/native_backend.py`: Python wrapper that finds and runs
  native executables.
- `sequence_viewer/app/sqx_conversion_worker.py`: background worker that tries
  native conversion first and falls back to the Python SQX writer if needed.

## Central CLI

Preferred executable name:

```powershell
sequence_viewer_native.exe
```

Supported commands:

```powershell
sequence_viewer_native.exe capabilities
sequence_viewer_native.exe --version
sequence_viewer_native.exe fasta-to-sqx input.fasta output.sqx ProjectName
sequence_viewer_native.exe motif-search jobs/job_000001/manifest.json
```

The legacy call shape is still supported when the same source is built as
`fasta_to_sqx.exe`:

```powershell
fasta_to_sqx.exe input.fasta output.sqx ProjectName
```

## Build

On Windows with `g++` available:

```powershell
New-Item -ItemType Directory -Force build/native | Out-Null
g++ -O3 -std=c++17 native_tools/fasta_to_sqx.cpp -o build/native/sequence_viewer_native.exe
```

Legacy build remains possible:

```powershell
g++ -O3 -std=c++17 native_tools/fasta_to_sqx.cpp -o build/native/fasta_to_sqx.exe
```

## Lookup Order

`find_sequence_viewer_native()` checks:

1. `SEQUENCE_VIEWER_NATIVE`
2. `build/native/sequence_viewer_native.exe`
3. `native_tools/sequence_viewer_native.exe`
4. `PATH`

`find_fasta_to_sqx()` checks:

1. `SEQUENCE_VIEWER_FASTA_TO_SQX`
2. the central native executable above
3. `build/native/fasta_to_sqx.exe`
4. `native_tools/fasta_to_sqx.exe`
5. `PATH`

If no native converter is found, the application keeps using the existing
Python conversion path.

## Current SQX Scope

The native converter writes SQX `PROJECT_META` and `SEQUENCES` blocks for FASTA
nucleotide records. Annotation and analysis blocks are intentionally not part of
this first native import path. Future compute jobs should write result artifacts
that Python imports into the live project; project save then persists accepted
state into SQX.

## Backend Visibility

Python prints the selected execution path before running native work:

```text
[NATIVE] backend=CENTRAL_NATIVE executable=...
[NATIVE] backend=LEGACY_FASTA_TO_SQX executable=...
[NATIVE] backend=NONE; using PYTHON_FALLBACK
```

Manifest jobs are central-native only:

```text
[NATIVE-JOB] backend=CENTRAL_NATIVE executable=...
[NATIVE-JOB] command=... motif-search .../manifest.json
```
