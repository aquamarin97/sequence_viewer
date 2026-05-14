# Native Job Protocol

This document defines the direction for long-running C++ subprocess jobs such as
primer design, multiplex design, motif search, indexing, and alignment.

## Roles

- Python GUI is the orchestrator. It writes input snapshots, starts subprocesses,
  monitors status, imports results, and owns the live project model.
- C++ native tools are stateless workers. They read declared inputs, perform one
  job, and write declared outputs.
- SQX is the project document. Native jobs should not mutate an open SQX file
  while Python is reading it.

## Job Directory

Each job should run inside an isolated directory:

```text
jobs/
  job_<id>/
    manifest.json
    status.json
    events.ndjson
    stdout.log
    stderr.log
    result.json
    artifacts/
```

## Manifest

`manifest.json` is written by Python before the subprocess starts.

```json
{
  "protocol_version": 1,
  "job_id": "job_000001",
  "command": "motif-search",
  "created_at": "2026-05-11T00:00:00Z",
  "threads": 4,
  "inputs": {
    "project_snapshot": "input.sqx"
  },
  "parameters": {
    "query": "ATGC",
    "max_mismatches": 1,
    "search_forward": true,
    "search_reverse": false
  },
  "outputs": {
    "result": "result.json",
    "artifacts": "artifacts"
  }
}
```

Python can create and run the first motif-search skeleton through:

```python
from file_io.native.jobs import (
    create_motif_search_manifest,
    run_motif_search_manifest,
)

paths = create_motif_search_manifest("jobs", query="ATGC", max_mismatches=1)
result = run_motif_search_manifest(paths.manifest)
```

The current native implementation validates the manifest path, writes
`status.json`, appends `events.ndjson`, creates `artifacts/`, and writes a
skeleton `result.json` with empty `hits` and `annotations`.

## Status

Native tools update `status.json` atomically:

1. write `status.json.tmp`
2. flush and close
3. rename to `status.json`

Suggested shape:

```json
{
  "state": "running",
  "step": "scoring",
  "progress": 42.5,
  "message": "Scoring candidate primer pairs"
}
```

Allowed states:

```text
queued
running
succeeded
failed
cancelled
```

## Events

`events.ndjson` is append-only structured log output for the monitoring UI.
Each line is one JSON object.

```json
{"level":"info","step":"indexing","progress":10,"message":"Building target index"}
{"level":"warning","step":"filtering","message":"Low complexity region skipped"}
```

Plain `stdout.log` and `stderr.log` can still be kept for raw diagnostics.

## Results

Native tools write final result artifacts atomically. Python only imports a
result after the process exits with code `0` and the declared result file exists.

For annotation-producing jobs, C++ should write result data. Python converts that
result into application `Annotation` objects and applies it to the live model.
Project save is responsible for persisting accepted annotations into SQX.

## Cancellation

Python may request cooperative cancellation by creating:

```text
cancel.requested
```

Long-running native jobs should check for this file between major steps and exit
with a cancelled status when possible. Python may still terminate the process if
the worker does not stop.

## Exit Codes

Recommended exit code meanings:

```text
0  succeeded
1  runtime error
2  usage or invalid manifest
3  input validation failed
4  cancelled
```
