# sequence_viewer/model/alignment_data_model.py
from __future__ import annotations
from copy import deepcopy


def _to_str(seq) -> str:
    return seq.to_str() if hasattr(seq, 'to_str') else seq


from dataclasses import dataclass
from typing import List, Optional
from PyQt5.QtCore import QObject, pyqtSignal
from sequence_viewer.model.alignment_metadata import AlignmentMetadata
from sequence_viewer.model.annotation import Annotation
from sequence_viewer.model.sequence_record import SequenceRecord


class _LazyRowStore:
    """
    A list-like container for SequenceRecord objects backed by one or more
    lazy segments (SQXReader) and/or eager segments (plain lists).

    Records from a reader segment are created on first access and cached.
    Any structural mutation (delete, move, insert) materialises everything
    into a flat list first — cheap amortised cost since mutations happen
    only on user interaction, not on load.
    """

    def __init__(self):
        self._segments: list = []   # each element: dict (reader seg) or list (eager seg)
        self._mutated = False
        self._overlay: list = []    # active flat list once _mutated is True

    # ── segment helpers ────────────────────────────────────────────────────

    def _seg_len(self, seg) -> int:
        if not isinstance(seg, dict):
            return len(seg)
        indices = seg.get('indices')
        return len(indices) if indices is not None else seg['count']

    def _source_index(self, seg, local_i: int) -> int:
        indices = seg.get('indices')
        return local_i if indices is None else indices[local_i]

    def _seg_get(self, seg, local_i):
        if isinstance(seg, dict):
            cache = seg['cache']
            source_i = self._source_index(seg, local_i)
            if source_i not in cache:
                cache[source_i] = seg['reader'].read_sequence_record(source_i)
            return cache[source_i]
        return seg[local_i]

    def _locate(self, index: int):
        n = len(self)
        if index < 0:
            index += n
        if not (0 <= index < n):
            raise IndexError(index)
        offset = 0
        for seg in self._segments:
            seg_len = self._seg_len(seg)
            if index < offset + seg_len:
                return seg, index - offset
            offset += seg_len
        raise IndexError(index)

    def _cached_record(self, seg, local_i):
        if isinstance(seg, dict):
            return seg['cache'].get(self._source_index(seg, local_i))
        return seg[local_i]

    def _seg_max_len(self, seg) -> int:
        if isinstance(seg, dict):
            indices = seg.get('indices')
            if indices is not None:
                return max((seg['reader'].sequence_length(i) for i in indices), default=0)
            return seg['reader'].max_sequence_length()
        return max((len(r.sequence) for r in seg), default=0)

    def _remove_empty_segments(self) -> None:
        self._segments = [seg for seg in self._segments if self._seg_len(seg) > 0]

    def _seg_delete(self, seg, local_i: int) -> None:
        if isinstance(seg, dict):
            if seg.get('indices') is None:
                seg['indices'] = list(range(seg['count']))
            seg['indices'].pop(local_i)
            seg['count'] = len(seg['indices'])
            return
        del seg[local_i]

    def _slice_reader_segment(self, seg, start: int, end: int):
        indices = [self._source_index(seg, i) for i in range(start, end)]
        return {
            'reader': seg['reader'],
            'count': len(indices),
            'cache': seg['cache'],
            'indices': indices,
        }

    def _locate_for_insert(self, index: int):
        if index < 0:
            index = 0
        n = len(self)
        if index > n:
            index = n
        offset = 0
        for seg_i, seg in enumerate(self._segments):
            seg_len = self._seg_len(seg)
            if index <= offset + seg_len:
                return seg_i, seg, index - offset
            offset += seg_len
        return len(self._segments), None, 0

    # ── public list-like API ───────────────────────────────────────────────

    def attach_reader(self, reader) -> None:
        if self._mutated:
            for i in range(reader.sequence_count()):
                self._overlay.append(reader.read_sequence_record(i))
        else:
            self._segments.append({'reader': reader, 'count': reader.sequence_count(), 'cache': {}})

    def __len__(self) -> int:
        if self._mutated:
            return len(self._overlay)
        return sum(self._seg_len(s) for s in self._segments)

    def __bool__(self) -> bool:
        return len(self) > 0

    def __getitem__(self, index: int):
        if self._mutated:
            return self._overlay[index]
        seg, local_i = self._locate(index)
        return self._seg_get(seg, local_i)

    def __iter__(self):
        if self._mutated:
            yield from self._overlay
            return
        for seg in self._segments:
            if isinstance(seg, dict):
                for i in range(self._seg_len(seg)):
                    yield self._seg_get(seg, i)
            else:
                yield from seg

    def max_sequence_length(self) -> int:
        if self._mutated:
            return max((len(r.sequence) for r in self._overlay), default=0)
        return max((self._seg_max_len(s) for s in self._segments), default=0)

    def get_header(self, index: int) -> str:
        if self._mutated:
            return self._overlay[index].header
        seg, local_i = self._locate(index)
        cached = self._cached_record(seg, local_i)
        if cached is not None:
            return cached.header
        return seg['reader'].sequence_header(self._source_index(seg, local_i))

    def get_sequence(self, index: int):
        if self._mutated:
            return self._overlay[index].sequence
        seg, local_i = self._locate(index)
        cached = self._cached_record(seg, local_i)
        if cached is not None:
            return cached.sequence
        return seg['reader'].read_sequence(self._source_index(seg, local_i))

    def get_annotations(self, index: int) -> list:
        if self._mutated:
            return list(self._overlay[index].annotations)
        seg, local_i = self._locate(index)
        cached = self._cached_record(seg, local_i)
        if cached is not None:
            return list(cached.annotations)
        return seg['reader'].sequence_annotations(self._source_index(seg, local_i))

    def iter_headers(self):
        if self._mutated:
            for record in self._overlay:
                yield record.header
            return
        for seg in self._segments:
            if isinstance(seg, dict):
                cache = seg['cache']
                reader = seg['reader']
                for i in range(self._seg_len(seg)):
                    source_i = self._source_index(seg, i)
                    cached = cache.get(source_i)
                    yield cached.header if cached is not None else reader.sequence_header(source_i)
            else:
                for record in seg:
                    yield record.header

    def iter_annotation_lists(self):
        if self._mutated:
            for record in self._overlay:
                yield list(record.annotations)
            return
        for seg in self._segments:
            if isinstance(seg, dict):
                cache = seg['cache']
                reader = seg['reader']
                for i in range(self._seg_len(seg)):
                    source_i = self._source_index(seg, i)
                    cached = cache.get(source_i)
                    yield list(cached.annotations) if cached is not None else reader.sequence_annotations(source_i)
            else:
                for record in seg:
                    yield list(record.annotations)

    def iter_annotations_flat(self):
        row_index = 0
        for annotations in self.iter_annotation_lists():
            for ann in annotations:
                yield row_index, ann
            row_index += 1

    def extend(self, records) -> None:
        lst = list(records)
        if self._mutated:
            self._overlay.extend(lst)
            return
        if self._segments and isinstance(self._segments[-1], list):
            self._segments[-1].extend(lst)
        else:
            self._segments.append(lst)

    def append(self, record) -> None:
        if self._mutated:
            self._overlay.append(record)
            return
        if self._segments and isinstance(self._segments[-1], list):
            self._segments[-1].append(record)
        else:
            self._segments.append([record])

    def delete_indices(self, indices) -> list[tuple[int, SequenceRecord]]:
        n = len(self)
        rows = sorted({i for i in indices if 0 <= i < n})
        if not rows:
            return []
        deleted: list[tuple[int, SequenceRecord]] = []
        if self._mutated:
            for index in reversed(rows):
                deleted.append((index, self._overlay.pop(index)))
            deleted.reverse()
            return deleted
        for index in reversed(rows):
            seg, local_i = self._locate(index)
            deleted.append((index, self._seg_get(seg, local_i)))
            self._seg_delete(seg, local_i)
        self._remove_empty_segments()
        deleted.reverse()
        return deleted

    def insert_records_at(self, indexed_records) -> None:
        pairs = sorted(indexed_records, key=lambda pair: pair[0])
        if not pairs:
            return
        if self._mutated:
            for index, record in pairs:
                self._overlay.insert(index, record)
            return
        for index, record in pairs:
            self._insert_record(index, record)

    def _insert_record(self, index: int, record: SequenceRecord) -> None:
        seg_i, seg, local_i = self._locate_for_insert(index)
        if seg is None:
            self._segments.append([record])
            return
        if isinstance(seg, list):
            seg.insert(local_i, record)
            return

        new_segments = []
        if local_i > 0:
            new_segments.append(self._slice_reader_segment(seg, 0, local_i))
        new_segments.append([record])
        seg_len = self._seg_len(seg)
        if local_i < seg_len:
            new_segments.append(self._slice_reader_segment(seg, local_i, seg_len))
        self._segments[seg_i:seg_i + 1] = new_segments

    def clear(self) -> None:
        self._segments = []
        self._mutated = False
        self._overlay = []

    def _materialize_all(self) -> None:
        if self._mutated:
            return
        result = []
        for seg in self._segments:
            if isinstance(seg, dict):
                for i in range(self._seg_len(seg)):
                    result.append(self._seg_get(seg, i))
            else:
                result.extend(seg)
        self._overlay = result
        self._segments = []
        self._mutated = True

    def pop(self, index: int):
        self._materialize_all()
        return self._overlay.pop(index)

    def __delitem__(self, index: int) -> None:
        self._materialize_all()
        del self._overlay[index]

    def insert(self, index: int, value) -> None:
        self._materialize_all()
        self._overlay.insert(index, value)

    def __deepcopy__(self, memo):
        return deepcopy(list(self), memo)


