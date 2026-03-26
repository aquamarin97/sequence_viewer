# model/alignment_data_model.py

from __future__ import annotations

from typing import List, Optional, Tuple

from PyQt5.QtCore import QObject, pyqtSignal


class AlignmentDataModel(QObject):
    """
    Tüm view'ların tek gerçek kaynağı (single source of truth).

    Bu model değiştiğinde ilgili sinyaller tetiklenir;
    view'lar bu sinyallere subscribe ederek kendilerini günceller.
    Böylece HeaderViewer / SequenceViewer / ConsensusRow / AnnotationLayer
    vb. hiçbir zaman birbirini doğrudan çağırmaz.

    Sinyaller
    ---------
    rowAppended(index, header, sequence)
        Sonuna yeni satır eklendi.

    rowRemoved(index)
        Belirtilen indeksteki satır silindi.

    rowMoved(from_index, to_index)
        Satır taşındı. View'lar tam listeyi yeniden çizmelidir.

    headerChanged(index, new_header)
        Sadece header metni değişti; sekans aynı kaldı.

    modelReset()
        Model tamamen temizlendi veya toplu olarak yeniden yüklendi.
        View'lar tüm içeriği silip sıfırdan çizmelidir.
    """

    rowAppended    = pyqtSignal(int, str, str)   # index, header, sequence
    rowRemoved     = pyqtSignal(int)              # index
    rowMoved       = pyqtSignal(int, int)         # from_index, to_index
    headerChanged  = pyqtSignal(int, str)         # index, new_header
    modelReset     = pyqtSignal()

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._rows: List[Tuple[str, str]] = []   # (header, sequence)

    # ------------------------------------------------------------------
    # Okuma API'si
    # ------------------------------------------------------------------

    def row_count(self) -> int:
        return len(self._rows)

    def get_row(self, index: int) -> Tuple[str, str]:
        """(header, sequence) döner. IndexError fırlatabiliır."""
        return self._rows[index]

    def get_header(self, index: int) -> str:
        return self._rows[index][0]

    def get_sequence(self, index: int) -> str:
        return self._rows[index][1]

    def all_rows(self) -> List[Tuple[str, str]]:
        """Tüm (header, sequence) çiftlerinin kopyasını döner."""
        return list(self._rows)

    @property
    def max_sequence_length(self) -> int:
        if not self._rows:
            return 0
        return max(len(seq) for _, seq in self._rows)

    # ------------------------------------------------------------------
    # Yazma API'si  →  her operasyon ilgili sinyali tetikler
    # ------------------------------------------------------------------

    def append_row(self, header: str, sequence: str) -> int:
        """
        Sona yeni satır ekler.
        rowAppended(index, header, sequence) sinyalini tetikler.
        Eklenen satırın indeksini döner.
        """
        index = len(self._rows)
        self._rows.append((header, sequence))
        self.rowAppended.emit(index, header, sequence)
        return index

    def remove_row(self, index: int) -> None:
        """
        Belirtilen satırı siler.
        rowRemoved(index) sinyalini tetikler.
        """
        if index < 0 or index >= len(self._rows):
            raise IndexError(f"Row index {index} out of range ({len(self._rows)} rows)")
        del self._rows[index]
        self.rowRemoved.emit(index)

    def move_row(self, from_index: int, to_index: int) -> None:
        """
        Satırı from_index'ten to_index'e taşır.
        İndeksler taşıma *öncesindeki* pozisyonlardır.
        rowMoved(from_index, to_index) sinyalini tetikler.
        """
        n = len(self._rows)
        if not (0 <= from_index < n and 0 <= to_index < n):
            raise IndexError(
                f"move_row({from_index}, {to_index}) out of range ({n} rows)"
            )
        if from_index == to_index:
            return

        row = self._rows.pop(from_index)
        self._rows.insert(to_index, row)
        self.rowMoved.emit(from_index, to_index)

    def set_header(self, index: int, new_header: str) -> None:
        """
        Sadece header metnini günceller; sekans değişmez.
        headerChanged(index, new_header) sinyalini tetikler.
        """
        if index < 0 or index >= len(self._rows):
            raise IndexError(f"Row index {index} out of range")
        _, seq = self._rows[index]
        self._rows[index] = (new_header, seq)
        self.headerChanged.emit(index, new_header)

    def clear(self) -> None:
        """
        Tüm satırları siler.
        modelReset() sinyalini tetikler.
        """
        self._rows.clear()
        self.modelReset.emit()

    def reset_from_list(self, rows: List[Tuple[str, str]]) -> None:
        """
        Modeli bir satır listesiyle tamamen yeniden yükler.
        modelReset() sinyalini tetikler.
        FASTA yükleme veya toplu güncelleme için kullanın.
        """
        self._rows = list(rows)
        self.modelReset.emit()