# file_io/native/jobs.py
from __future__ import annotations

import json
import subprocess
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from file_io.native.backend import run_native_manifest_job


def _utc_now_text() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _write_json_atomic(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(path.name + ".tmp")
    temp_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temp_path.replace(path)


@dataclass(frozen=True)
class NativeJobPaths:
    job_dir: Path
    manifest: Path
    status: Path
    events: Path
    stdout_log: Path
    stderr_log: Path
    result: Path
    artifacts: Path


@dataclass(frozen=True)
class NativeJobResult:
    command: str
    paths: NativeJobPaths
    process: subprocess.CompletedProcess[str]

    @property
    def returncode(self) -> int:
        return self.process.returncode

    def read_status(self) -> dict[str, Any] | None:
        if not self.paths.status.exists():
            return None
        return json.loads(self.paths.status.read_text(encoding="utf-8"))

    def read_result(self) -> dict[str, Any] | None:
        if not self.paths.result.exists():
            return None
        return json.loads(self.paths.result.read_text(encoding="utf-8"))


def native_job_paths(job_dir: str | Path) -> NativeJobPaths:
    root = Path(job_dir)
    return NativeJobPaths(
        job_dir=root,
        manifest=root / "manifest.json",
        status=root / "status.json",
        events=root / "events.ndjson",
        stdout_log=root / "stdout.log",
        stderr_log=root / "stderr.log",
        result=root / "result.json",
        artifacts=root / "artifacts",
    )


def create_motif_search_manifest(
    jobs_root: str | Path,
    *,
    input_snapshot: str | Path | None = None,
    query: str = "",
    max_mismatches: int = 0,
    search_forward: bool = True,
    search_reverse: bool = False,
    threads: int = 1,
    parameters: dict[str, Any] | None = None,
) -> NativeJobPaths:
    """Create a manifest-based native motif-search job directory."""
    job_id = f"motif_search_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
    paths = native_job_paths(Path(jobs_root) / job_id)
    paths.artifacts.mkdir(parents=True, exist_ok=True)

    merged_parameters: dict[str, Any] = {
        "query": query,
        "max_mismatches": max(0, int(max_mismatches)),
        "search_forward": bool(search_forward),
        "search_reverse": bool(search_reverse),
    }
    if parameters:
        merged_parameters.update(parameters)

    inputs: dict[str, str] = {}
    if input_snapshot is not None:
        inputs["project_snapshot"] = str(Path(input_snapshot))

    manifest = {
        "protocol_version": 1,
        "job_id": job_id,
        "command": "motif-search",
        "created_at": _utc_now_text(),
        "threads": max(1, int(threads)),
        "inputs": inputs,
        "parameters": merged_parameters,
        "outputs": {
            "result": paths.result.name,
            "artifacts": paths.artifacts.name,
        },
    }
    _write_json_atomic(paths.manifest, manifest)
    print(f"[NATIVE-JOB] created motif-search manifest={paths.manifest}")
    return paths


def run_motif_search_manifest(
    manifest_path: str | Path,
    *,
    native_path: str | Path | None = None,
) -> NativeJobResult:
    """Run an existing motif-search manifest with the central native executable."""
    manifest = Path(manifest_path)
    paths = native_job_paths(manifest.parent)
    process = run_native_manifest_job("motif-search", manifest, native_path=native_path)
    paths.stdout_log.write_text(process.stdout or "", encoding="utf-8")
    paths.stderr_log.write_text(process.stderr or "", encoding="utf-8")
    print(f"[NATIVE-JOB] motif-search returncode={process.returncode}")
    print(f"[NATIVE-JOB] stdout_log={paths.stdout_log}")
    print(f"[NATIVE-JOB] stderr_log={paths.stderr_log}")
    return NativeJobResult(command="motif-search", paths=paths, process=process)
