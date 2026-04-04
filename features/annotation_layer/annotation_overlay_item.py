# features/annotation_layer/annotation_overlay_item.py
from __future__ import annotations
from typing import Dict, List, Optional, Tuple
from PyQt5.QtCore import Qt, QRectF
from PyQt5.QtGui import QPainter, QBrush, QColor, QPen
from PyQt5.QtWidgets import QGraphicsItem, QStyleOptionGraphicsItem
from model.annotation import Annotation
from model.annotation_store import AnnotationStore

_OVERLAY_ALPHA = 35; _OVERLAY_Z = 5.0

class AnnotationOverlayItem(QGraphicsItem):
    def __init__(self, store, parent=None):
        super().__init__(parent)
        self._store = store; self._annotations = []
        self._scene_width = 0.0; self._scene_height = 0.0; self._char_width = 12.0; self._char_height = 18
        self.setZValue(_OVERLAY_Z); self.setFlag(QGraphicsItem.ItemUsesExtendedStyleOption, True)
        self._store.annotationAdded.connect(self._on_store_changed)
        self._store.annotationRemoved.connect(self._on_store_changed)
        self._store.annotationUpdated.connect(self._on_store_changed)
        self._store.storeReset.connect(self._on_store_changed)

    def update_geometry(self, scene_width, scene_height, char_width, char_height):
        self.prepareGeometryChange()
        self._scene_width = scene_width; self._scene_height = scene_height
        self._char_width = char_width; self._char_height = char_height; self.update()

    def _on_store_changed(self, *_): self._annotations = self._store.all(); self.update()
    def boundingRect(self): return QRectF(0, 0, self._scene_width, self._scene_height)

    def paint(self, painter, option, widget=None):
        if not self._annotations or self._char_width <= 0: return
        exposed = option.exposedRect; cw = self._char_width
        vis_left = max(0.0, exposed.left()); vis_right = exposed.right()
        painter.setPen(Qt.NoPen)
        for ann in self._annotations:
            x = ann.start * cw; w = ann.length() * cw
            if x + w < vis_left or x > vis_right: continue
            color = QColor(ann.resolved_color()); color.setAlpha(_OVERLAY_ALPHA)
            painter.setBrush(QBrush(color))
            painter.drawRect(QRectF(x, 0, w, self._scene_height))
