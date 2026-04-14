from __future__ import annotations

from PyQt5.QtCore import QRectF, Qt
from PyQt5.QtGui import QColor

from sequence_viewer.features.annotation_layer.annotation_painter import (
    draw_mismatch_marker,
    draw_primer,
    draw_probe,
    draw_repeated_region,
    draw_selection_outline,
)
from sequence_viewer.model.annotation import AnnotationType


class AnnotationRenderer:
    def render_annotation(self, painter, annotation, rect: QRectF, *, selected: bool) -> None:
        painter.save()
        char_width = rect.width() / max(annotation.length(), 1)
        color = annotation.resolved_color()

        if annotation.type == AnnotationType.PRIMER:
            draw_primer(
                painter,
                rect.x(),
                rect.y(),
                rect.width(),
                rect.height(),
                color,
                annotation.label,
                strand=annotation.strand,
                char_width=char_width,
            )
        elif annotation.type == AnnotationType.PROBE:
            draw_probe(
                painter,
                rect.x(),
                rect.y(),
                rect.width(),
                rect.height(),
                color,
                annotation.label,
                strand=annotation.strand,
                char_width=char_width,
            )
        elif annotation.type == AnnotationType.MISMATCH_MARKER:
            from sequence_viewer.settings.display_settings_manager import (
                display_settings_manager,
            )

            draw_mismatch_marker(
                painter,
                rect.x(),
                rect.y(),
                rect.width(),
                rect.height(),
                color,
                annotation.expected_base or annotation.mismatch_base or annotation.label,
                char_width=rect.width(),
                font_family=display_settings_manager.sequence_font_family,
                font_size=display_settings_manager.sequence_font_size_base,
            )
        else:
            draw_repeated_region(
                painter,
                rect.x(),
                rect.y(),
                rect.width(),
                rect.height(),
                color,
                annotation.label,
            )

        if selected:
            draw_selection_outline(
                painter,
                rect.x(),
                rect.y(),
                rect.width(),
                rect.height(),
                annotation.type,
                color,
                strand=getattr(annotation, "strand", "+"),
                char_width=char_width,
            )
        painter.restore()

    def render_dim_effect(
        self,
        painter,
        dim_range,
        *,
        char_width: float,
        offset: float,
        widget_width: float,
        widget_height: float,
        dim_color: QColor,
    ) -> None:
        if dim_range is None or char_width <= 0:
            return

        left_col, right_col = dim_range
        left_px = left_col * char_width - offset
        right_px = right_col * char_width - offset
        painter.setPen(Qt.NoPen)
        if left_px > 0:
            painter.fillRect(QRectF(0.0, 0.0, min(left_px, widget_width), widget_height), dim_color)
        if right_px < widget_width:
            right_start = max(right_px, 0.0)
            painter.fillRect(
                QRectF(right_start, 0.0, widget_width - right_start, widget_height),
                dim_color,
            )
