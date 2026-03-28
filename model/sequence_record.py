# model/sequence_record.py
"""
Tek bir dizinin domain modeli.

Sorumluluklar
-------------
* header ve sequence string'lerini taşımak
* O diziye ait annotation listesini sahiplenmek
* Persistence katmanından bağımsız olmak — serileştirme buraya girmez

id
--
UUID tabanlı. FASTA başlığı benzersiz olmayabilir, slug kırılgan olur.
Persistence katmanı bu id'yi dış referans anahtarı olarak kullanır.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import List, Optional

from model.annotation import Annotation


@dataclass
class SequenceRecord:
    """
    Bir dizinin bellekteki tam temsili.

    Parametreler
    ------------
    header     : FASTA başlığı veya kullanıcının düzenlediği isim.
    sequence   : Ham dizi string'i (gaplar dahil, büyük harf önerilir).
    id         : Otomatik üretilen UUID. Dışarıdan verilmesi gerekmez.
    annotations: Bu diziye ait annotation listesi. Sahip bu objedir.
    """

    header:      str
    sequence:    str
    id:          str                = field(default_factory=lambda: str(uuid.uuid4()))
    annotations: List[Annotation]  = field(default_factory=list)

    # ------------------------------------------------------------------
    # Annotation yönetimi
    # ------------------------------------------------------------------

    def add_annotation(self, annotation: Annotation) -> None:
        """Annotation ekler. id çakışıyorsa ValueError fırlatır."""
        if any(a.id == annotation.id for a in self.annotations):
            raise ValueError(
                f"Annotation id '{annotation.id}' already exists "
                f"in record '{self.header}'."
            )
        self.annotations.append(annotation)

    def remove_annotation(self, annotation_id: str) -> None:
        """id'ye göre annotation siler. Bulunamazsa KeyError."""
        for i, ann in enumerate(self.annotations):
            if ann.id == annotation_id:
                del self.annotations[i]
                return
        raise KeyError(
            f"Annotation '{annotation_id}' not found "
            f"in record '{self.header}'."
        )

    def update_annotation(self, annotation: Annotation) -> None:
        """Aynı id'li annotation'ı günceller. Bulunamazsa KeyError."""
        for i, ann in enumerate(self.annotations):
            if ann.id == annotation.id:
                self.annotations[i] = annotation
                return
        raise KeyError(
            f"Annotation '{annotation.id}' not found "
            f"in record '{self.header}'."
        )

    def get_annotation(self, annotation_id: str) -> Optional[Annotation]:
        """id'ye göre annotation döner. Bulunamazsa None."""
        for ann in self.annotations:
            if ann.id == annotation_id:
                return ann
        return None

    def clear_annotations(self) -> None:
        """Tüm annotation'ları siler."""
        self.annotations.clear()