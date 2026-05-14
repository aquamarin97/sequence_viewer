# file_io/native/backend.py
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path


def _native_root() -> Path:
    return Path(__file__).resolve().parent


def _native_executable_names() -> tuple[str, ...]:
    return ("sequence_viewer_native.exe", "sequence_viewer_native")


def _legacy_fasta_to_sqx_names() -> tuple[str, ...]:
    return ("fasta_to_sqx.exe", "fasta_to_sqx")


def _native_search_directories() -> tuple[Path, ...]:
    return (_native_root() / "bin",)


def _path_from_env(var_name: str) -> Path | None:
    env_path = os.environ.get(var_name)
    if not env_path:
        return None

    path = Path(env_path)
    if path.is_file():
        return path
    return None


def _find_executable(names: tuple[str, ...]) -> Path | None:
    for directory in _native_search_directories():
        for name in names:
            path = directory / name
            if path.is_file():
                return path

    for name in names:
        found = shutil.which(name)
        if found:
            return Path(found)

    return None


def _is_central_native(path: Path) -> bool:
    return path.stem.lower() in {"sequence_viewer_native", "sequence-viewer-native"}


def native_backend_name(path: str | Path) -> str:
    """Return a short user-visible native backend label."""
    native_path = Path(path)
    if _is_central_native(native_path):
        return "CENTRAL_NATIVE"
    return "LEGACY_FASTA_TO_SQX"


def find_sequence_viewer_native() -> Path | None:
    """Return the central native subprocess tool if one is available."""
    return (
        _path_from_env("SEQUENCE_VIEWER_NATIVE")
        or _find_executable(_native_executable_names())
    )


def find_fasta_to_sqx() -> Path | None:
    """Return a native tool that can perform FASTA->SQX conversion."""
    return (
        _path_from_env("SEQUENCE_VIEWER_FASTA_TO_SQX")
        or find_sequence_viewer_native()
        or _find_executable(_legacy_fasta_to_sqx_names())
    )


def native_capabilities(
    *,
    native_path: str | Path | None = None,
) -> dict | None:
    """Return central native capabilities, or None if the central tool is absent."""
    native = Path(native_path) if native_path is not None else find_sequence_viewer_native()
    if native is None:
        return None

    result = subprocess.run(
        [str(native), "capabilities"],
        capture_output=True,
        text=True,
        check=False,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    if result.returncode != 0:
        return None
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return None


def convert_fasta_to_sqx(
    fasta_path: str | Path,
    sqx_path: str | Path,
    *,
    project_name: str | None = None,
    converter_path: str | Path | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run the native FASTA->SQX converter and return its completed process."""
    converter = Path(converter_path) if converter_path is not None else find_fasta_to_sqx()
    if converter is None:
        raise FileNotFoundError("Native FASTA->SQX converter was not found.")

    fasta = Path(fasta_path)
    sqx = Path(sqx_path)
    sqx.parent.mkdir(parents=True, exist_ok=True)

    backend = native_backend_name(converter)
    if _is_central_native(converter):
        command = [str(converter), "fasta-to-sqx", str(fasta), str(sqx)]
    else:
        command = [str(converter), str(fasta), str(sqx)]
    if project_name:
        command.append(project_name)

    print(f"[NATIVE] backend={backend} executable={converter}")
    print(f"[NATIVE] command={' '.join(command)}")

    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
        creationflags=creationflags,
    )


def run_native_manifest_job(
    command_name: str,
    manifest_path: str | Path,
    *,
    native_path: str | Path | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run a manifest-based central native job."""
    native = Path(native_path) if native_path is not None else find_sequence_viewer_native()
    if native is None:
        raise FileNotFoundError("Central native executable was not found.")
    if not _is_central_native(native):
        raise ValueError(f"Manifest jobs require CENTRAL_NATIVE, got: {native}")

    manifest = Path(manifest_path)
    command = [str(native), command_name, str(manifest)]
    print(f"[NATIVE-JOB] backend=CENTRAL_NATIVE executable={native}")
    print(f"[NATIVE-JOB] command={' '.join(command)}")

    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
        creationflags=creationflags,
    )
