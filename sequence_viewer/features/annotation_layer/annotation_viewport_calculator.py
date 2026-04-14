from __future__ import annotations

from typing import Optional

from PyQt5.QtCore import QRectF

from sequence_viewer.features.annotation_layer.annotation_layout_engine import AnnotationSideGeometry
from sequence_viewer.model.annotation import Annotation, AnnotationType


class AnnotationViewportCalculator:
    def __init__(self, side_geometry: AnnotationSideGeometry, lane_assignment: dict[str, int]) -> None:
        self._side_geometry = side_geometry
        self._lane_assignment = lane_assignment

    def calc_rect(
        self,
        annotation: Annotation,
        lane: int,
        *,
        char_width: float,
        view_left: float,
        widget_width: float,
        lane_height: int,
        lane_padding: int,
    ) -> Optional[QRectF]:
        x = annotation.start * char_width - view_left
        width = annotation.length() * char_width
        y = self._annotation_y(annotation, lane, lane_height, lane_padding)
        rect = QRectF(x, y, width, lane_height)
        return self._clip_rect(rect, widget_width)

    def _annotation_y(
        self,
        annotation: Annotation,
        lane: int,
        lane_height: int,
        lane_padding: int,
    ) -> float:
        if annotation.type == AnnotationType.MISMATCH_MARKER:
            parent_lane = self._lane_assignment.get(annotation.parent_id, 0)
            visual_lane = self._side_geometry.expanded_parent_lane(parent_lane) + 1
        else:
            visual_lane = self._side_geometry.expanded_parent_lane(lane)
        return lane_padding + visual_lane * (lane_height + lane_padding)

    @staticmethod
    def _clip_rect(rect: QRectF, widget_width: float) -> Optional[QRectF]:
        if rect.x() + rect.width() < 0 or rect.x() > widget_width:
            return None

        x = rect.x()
        width = rect.width()
        if x < 0:
            width += x
            x = 0.0
        if x + width > widget_width:
            width = widget_width - x
        if width <= 0:
            return None
        return QRectF(x, rect.y(), width, rect.height())
