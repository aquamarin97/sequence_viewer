# model/alignment_data_model.py
"""
Tüm view'ların tek gerçek kaynağı (single source of truth).

Adım 1 değişiklikleri
---------------------
* İç depolama List[Tuple[str,str]] → List[SequenceRecord].
* is_aligned bayrağı ve AlignmentMetadata eklendi.
* global_annotations listesi eklendi (is_aligned=True iken anlamlı).
* Per-sequence annotation CRUD sinyalleri eklendi.
* Tüm eski sinyaller ve metot imzaları korundu — view katmanı değişmez.

Backward-compatible public API
-------------------------------
append_row / remove_row / move_row / set_header / clear / reset_from_list
get_row / get_header / get_sequence / all_rows / row_count / max_sequence_length
→ Bunların imzası ve dönüş tipleri değişmedi.

Yeni public API
---------------
get_record(index) → SequenceRecord
all_records()     → List[SequenceRecord]

# Per-sequence annotation CRUD
add_annotation(row_index, annotation)
remove_annotation(row_index, annotation_id)
update_annotation(row_index, annotation)
get_annotations(row_index) → List[Annotation]

# Global (alignment-level) annotation CRUD
add_global_annotation(annotation)
remove_global_annotation(annotation_id)
update_global_annotation(annotation)

# Hizalama durumu
set_aligned(metadata)   → is_aligned=True, metadata kaydedilir
clear_alignment()       → is_aligned=False, metadata temizlenir
"""

from __future__ import annotations

from typing import List, Optional, Tuple

from PyQt5.QtCore import QObject, pyqtSignal

from model.alignment_metadata import AlignmentMetadata
from model.annotation import Annotation
from model.sequence_record import SequenceRecord


