# sequence_viewer/model/sequence_record.py
# model/sequence_record.py
from __future__ import annotations
import uuid
from dataclasses import dataclass, field
from typing import List, Optional
from sequence_viewer.model.annotation import Annotation

@dataclass
class SequenceRecord:
    header:      str
    sequence:    str
    id:          str                = field(default_factory=lambda: str(uuid.uuid4()))
    annotations: List[Annotation]  = field(default_factory=list)

    def add_annotation(self, annotation):
        if any(a.id == annotation.id for a in self.annotations):
            raise ValueError(f"Annotation id '{annotation.id}' already exists in record '{self.header}'.")
        self.annotations.append(annotation)

    def remove_annotation(self, annotation_id):
        remove_ids = {annotation_id}
        target = self.get_annotation(annotation_id)
        if target is not None and target.parent_id is None:
            remove_ids.update(a.id for a in self.annotations if a.parent_id == annotation_id)
        kept = [ann for ann in self.annotations if ann.id not in remove_ids]
        if len(kept) != len(self.annotations):
            self.annotations[:] = kept
            return
        raise KeyError(f"Annotation '{annotation_id}' not found in record '{self.header}'.")

    def update_annotation(self, annotation):
        for i, ann in enumerate(self.annotations):
            if ann.id == annotation.id:
                self.annotations[i] = annotation
                return
        raise KeyError(f"Annotation '{annotation.id}' not found in record '{self.header}'.")

    def get_annotation(self, annotation_id):
        for ann in self.annotations:
            if ann.id == annotation_id:
                return ann
        return None

    def clear_annotations(self):
        self.annotations.clear()


