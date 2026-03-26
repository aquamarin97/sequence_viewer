# features/annotation_layer/annotation_overlay_item.py
"""
Sequence viewer sahnesi üzerinde yarı saydam annotasyon overlay'i.

Her AnnotationType için ayrı bir renk bandı çizer.
Kullanıcı sekansın altında annotasyonun rengini görebilir.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from PyQt5.QtCore import Qt, QRectF
from PyQt5.QtGui import QPainter, QBrush, QColor, QPen
from PyQt5.QtWidgets import QGraphicsItem, QStyleOptionGraphicsItem

from model.annotation import Annotation
from model.annotation_store import AnnotationStore


# Overlay saydamlığı
_OVERLAY_ALPHA = 35     # 0-255 (çok düşük — sekans okunabilirliği korunur)
_OVERLAY_Z     = 5.0    # SequenceGraphicsItem'ın üstünde


class AnnotationOverlayItem(QGraphicsItem):
    """
    Sequence viewer sahnesine eklenen tek bir QGraphicsItem.
    Tüm annotasyonların saydam bantlarını tek seferde çizer.

    Sahnenin tam boyutunda bir bounding rect tutar.
    Sadece görünür (exposed) alan için çizim yapar.
    """

    def __init__(
        self,
        store: AnnotationStore,
        parent: Optional[QGraphicsItem] = None,
    ) -> None:
        super().__init__(parent)

        self._store       = store
        self._annotations: List[Annotation] = []

        # Geometri — sequence_viewer tarafından güncellenir
        self._scene_width:  float = 0.0
        self._scene_height: float = 0.0
        self._char_width:   float = 12.0
        self._char_height:  int   = 18

        self.setZValue(_OVERLAY_Z)
        self.setFlag(QGraphicsItem.ItemUsesExtendedStyleOption, True)

        # Store sinyalleri
        self._store.annotationAdded.connect(self._on_store_changed)
        self._store.annotationRemoved.connect(self._on_store_changed)
        self._store.annotationUpdated.connect(self._on_store_changed)
        self._store.storeReset.connect(self._on_store_changed)

    # ------------------------------------------------------------------
    # Güncelleme API'si (workspace / viewer tarafından çağrılır)
    # ------------------------------------------------------------------

    def update_geometry(
        self,
        scene_width: float,
        scene_height: float,
        char_width: float,
        char_height: int,
    ) -> None:
        """Sahne boyutu veya zoom değiştiğinde çağrılır."""
        self.prepareGeometryChange()
        self._scene_width  = scene_width
        self._scene_height = scene_height
        self._char_width   = char_width
        self._char_height  = char_height
        self.update()

    # ------------------------------------------------------------------
    # Slot
    # ------------------------------------------------------------------

    def _on_store_changed(self, *_args) -> None:
        self._annotations = self._store.all()
        self.update()

    # ------------------------------------------------------------------
    # QGraphicsItem
    # ------------------------------------------------------------------

    def boundingRect(self) -> QRectF:
        return QRectF(0, 0, self._scene_width, self._scene_height)

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionGraphicsItem,
        widget=None,
    ) -> None:
        if not self._annotations or self._char_width <= 0:
            return

        exposed = option.exposedRect
        cw      = self._char_width
        ch      = float(self._char_height)

        # Görünür kolon aralığı
        vis_left  = max(0.0, exposed.left())
        vis_right = exposed.right()

        painter.setPen(Qt.NoPen)

        for ann in self._annotations:
            x = ann.start * cw
            w = ann.length() * cw

            # Görünür alanla kesişiyor mu?
            if x + w < vis_left or x > vis_right:
                continue

            color = QColor(ann.resolved_color())
            color.setAlpha(_OVERLAY_ALPHA)
            painter.setBrush(QBrush(color))

            # Tüm satırları kapsa (y=0'dan sahne yüksekliğine)
            painter.drawRect(QRectF(x, 0, w, self._scene_height))