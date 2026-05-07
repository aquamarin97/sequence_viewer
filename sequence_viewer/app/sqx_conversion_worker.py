# sequence_viewer/app/sqx_conversion_worker.py
from __future__ import annotations

from pathlib import Path

from PyQt5.QtCore import QThread, pyqtSignal


class SQXConversionWorker(QThread):
    """FASTA → SQX dönüşümünü arka planda yapar."""
    finished = pyqtSignal(str)   # sqx_path — dönüşüm başarılı
    failed   = pyqtSignal(str)   # hata mesajı

    def __init__(self, fasta_path: Path, sqx_path: Path) -> None:
        super().__init__()
        self._fasta_path = fasta_path
        self._sqx_path   = sqx_path

    def run(self) -> None:
        try:
            from sequence_viewer.io.parsers.fasta_parser import FASTAParser
            from sequence_viewer.io.sqx.block_types.project_meta import ProjectMeta
            from sequence_viewer.io.sqx.writer import SQXWriter
            from sequence_viewer.model.sequence_record import SequenceRecord

            records = [
                SequenceRecord(header=h, sequence=s)
                for h, s in FASTAParser().parse(self._fasta_path)
            ]
            if not records:
                self.failed.emit("Dosyada sequence bulunamadi.")
                return
            SQXWriter().write(
                self._sqx_path, records,
                ProjectMeta(project_name=self._fasta_path.stem),
                source_file=self._fasta_path.name,
            )
            self.finished.emit(str(self._sqx_path))
        except Exception as exc:
            self.failed.emit(str(exc))


class SQXLoadWorker(QThread):
    """Mevcut .sqx dosyasini arka planda acar ve tum kayitlari okur."""
    records_ready = pyqtSignal(object, object)  # (SQXReader, list[SequenceRecord])
    failed        = pyqtSignal(str)

    def __init__(self, sqx_path: Path) -> None:
        super().__init__()
        self._sqx_path = sqx_path

    def run(self) -> None:
        try:
            from sequence_viewer.io.sqx.reader import SQXReader
            reader = SQXReader(self._sqx_path)
            reader.open()
            records = [
                reader.read_sequence_record(i)
                for i in range(reader.sequence_count())
            ]
            self.records_ready.emit(reader, records)
        except Exception as exc:
            self.failed.emit(str(exc))
