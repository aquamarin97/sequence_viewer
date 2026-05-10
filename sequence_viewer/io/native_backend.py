# sequence_viewer/io/native_backend.py
from __future__ import annotations
import os
import shutil
import subprocess
from pathlib import Path

def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]

def _executable_names() -> tuple[str, ...]:
    return ("fasta_to_sqx.exe", "fasta_to_sqx")

def find_fasta_to_sqx() -> Path | None:
    """Return the native FASTA->SQX converter path if one is available."""
    env_path = os.environ.get("SEQUENCE_VIEWER_FASTA_TO_SQX")
    if env_path:
        path = Path(env_path)
        if path.is_file():
            return path

    root = _repo_root()
    # Build klasörü veya native_tools içindeki binary'leri ara
    for directory in (root / "build" / "native", root / "native_tools"):
        for name in _executable_names():
            path = directory / name
            if path.is_file():
                return path

    # Sistem PATH'inde ara
    for name in _executable_names():
        found = shutil.which(name)
        if found:
            return Path(found)

    return None

def convert_fasta_to_sqx(
    fasta_path: str | Path,
    sqx_path: str | Path,
    *,
    project_name: str | None = None,
    converter_path: str | Path | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run the native converter and return its completed process."""
    converter = Path(converter_path) if converter_path is not None else find_fasta_to_sqx()
    if converter is None:
        raise FileNotFoundError("Native fasta_to_sqx converter was not found.")

    fasta = Path(fasta_path)
    sqx = Path(sqx_path)
    sqx.parent.mkdir(parents=True, exist_ok=True)
    
    command = [str(converter), str(fasta), str(sqx)]
    if project_name:
        command.append(project_name)

    # Log çıktısı: Komutun tam halini görmek hata ayıklamayı kolaylaştırır
    print(f"[NATIVE] Komut çalıştırılıyor: {' '.join(command)}")

    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
        creationflags=creationflags,
    )