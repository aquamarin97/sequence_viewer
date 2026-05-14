# sequence_viewer/app/sqx_conversion_worker.py
from __future__ import annotations

from pathlib import Path

from PyQt5.QtCore import QThread, pyqtSignal


class SQXConversionWorker(QThread):
    """Convert FASTA to SQX in the background."""

    finished = pyqtSignal(str)   # sqx_path; conversion succeeded
    failed = pyqtSignal(str)     # error message

    def __init__(self, fasta_path: Path, sqx_path: Path) -> None:
        super().__init__()
        self._fasta_path = fasta_path
        self._sqx_path = sqx_path

    def run(self) -> None:
        try:
            if self._try_native_conversion():
                return

            print("---" * 10)
            print("KONTROL: Islem PYTHON fallback ile yapiliyor.")
            print("---" * 10)
            self._run_python_conversion()

        except Exception as exc:
            self.failed.emit(str(exc))

    def _try_native_conversion(self) -> bool:
        from file_io.native.backend import (
            convert_fasta_to_sqx,
            find_fasta_to_sqx,
            native_backend_name,
        )

        converter = find_fasta_to_sqx()
        if converter is None:
            print("[NATIVE] backend=NONE; using PYTHON_FALLBACK")
            return False

        print("---" * 10)
        print(
            "KONTROL: Islem C++ native subprocess ile yapiliyor. "
            f"backend={native_backend_name(converter)} arac={converter}"
        )
        print("---" * 10)

        result = convert_fasta_to_sqx(
            self._fasta_path,
            self._sqx_path,
            project_name=self._fasta_path.stem,
            converter_path=converter,
        )

        if result.returncode != 0:
            print(
                "[NATIVE] conversion failed; "
                f"backend={native_backend_name(converter)} returncode={result.returncode}; "
                "using PYTHON_FALLBACK"
            )
            if result.stderr:
                print(f"[NATIVE:stderr] {result.stderr.strip()}")
            return False

        print(f"[NATIVE] conversion succeeded; backend={native_backend_name(converter)}")
        self.finished.emit(str(self._sqx_path))
        return True

    def _run_python_conversion(self) -> None:
        from file_io.parsers.fasta_parser import FASTAParser
        from file_io.sqx.block_types.project_meta import ProjectMeta
        from file_io.sqx.writer import SQXWriter
        from sequence_viewer.model.sequence_record import SequenceRecord

        records = [
            SequenceRecord(header=h, sequence=s)
            for h, s in FASTAParser().parse(self._fasta_path)
        ]
        if not records:
            self.failed.emit("Dosyada sequence bulunamadi.")
            return

        SQXWriter().write(
            self._sqx_path,
            records,
            ProjectMeta(project_name=self._fasta_path.stem),
            source_file=self._fasta_path.name,
        )
        self.finished.emit(str(self._sqx_path))


class SQXLoadWorker(QThread):
    """Load an existing .sqx file and emit the open reader for lazy access."""

    reader_ready = pyqtSignal(object)  # SQXReader: directory loaded, records lazy
    failed = pyqtSignal(str)

    def __init__(self, sqx_path: Path) -> None:
        super().__init__()
        self._sqx_path = sqx_path

    def run(self) -> None:
        try:
            from file_io.sqx.reader import SQXReader

            print(f"[LOADER] SQX dosyasi okunuyor: {self._sqx_path.name}")
            reader = SQXReader(self._sqx_path)
            reader.open()
            print(f"[LOADER] {reader.sequence_count()} kayit dizini yuklendi (lazy).")
            self.reader_ready.emit(reader)
        except Exception as exc:
            print(f"[LOADER ERROR] {exc}")
            self.failed.emit(str(exc))