class AlignmentDataModel(QObject):
    """
    MSA viewer'ın merkezi veri modeli.

    Sinyaller — mevcut (backward-compatible)
    -----------------------------------------
    rowAppended(index, header, sequence)
    rowRemoved(index)
    rowMoved(from_index, to_index)
    headerChanged(index, new_header)
    modelReset()

    Sinyaller — yeni (per-sequence annotation)
    -------------------------------------------
    annotationAdded(row_index, annotation)
    annotationRemoved(row_index, annotation_id)
    annotationUpdated(row_index, annotation)
    annotationsReset(row_index)

    Sinyaller — yeni (global annotation)
    -------------------------------------
    globalAnnotationAdded(annotation)
    globalAnnotationRemoved(annotation_id)
    globalAnnotationUpdated(annotation)

    Sinyaller — yeni (hizalama durumu)
    ------------------------------------
    alignmentStateChanged(is_aligned)
    """

    # --- Mevcut sinyaller (değişmedi) ---
    rowAppended    = pyqtSignal(int, str, str)
    rowRemoved     = pyqtSignal(int)
    rowMoved       = pyqtSignal(int, int)
    headerChanged  = pyqtSignal(int, str)
    modelReset     = pyqtSignal()

    # --- Yeni: per-sequence annotation sinyalleri ---
    annotationAdded   = pyqtSignal(int, object)   # row_index, Annotation
    annotationRemoved = pyqtSignal(int, str)       # row_index, annotation_id
    annotationUpdated = pyqtSignal(int, object)    # row_index, Annotation
    annotationsReset  = pyqtSignal(int)            # row_index

    # --- Yeni: global annotation sinyalleri ---
    globalAnnotationAdded   = pyqtSignal(object)  # Annotation
    globalAnnotationRemoved = pyqtSignal(str)      # annotation_id
    globalAnnotationUpdated = pyqtSignal(object)   # Annotation

    # --- Yeni: hizalama durumu ---
    alignmentStateChanged = pyqtSignal(bool)       # is_aligned

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._rows: List[SequenceRecord] = []

        # Hizalama durumu
        self._is_aligned:     bool                        = False
        self._alignment_meta: Optional[AlignmentMetadata] = None

        # Alignment-level (global) annotasyonlar
        # Yalnızca is_aligned=True iken anlamlıdır
        self._global_annotations: List[Annotation] = []

    # ==================================================================
    # Hizalama durumu
    # ==================================================================

    @property
    def is_aligned(self) -> bool:
        return self._is_aligned

    @property
    def alignment_meta(self) -> Optional[AlignmentMetadata]:
        return self._alignment_meta

    def set_aligned(self, metadata: AlignmentMetadata) -> None:
        """
        Hizalama tamamlandığında çağrılır (kullanıcı 'Align' aksiyonu).
        is_aligned=True yapılır, metadata kaydedilir.
        """
        self._is_aligned     = True
        self._alignment_meta = metadata
        self.alignmentStateChanged.emit(True)

    def clear_alignment(self) -> None:
        """
        Hizalama kaldırıldığında çağrılır.
        is_aligned=False, metadata ve global annotasyonlar temizlenir.
        """
        self._is_aligned          = False
        self._alignment_meta      = None
        self._global_annotations.clear()
        self.alignmentStateChanged.emit(False)

    # ==================================================================
    # Okuma API'si — backward-compatible
    # ==================================================================

    def row_count(self) -> int:
        return len(self._rows)

    def get_row(self, index: int) -> Tuple[str, str]:
        """(header, sequence) döner. Eski API uyumluluğu."""
        r = self._rows[index]
        return r.header, r.sequence

    def get_header(self, index: int) -> str:
        return self._rows[index].header

    def get_sequence(self, index: int) -> str:
        return self._rows[index].sequence

    def all_rows(self) -> List[Tuple[str, str]]:
        """[(header, sequence), …] döner. Eski API uyumluluğu."""
        return [(r.header, r.sequence) for r in self._rows]

    @property
    def max_sequence_length(self) -> int:
        if not self._rows:
            return 0
        return max(len(r.sequence) for r in self._rows)

    # --- Yeni okuma API'si ---

    def get_record(self, index: int) -> SequenceRecord:
        """SequenceRecord'u döner. IndexError fırlatabiliır."""
        return self._rows[index]

    def all_records(self) -> List[SequenceRecord]:
        """Tüm SequenceRecord'ların kopyasını döner."""
        return list(self._rows)

    # ==================================================================
    # Yazma API'si — satır CRUD (backward-compatible)
    # ==================================================================

    def append_row(self, header: str, sequence: str) -> int:
        """
        Sona yeni satır ekler.
        rowAppended(index, header, sequence) sinyalini tetikler.
        """
        record = SequenceRecord(header=header, sequence=sequence)
        index  = len(self._rows)
        self._rows.append(record)
        self.rowAppended.emit(index, header, sequence)
        return index

    def remove_row(self, index: int) -> None:
        """
        Belirtilen satırı siler.
        rowRemoved(index) sinyalini tetikler.
        """
        if index < 0 or index >= len(self._rows):
            raise IndexError(
                f"Row index {index} out of range ({len(self._rows)} rows)"
            )
        del self._rows[index]
        self.rowRemoved.emit(index)

    def move_row(self, from_index: int, to_index: int) -> None:
        """
        Satırı taşır. rowMoved(from_index, to_index) sinyalini tetikler.
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
        Header metnini günceller.
        headerChanged(index, new_header) sinyalini tetikler.
        """
        if index < 0 or index >= len(self._rows):
            raise IndexError(f"Row index {index} out of range")
        self._rows[index].header = new_header
        self.headerChanged.emit(index, new_header)

    def clear(self) -> None:
        """Tüm satırları ve global annotasyonları siler."""
        self._rows.clear()
        self._global_annotations.clear()
        self._is_aligned     = False
        self._alignment_meta = None
        self.modelReset.emit()

    def reset_from_list(self, rows: List[Tuple[str, str]]) -> None:
        """
        Tuple listesiyle toplu yeniden yükleme. Eski API uyumluluğu.
        modelReset() sinyalini tetikler.
        """
        self._rows = [
            SequenceRecord(header=h, sequence=s)
            for h, s in rows
        ]
        self._global_annotations.clear()
        self._is_aligned     = False
        self._alignment_meta = None
        self.modelReset.emit()

    def reset_from_records(self, records: List[SequenceRecord]) -> None:
        """
        SequenceRecord listesiyle toplu yeniden yükleme.
        Persistence katmanı (Adım 4) bu metodu kullanacak.
        modelReset() sinyalini tetikler.
        """
        self._rows = list(records)
        self.modelReset.emit()

    # ==================================================================
    # Per-sequence annotation CRUD
    # ==================================================================

    def add_annotation(self, row_index: int, annotation: Annotation) -> None:
        """
        Belirtilen satıra annotation ekler.
        annotationAdded(row_index, annotation) sinyalini tetikler.
        """
        self._rows[row_index].add_annotation(annotation)
        self.annotationAdded.emit(row_index, annotation)

    def remove_annotation(self, row_index: int, annotation_id: str) -> None:
        """
        Annotation siler.
        annotationRemoved(row_index, annotation_id) sinyalini tetikler.
        """
        self._rows[row_index].remove_annotation(annotation_id)
        self.annotationRemoved.emit(row_index, annotation_id)

    def update_annotation(self, row_index: int, annotation: Annotation) -> None:
        """
        Annotation günceller.
        annotationUpdated(row_index, annotation) sinyalini tetikler.
        """
        self._rows[row_index].update_annotation(annotation)
        self.annotationUpdated.emit(row_index, annotation)

    def get_annotations(self, row_index: int) -> List[Annotation]:
        """Belirtilen satırın annotation listesinin kopyasını döner."""
        return list(self._rows[row_index].annotations)

    def clear_annotations(self, row_index: int) -> None:
        """Belirtilen satırın tüm annotation'larını siler."""
        self._rows[row_index].clear_annotations()
        self.annotationsReset.emit(row_index)

    def find_annotation(
        self, annotation_id: str
    ) -> Optional[Tuple[int, Annotation]]:
        """
        annotation_id'ye göre (row_index, annotation) çiftini döner.
        Bulunamazsa None.
        """
        for i, record in enumerate(self._rows):
            for ann in record.annotations:
                if ann.id == annotation_id:
                    return i, ann
        return None

    def all_annotations_flat(self) -> List[Tuple[int, Annotation]]:
        """
        Tüm satırlardaki annotation'ları (row_index, annotation) çiftleri
        olarak düz liste halinde döner.

        Geçici görüntüleme mantığı (Adım 2 tamamlanana kadar workspace
        bu metodu kullanabilir).
        """
        result: List[Tuple[int, Annotation]] = []
        for i, record in enumerate(self._rows):
            for ann in record.annotations:
                result.append((i, ann))
        return result

    # ==================================================================
    # Global annotation CRUD
    # ==================================================================

    @property
    def global_annotations(self) -> List[Annotation]:
        """Global annotation listesini döner (salt okunur referans)."""
        return self._global_annotations

    def add_global_annotation(self, annotation: Annotation) -> None:
        """
        Global annotation ekler.
        globalAnnotationAdded(annotation) sinyalini tetikler.
        Yalnızca is_aligned=True iken çağrılmalıdır.
        """
        if any(a.id == annotation.id for a in self._global_annotations):
            raise ValueError(
                f"Global annotation id '{annotation.id}' already exists."
            )
        self._global_annotations.append(annotation)
        self.globalAnnotationAdded.emit(annotation)

    def remove_global_annotation(self, annotation_id: str) -> None:
        """Global annotation siler. globalAnnotationRemoved sinyalini tetikler."""
        for i, ann in enumerate(self._global_annotations):
            if ann.id == annotation_id:
                del self._global_annotations[i]
                self.globalAnnotationRemoved.emit(annotation_id)
                return
        raise KeyError(f"Global annotation '{annotation_id}' not found.")

    def update_global_annotation(self, annotation: Annotation) -> None:
        """Global annotation günceller. globalAnnotationUpdated sinyalini tetikler."""
        for i, ann in enumerate(self._global_annotations):
            if ann.id == annotation.id:
                self._global_annotations[i] = annotation
                self.globalAnnotationUpdated.emit(annotation)
                return
        raise KeyError(f"Global annotation '{annotation.id}' not found.")