@dataclass
class AlignmentDataModelSnapshot:
    rows: List[SequenceRecord]
    is_aligned: bool
    alignment_meta: Optional[AlignmentMetadata]
    global_annotations: List[Annotation]
    consensus_annotations: List[Annotation]

class AlignmentDataModel(QObject):
    rowAppended    = pyqtSignal(int, str)
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
        self._rows = _LazyRowStore()
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
        r = self._rows[index]
        return r.header, _to_str(r.sequence)
    def get_header(self, index): return self._rows.get_header(index)
    def get_sequence_object(self, index): return self._rows.get_sequence(index)
    def get_sequence(self, index): return _to_str(self._rows.get_sequence(index))
    def all_rows(self): return [(r.header, _to_str(r.sequence)) for r in self._rows]
    @property
    def max_sequence_length(self):
        if not self._rows:
            return 0
        return self._rows.max_sequence_length()
    def get_record(self, index): return self._rows[index]
    def all_records(self): return list(self._rows)
    def iter_headers(self): return self._rows.iter_headers()
    def iter_annotation_lists(self): return self._rows.iter_annotation_lists()

    def append_row(self, header, sequence):
        record = SequenceRecord(header=header, sequence=sequence)
        index = len(self._rows)
        self._rows.append(record)
        self.rowAppended.emit(index, header)
        return index

    def attach_reader(self, reader) -> None:
        self._rows.attach_reader(reader)
        self.modelReset.emit()

    def append_records_bulk(self, records: list) -> None:
        self._rows.extend(records)
        self.modelReset.emit()

    def remove_row(self, index):
        if index < 0 or index >= len(self._rows):
            raise IndexError(f"Row index {index} out of range")
        del self._rows[index]
        self.rowRemoved.emit(index)

    def remove_rows(self, indices) -> list[tuple[int, SequenceRecord]]:
        deleted = self._rows.delete_indices(indices)
        if deleted:
            self.modelReset.emit()
        return deleted

    def insert_records_at(self, indexed_records) -> None:
        pairs = list(indexed_records)
        if not pairs:
            return
        self._rows.insert_records_at(pairs)
        self.modelReset.emit()

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
        store = _LazyRowStore()
        store.extend([SequenceRecord(header=h, sequence=s) for h, s in rows])
        self._rows = store
        self._global_annotations.clear()
        self._consensus_annotations.clear()
        self._is_aligned = False
        self._alignment_meta = None
        self.modelReset.emit()

    def reset_from_records(self, records):
        store = _LazyRowStore()
        store.extend(list(records))
        self._rows = store
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
        return self._rows.get_annotations(row_index)

    def clear_annotations(self, row_index):
        self._rows[row_index].clear_annotations()
        self.annotationsReset.emit(row_index)

    def find_annotation(self, annotation_id):
        for i, record in enumerate(self._rows):
            for ann in record.annotations:
                if ann.id == annotation_id: return i, ann
        return None

    def all_annotations_flat(self):
        return list(self._rows.iter_annotations_flat())

    def _add_collection_annotation(self, collection, annotation, scope_name, signal):
        if any(item.id == annotation.id for item in collection):
            raise ValueError(f"{scope_name} annotation id '{annotation.id}' already exists.")
        collection.append(annotation)
        signal.emit(annotation)

    def _remove_collection_annotation(self, collection, annotation_id, scope_name, signal):
        remove_ids = {annotation_id}
        target = next((item for item in collection if item.id == annotation_id), None)
        if target is not None and target.parent_id is None:
            remove_ids.update(item.id for item in collection if item.parent_id == annotation_id)

        kept = [item for item in collection if item.id not in remove_ids]
        if len(kept) == len(collection):
            raise KeyError(f"{scope_name} annotation '{annotation_id}' not found.")

        collection[:] = kept
        signal.emit(annotation_id)

    def _update_collection_annotation(self, collection, annotation, scope_name, signal):
        for index, item in enumerate(collection):
            if item.id == annotation.id:
                collection[index] = annotation
                signal.emit(annotation)
                return
        raise KeyError(f"{scope_name} annotation '{annotation.id}' not found.")

    @property
    def global_annotations(self): return self._global_annotations

    def add_global_annotation(self, annotation):
        self._add_collection_annotation(
            self._global_annotations,
            annotation,
            "Global",
            self.globalAnnotationAdded,
        )

    def remove_global_annotation(self, annotation_id):
        self._remove_collection_annotation(
            self._global_annotations,
            annotation_id,
            "Global",
            self.globalAnnotationRemoved,
        )

    def update_global_annotation(self, annotation):
        self._update_collection_annotation(
            self._global_annotations,
            annotation,
            "Global",
            self.globalAnnotationUpdated,
        )

    # ---- Consensus Annotation API ----
    @property
    def consensus_annotations(self): return list(self._consensus_annotations)

    def add_consensus_annotation(self, annotation):
        self._add_collection_annotation(
            self._consensus_annotations,
            annotation,
            "Consensus",
            self.consensusAnnotationAdded,
        )

    def remove_consensus_annotation(self, annotation_id):
        self._remove_collection_annotation(
            self._consensus_annotations,
            annotation_id,
            "Consensus",
            self.consensusAnnotationRemoved,
        )

    def update_consensus_annotation(self, annotation):
        self._update_collection_annotation(
            self._consensus_annotations,
            annotation,
            "Consensus",
            self.consensusAnnotationUpdated,
        )

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
        store = _LazyRowStore()
        store.extend(deepcopy(snapshot.rows))
        self._rows = store
        self._is_aligned = snapshot.is_aligned
        self._alignment_meta = deepcopy(snapshot.alignment_meta)
        self._global_annotations = deepcopy(snapshot.global_annotations)
        self._consensus_annotations = deepcopy(snapshot.consensus_annotations)
        self.modelReset.emit()
        if alignment_changed:
            self.alignmentStateChanged.emit(self._is_aligned)
