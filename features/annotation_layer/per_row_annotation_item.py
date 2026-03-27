# features/annotation_layer/per_row_annotation_item.py

from __future__ import annotations

import math
from typing import Callable, Dict, List, Optional, Tuple

from PyQt5.QtCore import Qt, QRectF, QPointF
from PyQt5.QtGui import QPainter, QPen, QBrush, QColor
from PyQt5.QtWidgets import QGraphicsItem, QStyleOptionGraphicsItem

from features.annotation_layer.annotation_layout_engine import (
    assign_lanes, lane_count,
)
from features.annotation_layer.annotation_painter import (
    draw_forward_primer, draw_reverse_primer, draw_probe, draw_region,
)
from model.annotation import Annotation, AnnotationType
from model.annotation_store import AnnotationStore
from settings.theme import theme_manager

LANE_HEIGHT  = 16
LANE_PADDING = 2


class PerRowAnnotationItem(QGraphicsItem):
    """
    Her sequence satırının üstünde greedy-lane annotasyon şeritleri çizer.

    Tıklama callback'i
    ------------------
    on_annotation_clicked: Callable[[Annotation, int], None] | None
        (annotation, row_index) → workspace'in selection + guide logic'i
    """

    def __init__(self, store: AnnotationStore) -> None:
        super().__init__()

        self._store = store

        self._row_count:   int   = 0
        self._char_width:  float = 12.0
        self._char_height: int   = 18
        self._row_stride:  int   = 18
        self._per_row_h:   int   = 0
        self._scene_w:     float = 0.0
        self._scene_h:     float = 0.0

        self._annotations:     List[Annotation]  = []
        self._lane_assignment: Dict[str, int]    = {}
        self._lane_cnt:        int               = 0

        # Tıklama callback — workspace tarafından atanır
        self.on_annotation_clicked: Optional[Callable[[Annotation, int], None]] = None

        self.setFlag(QGraphicsItem.ItemUsesExtendedStyleOption, True)
        # Mouse event'leri almak için gerekli
        self.setAcceptedMouseButtons(Qt.LeftButton)
        self.setZValue(10.0)

        self._store.annotationAdded.connect(self._on_store_changed)
        self._store.annotationRemoved.connect(self._on_store_changed)
        self._store.annotationUpdated.connect(self._on_store_changed)
        self._store.storeReset.connect(self._on_store_changed)

        theme_manager.themeChanged.connect(self.update)

    # ------------------------------------------------------------------
    # Geometri
    # ------------------------------------------------------------------

    def update_geometry(
        self,
        row_count:   int,
        char_width:  float,
        char_height: int,
        row_stride:  int,
        per_row_h:   int,
        scene_w:     float,
        scene_h:     float,
    ) -> None:
        self.prepareGeometryChange()
        self._row_count   = row_count
        self._char_width  = char_width
        self._char_height = char_height
        self._row_stride  = row_stride
        self._per_row_h   = per_row_h
        self._scene_w     = scene_w
        self._scene_h     = scene_h
        self.update()

    # ------------------------------------------------------------------
    # Store
    # ------------------------------------------------------------------

    def _on_store_changed(self, *_args) -> None:
        self._annotations     = self._store.all()
        self._lane_assignment = assign_lanes(self._annotations)
        self._lane_cnt        = lane_count(self._lane_assignment)
        self.update()

    # ------------------------------------------------------------------
    # Hit test — hangi annotasyon ve hangi satır
    # ------------------------------------------------------------------

    def annotation_at(
        self, scene_pos: QPointF
    ) -> Optional[Tuple[Annotation, int]]:
        """
        (annotation, row_index) döner veya None.
        """
        if not self._annotations or self._per_row_h == 0 or self._row_stride <= 0:
            return None

        cw  = self._char_width
        sy  = scene_pos.y()
        sx  = scene_pos.x()

        row = int(sy // self._row_stride)
        if row < 0 or row >= self._row_count:
            return None

        strip_top = row * self._row_stride
        strip_bot = strip_top + self._per_row_h
        if sy < strip_top or sy >= strip_bot:
            return None

        rel_y = sy - strip_top
        lane  = int(rel_y // (LANE_HEIGHT + LANE_PADDING))

        for ann in self._annotations:
            if self._lane_assignment.get(ann.id, -1) != lane:
                continue
            ann_x = ann.start * cw
            ann_w = ann.length() * cw
            if ann_x <= sx <= ann_x + ann_w:
                return ann, row

        return None

    # ------------------------------------------------------------------
    # Mouse events
    # ------------------------------------------------------------------

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            result = self.annotation_at(event.scenePos())
            if result is not None and self.on_annotation_clicked is not None:
                ann, row = result
                self.on_annotation_clicked(ann, row)
            event.accept()
        else:
            super().mousePressEvent(event)

    # ------------------------------------------------------------------
    # QGraphicsItem
    # ------------------------------------------------------------------

    def boundingRect(self) -> QRectF:
        return QRectF(0, 0, self._scene_w, self._scene_h)

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionGraphicsItem,
        widget=None,
    ) -> None:
        if self._per_row_h == 0 or not self._annotations:
            return

        exposed   = option.exposedRect
        cw        = self._char_width
        t         = theme_manager.current
        vis_left  = exposed.left()
        vis_right = exposed.right()

        painter.setRenderHint(QPainter.Antialiasing, True)

        for row in range(self._row_count):
            strip_top = row * self._row_stride
            strip_bot = strip_top + self._per_row_h

            if strip_bot < exposed.top() or strip_top > exposed.bottom():
                continue

            # Şerit arkaplanı
            bg = QColor(t.row_bg_odd)
            painter.fillRect(
                QRectF(vis_left, strip_top, vis_right - vis_left, self._per_row_h),
                bg,
            )

            # Alt çizgi
            painter.setPen(QPen(QColor(t.border_normal), 0))
            painter.drawLine(
                QPointF(vis_left,  strip_bot - 1),
                QPointF(vis_right, strip_bot - 1),
            )

            for ann in self._annotations:
                lane  = self._lane_assignment.get(ann.id, 0)
                lane_y = (strip_top
                          + lane * (LANE_HEIGHT + LANE_PADDING)
                          + LANE_PADDING)
                ann_x  = ann.start * cw
                ann_w  = ann.length() * cw
                ann_h  = float(LANE_HEIGHT)

                if ann_x + ann_w < vis_left or ann_x > vis_right:
                    continue

                painter.save()

                if ann.type == AnnotationType.FORWARD_PRIMER:
                    draw_forward_primer(
                        painter, ann_x, lane_y, ann_w, ann_h,
                        ann.resolved_color(), ann.label,
                    )
                elif ann.type == AnnotationType.REVERSE_PRIMER:
                    draw_reverse_primer(
                        painter, ann_x, lane_y, ann_w, ann_h,
                        ann.resolved_color(), ann.label,
                    )
                elif ann.type == AnnotationType.PROBE:
                    # strand bilgisini geç
                    draw_probe(
                        painter, ann_x, lane_y, ann_w, ann_h,
                        ann.resolved_color(), ann.label,
                        strand=ann.strand,
                    )
                else:  # REGION
                    draw_region(
                        painter, ann_x, lane_y, ann_w, ann_h,
                        ann.resolved_color(), ann.label,
                    )

                painter.restore()