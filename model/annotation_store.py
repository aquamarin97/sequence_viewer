# model/annotation_store.py
"""
Annotasyon deposu — tek gerçek kaynak.

Sinyaller
---------
annotationAdded(annotation)       Yeni annotasyon eklendi.
annotationRemoved(annotation_id)  Annotasyon silindi.
annotationUpdated(annotation)     Mevcut annotasyon güncellendi.
storeReset()                      Tüm annotasyonlar temizlendi.
"""

from __future__ import annotations

from typing import Dict, Iterable, List, Optional

from PyQt5.QtCore import QObject, pyqtSignal

from model.annotation import Annotation


class AnnotationStore(QObject):

    annotationAdded   = pyqtSignal(object)   # Annotation
    annotationRemoved = pyqtSignal(str)      # annotation id
    annotationUpdated = pyqtSignal(object)   # Annotation
    storeReset        = pyqtSignal()

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._annotations: Dict[str, Annotation] = {}   # id → Annotation

    # ------------------------------------------------------------------
    # Yazma API'si
    # ------------------------------------------------------------------

    def add(self, annotation: Annotation) -> str:
        """
        Annotasyon ekler. id çakışıyorsa ValueError fırlatır.
        Eklenen annotasyonun id'sini döner.
        """
        if annotation.id in self._annotations:
            raise ValueError(f"Annotation id '{annotation.id}' already exists.")
        self._annotations[annotation.id] = annotation
        self.annotationAdded.emit(annotation)
        return annotation.id

    def remove(self, annotation_id: str) -> None:
        """Belirtilen annotasyonu siler. Bulunamazsa KeyError."""
        if annotation_id not in self._annotations:
            raise KeyError(f"Annotation '{annotation_id}' not found.")
        del self._annotations[annotation_id]
        self.annotationRemoved.emit(annotation_id)

    def update(self, annotation: Annotation) -> None:
        """
        Mevcut annotasyonu günceller (aynı id ile).
        id yoksa KeyError.
        """
        if annotation.id not in self._annotations:
            raise KeyError(f"Annotation '{annotation.id}' not found.")
        self._annotations[annotation.id] = annotation
        self.annotationUpdated.emit(annotation)

    def clear(self) -> None:
        """Tüm annotasyonları siler."""
        self._annotations.clear()
        self.storeReset.emit()

    # ------------------------------------------------------------------
    # Okuma API'si
    # ------------------------------------------------------------------

    def get(self, annotation_id: str) -> Optional[Annotation]:
        return self._annotations.get(annotation_id)

    def all(self) -> List[Annotation]:
        """Tüm annotasyonların listesini döner (ekleme sırasına göre)."""
        return list(self._annotations.values())

    def in_range(self, start: int, end: int) -> List[Annotation]:
        """Verilen aralıkla örtüşen annotasyonları döner."""
        return [
            a for a in self._annotations.values()
            if a.start <= end and a.end >= start
        ]

    def count(self) -> int:
        return len(self._annotations)