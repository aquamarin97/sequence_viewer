# sequence_viewer/model/annotation_store.py
# model/annotation_store.py
from __future__ import annotations
from typing import Dict, Iterable, List, Optional
from PyQt5.QtCore import QObject, pyqtSignal
from sequence_viewer.model.annotation import Annotation

class AnnotationStore(QObject):
    annotationAdded   = pyqtSignal(object)
    annotationRemoved = pyqtSignal(str)
    annotationUpdated = pyqtSignal(object)
    storeReset        = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._annotations: Dict[str, Annotation] = {}

    def add(self, annotation):
        if annotation.id in self._annotations:
            raise ValueError(f"Annotation id '{annotation.id}' already exists.")
        self._annotations[annotation.id] = annotation
        self.annotationAdded.emit(annotation)
        return annotation.id

    def remove(self, annotation_id):
        if annotation_id not in self._annotations:
            raise KeyError(f"Annotation '{annotation_id}' not found.")
        del self._annotations[annotation_id]
        self.annotationRemoved.emit(annotation_id)

    def update(self, annotation):
        if annotation.id not in self._annotations:
            raise KeyError(f"Annotation '{annotation.id}' not found.")
        self._annotations[annotation.id] = annotation
        self.annotationUpdated.emit(annotation)

    def clear(self):
        self._annotations.clear()
        self.storeReset.emit()

    def get(self, annotation_id):
        return self._annotations.get(annotation_id)

    def all(self):
        return list(self._annotations.values())

    def in_range(self, start, end):
        return [a for a in self._annotations.values() if a.start <= end and a.end >= start]

    def count(self):
        return len(self._annotations)


