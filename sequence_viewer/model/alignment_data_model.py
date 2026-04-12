# model/alignment_data_model.py
from __future__ import annotations
from copy import deepcopy
from dataclasses import dataclass
from typing import List, Optional, Tuple
from PyQt5.QtCore import QObject, pyqtSignal
from sequence_viewer.model.alignment_metadata import AlignmentMetadata
from sequence_viewer.model.annotation import Annotation
from sequence_viewer.model.sequence_record import SequenceRecord


@dataclass
class AlignmentDataModelSnapshot:
    rows: List[SequenceRecord]
    is_aligned: bool
    alignment_meta: Optional[AlignmentMetadata]
    global_annotations: List[Annotation]
    consensus_annotations: List[Annotation]

class AlignmentDataModel(QObject):
    rowAppended    = pyqtSignal(int, str, str)
    rowRemoved     = pyqtSignal(int)
    rowMoved       = pyqtSignal(int, int)
    headerChanged  = pyqtSignal(int, str)
    modelReset     = pyqtSignal()
    annotationAdded   = pyqtSignal(int, object)
    annotationRemoved = pyqtSignal(int, str)
    annotationUpdated = pyqtSignal(int, object)
    annotationsReset  = pyqtSignal(int)
    globalAnnotationAdded   = pyqtSignal(object)
    globalAnnotationRemoved = pyqtSignal(str)
    globalAnnotationUpdated = pyqtSignal(object)
    consensusAnnotationAdded   = pyqtSignal(object)
    consensusAnnotationRemoved = pyqtSignal(str)
    consensusAnnotationUpdated = pyqtSignal(object)
    alignmentStateChanged = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._rows: List[SequenceRecord] = []
        self._is_aligned = False
        self._alignment_meta = None
        self._global_annotations: List[Annotation] = []
        self._consensus_annotations: List[Annotation] = []

    @property
    def is_aligned(self): return self._is_aligned
    @property
    def alignment_meta(self): return self._alignment_meta

    def set_aligned(self, metadata):
        self._is_aligned = True
        self._alignment_meta = metadata
        self.alignmentStateChanged.emit(True)

    def clear_alignment(self):
        self._is_aligned = False
        self._alignment_meta = None
        self._global_annotations.clear()
        self._consensus_annotations.clear()
        self.alignmentStateChanged.emit(False)

    def row_count(self): return len(self._rows)
    def get_row(self, index):
        r = self._rows[index]; return r.header, r.sequence
    def get_header(self, index): return self._rows[index].header
    def get_sequence(self, index): return self._rows[index].sequence
    def all_rows(self): return [(r.header, r.sequence) for r in self._rows]
    @property
    def max_sequence_length(self):
        if not self._rows: return 0
        return max(len(r.sequence) for r in self._rows)
    def get_record(self, index): return self._rows[index]
    def all_records(self): return list(self._rows)

    def append_row(self, header, sequence):
        record = SequenceRecord(header=header, sequence=sequence)
        index = len(self._rows)
        self._rows.append(record)
        self.rowAppended.emit(index, header, sequence)
        return index

    def remove_row(self, index):
        if index < 0 or index >= len(self._rows):
            raise IndexError(f"Row index {index} out of range")
        del self._rows[index]
        self.rowRemoved.emit(index)

    def move_row(self, from_index, to_index):
        n = len(self._rows)
        if not (0 <= from_index < n and 0 <= to_index < n):
            raise IndexError(f"move_row out of range")
        if from_index == to_index: return
        row = self._rows.pop(from_index)
        self._rows.insert(to_index, row)
        self.rowMoved.emit(from_index, to_index)

    def set_header(self, index, new_header):
        if index < 0 or index >= len(self._rows): raise IndexError
        self._rows[index].header = new_header
        self.headerChanged.emit(index, new_header)

    def clear(self):
        self._rows.clear()
        self._global_annotations.clear()
        self._consensus_annotations.clear()
        self._is_aligned = False
        self._alignment_meta = None
        self.modelReset.emit()

    def reset_from_list(self, rows):
        self._rows = [SequenceRecord(header=h, sequence=s) for h, s in rows]
        self._global_annotations.clear()
        self._is_aligned = False
        self._alignment_meta = None
        self.modelReset.emit()

    def reset_from_records(self, records):
        self._rows = list(records)
        self.modelReset.emit()

    def add_annotation(self, row_index, annotation):
        self._rows[row_index].add_annotation(annotation)
        self.annotationAdded.emit(row_index, annotation)

    def remove_annotation(self, row_index, annotation_id):
        self._rows[row_index].remove_annotation(annotation_id)
        self.annotationRemoved.emit(row_index, annotation_id)

    def update_annotation(self, row_index, annotation):
        self._rows[row_index].update_annotation(annotation)
        self.annotationUpdated.emit(row_index, annotation)

    def get_annotations(self, row_index):
        return list(self._rows[row_index].annotations)

    def clear_annotations(self, row_index):
        self._rows[row_index].clear_annotations()
        self.annotationsReset.emit(row_index)

    def find_annotation(self, annotation_id):
        for i, record in enumerate(self._rows):
            for ann in record.annotations:
                if ann.id == annotation_id: return i, ann
        return None

    def all_annotations_flat(self):
        result = []
        for i, record in enumerate(self._rows):
            for ann in record.annotations:
                result.append((i, ann))
        return result

    @property
    def global_annotations(self): return self._global_annotations

    def add_global_annotation(self, annotation):
        if any(a.id == annotation.id for a in self._global_annotations):
            raise ValueError(f"Global annotation id '{annotation.id}' already exists.")
        self._global_annotations.append(annotation)
        self.globalAnnotationAdded.emit(annotation)

    def remove_global_annotation(self, annotation_id):
        remove_ids = {annotation_id}
        target = next((ann for ann in self._global_annotations if ann.id == annotation_id), None)
        if target is not None and target.parent_id is None:
            remove_ids.update(ann.id for ann in self._global_annotations if ann.parent_id == annotation_id)
        kept = [ann for ann in self._global_annotations if ann.id not in remove_ids]
        if len(kept) != len(self._global_annotations):
            self._global_annotations[:] = kept
            self.globalAnnotationRemoved.emit(annotation_id)
            return
        raise KeyError(f"Global annotation '{annotation_id}' not found.")

    def update_global_annotation(self, annotation):
        for i, ann in enumerate(self._global_annotations):
            if ann.id == annotation.id:
                self._global_annotations[i] = annotation
                self.globalAnnotationUpdated.emit(annotation)
                return
        raise KeyError(f"Global annotation '{annotation.id}' not found.")

    # ---- Consensus Annotation API ----
    @property
    def consensus_annotations(self): return list(self._consensus_annotations)

    def add_consensus_annotation(self, annotation):
        if any(a.id == annotation.id for a in self._consensus_annotations):
            raise ValueError(f"Consensus annotation id '{annotation.id}' already exists.")
        self._consensus_annotations.append(annotation)
        self.consensusAnnotationAdded.emit(annotation)

    def remove_consensus_annotation(self, annotation_id):
        remove_ids = {annotation_id}
        target = next((ann for ann in self._consensus_annotations if ann.id == annotation_id), None)
        if target is not None and target.parent_id is None:
            remove_ids.update(ann.id for ann in self._consensus_annotations if ann.parent_id == annotation_id)
        kept = [ann for ann in self._consensus_annotations if ann.id not in remove_ids]
        if len(kept) != len(self._consensus_annotations):
            self._consensus_annotations[:] = kept
            self.consensusAnnotationRemoved.emit(annotation_id)
            return
        raise KeyError(f"Consensus annotation '{annotation_id}' not found.")

    def update_consensus_annotation(self, annotation):
        for i, ann in enumerate(self._consensus_annotations):
            if ann.id == annotation.id:
                self._consensus_annotations[i] = annotation
                self.consensusAnnotationUpdated.emit(annotation)
                return
        raise KeyError(f"Consensus annotation '{annotation.id}' not found.")

    def clear_consensus_annotations(self):
        self._consensus_annotations.clear()

    def create_snapshot(self):
        return AlignmentDataModelSnapshot(
            rows=deepcopy(self._rows),
            is_aligned=self._is_aligned,
            alignment_meta=deepcopy(self._alignment_meta),
            global_annotations=deepcopy(self._global_annotations),
            consensus_annotations=deepcopy(self._consensus_annotations),
        )

    def restore_snapshot(self, snapshot: AlignmentDataModelSnapshot):
        alignment_changed = self._is_aligned != snapshot.is_aligned
        self._rows = deepcopy(snapshot.rows)
        self._is_aligned = snapshot.is_aligned
        self._alignment_meta = deepcopy(snapshot.alignment_meta)
        self._global_annotations = deepcopy(snapshot.global_annotations)
        self._consensus_annotations = deepcopy(snapshot.consensus_annotations)
        self.modelReset.emit()
        if alignment_changed:
            self.alignmentStateChanged.emit(self._is_aligned)


