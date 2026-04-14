from __future__ import annotations

import math

from PyQt5.QtCore import QPointF, QRectF, Qt
from PyQt5.QtGui import QBrush, QColor, QFont, QPainter, QPen

from sequence_viewer.features.annotation_layer.annotation_layout_engine import (
    build_side_geometry,
    partition_annotations_by_side,
    side_strip_height,
)
from sequence_viewer.features.annotation_layer.annotation_painter import (
    draw_hover_overlay,
    draw_mismatch_marker,
    draw_primer,
    draw_probe,
    draw_repeated_region,
    draw_selection_outline,
)
from sequence_viewer.graphics.sequence_item.sequence_glyph_cache import GLYPH_CACHE
from sequence_viewer.model.annotation import AnnotationType
from sequence_viewer.settings.display_settings_manager import display_settings_manager
from sequence_viewer.settings.theme import theme_manager


class ConsensusRenderer:
    def render(self, widget, painter: QPainter) -> list:
        rect = widget.rect()
        width = rect.width()
        height = rect.height()
        theme = theme_manager.current

        is_selected = widget._is_selected
        bg_color = QColor(theme.row_band_highlight) if is_selected else theme.row_bg_odd
        painter.fillRect(rect, QBrush(bg_color))
        painter.setPen(QPen(theme.border_normal))
        painter.drawLine(0, height - 1, width, height - 1)
        if is_selected and not widget._selected_ann_ids:
            h_pen = QPen(theme.guide_line_color, 1, Qt.SolidLine)
            painter.setPen(h_pen)
            painter.drawLine(0, height - 1, width, height - 1)

        sequences = [seq for _, seq in widget._alignment_model.all_rows()]
        char_h = float(int(round(widget._sequence_viewer.char_height)))
        if not sequences:
            label_font = QFont("Arial")
            label_font.setPointSizeF(max(1.0, char_h * 0.5))
            painter.setPen(QPen(theme.text_primary))
            painter.setFont(label_font)
            painter.drawText(rect.adjusted(6, 0, 0, 0), Qt.AlignVCenter | Qt.AlignLeft, "—")
            return []

        consensus = widget._model.get_consensus(sequences)
        if not consensus:
            return []

        char_width = widget._get_char_width()
        view_left = widget._get_view_left()
        if char_width <= 0:
            return []

        widget._sync_font_from_viewer()
        painter.setFont(widget._font)
        mode = widget._effective_mode()
        annotations = list(widget._alignment_model.consensus_annotations) if widget._alignment_model.is_aligned else []
        above_annotations, _ = partition_annotations_by_side(annotations)
        above_h = float(side_strip_height(above_annotations))
        seq_char_h = float(int(round(widget._sequence_viewer.char_height)))
        seq_top = above_h
        start_col = max(0, int(math.floor(view_left / char_width)))
        end_col = min(len(consensus), int(math.ceil((view_left + width) / char_width)))
        selection_ranges = widget._selection_ranges
        hit_rects = []

        if mode == "line":
            self._render_line_mode(
                painter, theme, start_col, end_col, char_width, view_left, width, seq_top, seq_char_h, selection_ranges
            )
            self._paint_dim_overlay(painter, widget, char_width, float(width), float(height), theme)
            return []

        if selection_ranges:
            sel_color = QColor(theme.seq_selection_bg)
            painter.setBrush(QBrush(sel_color))
            painter.setPen(Qt.NoPen)
            for sel_s, sel_e in selection_ranges:
                sel_l = max(sel_s, start_col)
                sel_r = min(sel_e, end_col)
                if sel_r > sel_l:
                    for col in range(sel_l, sel_r):
                        painter.drawRect(QRectF(col * char_width - view_left, seq_top, char_width, seq_char_h))

        font_pt = widget._font.pointSizeF()
        box_ref = min(seq_char_h * 0.7, font_pt)
        box_h = max(box_ref, 1.0)
        box_y = seq_top + (seq_char_h - box_h) / 2.0
        for col in range(start_col, end_col):
            base = consensus[col].upper()
            x = col * char_width - view_left
            selected = any(s <= col < e for s, e in selection_ranges)
            color = QColor(255, 255, 255) if selected else widget._color_map.get(base, theme.text_primary)
            if mode == "box":
                painter.setBrush(QBrush(color))
                painter.setPen(Qt.NoPen)
                painter.drawRect(QRectF(x, box_y, char_width, box_h))
            else:
                glyph = GLYPH_CACHE.get_glyph(base, widget._font, color)
                dx = x + (char_width - glyph.width()) / 2.0
                dy = seq_top + (seq_char_h - glyph.height()) / 2.0
                painter.drawPixmap(int(dx), int(dy), glyph)

        hit_rects = self._render_annotations(
            painter, widget, annotations, char_width, view_left, float(width), seq_char_h
        )
        self._paint_dim_overlay(painter, widget, char_width, float(width), float(height), theme)
        self._render_guides(painter, widget, char_width, seq_top, seq_char_h)
        return hit_rects

    def _render_line_mode(self, painter, theme, start_col, end_col, char_width, view_left, width, seq_top, seq_char_h, selection_ranges):
        line_h = seq_char_h * 0.3
        y = seq_top + (seq_char_h - line_h) / 2.0
        x_start = max(0.0, start_col * char_width - view_left)
        x_end = min(end_col * char_width - view_left, float(width))
        draw_width = max(0.0, x_end - x_start)
        painter.setBrush(QBrush(theme.seq_line_fg))
        painter.setPen(Qt.NoPen)
        painter.drawRect(QRectF(x_start, y, draw_width, line_h))
        if selection_ranges:
            sel_color = QColor(theme.seq_selection_bg)
            painter.setBrush(QBrush(sel_color))
            for sel_s, sel_e in selection_ranges:
                sx = sel_s * char_width - view_left
                sw = (sel_e - sel_s) * char_width
                sx2 = max(0.0, sx)
                sw2 = min(sw - (sx2 - sx), float(width) - sx2)
                if sw2 > 0:
                    painter.drawRect(QRectF(sx2, seq_top, sw2, seq_char_h))

    def _render_annotations(self, painter, widget, annotations, char_width, view_left, widget_w, seq_char_h):
        hit_rects = []
        if not annotations:
            return hit_rects
        from sequence_viewer.settings.annotation_styles import annotation_style_manager

        lane_h = annotation_style_manager.get_lane_height()
        above_annotations, below_annotations = partition_annotations_by_side(annotations)
        above_geometry = build_side_geometry(above_annotations)
        below_geometry = build_side_geometry(below_annotations)
        above_assignment = above_geometry.lane_assignment
        below_assignment = below_geometry.lane_assignment
        above_h = side_strip_height(above_annotations)
        seq_top = float(above_h)
        painter.setRenderHint(QPainter.Antialiasing, True)
        parent_by_id = {ann.id: ann for ann in annotations}
        for ann in annotations:
            x = ann.start * char_width - view_left
            ann_width = char_width if ann.type == AnnotationType.MISMATCH_MARKER else ann.length() * char_width
            if x + ann_width < 0 or x > widget_w:
                continue
            clipped_x = max(x, 0.0)
            clipped_w = min(ann_width - (clipped_x - x), widget_w - clipped_x)
            if clipped_w <= 0:
                continue
            ann_char_w = clipped_w / max(ann.length(), 1)
            parent = parent_by_id.get(ann.parent_id)
            is_above = (
                parent.type.is_above_sequence()
                if ann.type == AnnotationType.MISMATCH_MARKER and parent is not None
                else ann.type.is_above_sequence()
            )
            if is_above:
                lane = above_assignment.get(ann.id, 0)
                ann_y = (
                    above_geometry.marker_y(above_assignment.get(ann.parent_id, 0), above=True, lane_height=lane_h)
                    if ann.type == AnnotationType.MISMATCH_MARKER
                    else above_geometry.parent_y(lane, above=True, lane_height=lane_h)
                )
            else:
                lane = below_assignment.get(ann.id, 0)
                ann_y = seq_top + seq_char_h + (
                    below_geometry.marker_y(below_assignment.get(ann.parent_id, 0), above=False, lane_height=lane_h)
                    if ann.type == AnnotationType.MISMATCH_MARKER
                    else below_geometry.parent_y(lane, above=False, lane_height=lane_h)
                )

            ann_color = ann.resolved_color()
            ann_strand = getattr(ann, "strand", "+")
            painter.save()
            if ann.type == AnnotationType.PRIMER:
                draw_primer(painter, clipped_x, ann_y, clipped_w, lane_h, ann_color, ann.label, strand=ann_strand, char_width=ann_char_w)
            elif ann.type == AnnotationType.PROBE:
                draw_probe(painter, clipped_x, ann_y, clipped_w, lane_h, ann_color, ann.label, strand=ann_strand, char_width=ann_char_w)
            elif ann.type == AnnotationType.MISMATCH_MARKER:
                draw_mismatch_marker(
                    painter, clipped_x, ann_y, clipped_w, lane_h, ann_color,
                    ann.expected_base or ann.mismatch_base or ann.label,
                    char_width=char_width,
                    font_family=widget._font.family(),
                    font_size=display_settings_manager.consensus_font_size_base,
                )
            else:
                draw_repeated_region(painter, clipped_x, ann_y, clipped_w, lane_h, ann_color, ann.label)

            selected = ann.id in widget._selected_ann_ids
            hovered = ann.id == widget._hovered_ann_id
            if hovered and not selected:
                draw_hover_overlay(painter, clipped_x, ann_y, clipped_w, lane_h, ann.type, ann_color, strand=ann_strand, char_width=ann_char_w)
            if selected:
                draw_selection_outline(painter, clipped_x, ann_y, clipped_w, lane_h, ann.type, ann_color, strand=ann_strand, char_width=ann_char_w)
            painter.restore()
            hit_rects.append((QRectF(clipped_x, ann_y, clipped_w, lane_h), ann))
        painter.setRenderHint(QPainter.Antialiasing, False)
        return hit_rects

    def _render_guides(self, painter, widget, char_width, seq_top, seq_char_h):
        ctrl = widget._get_controller()
        if ctrl is not None and ctrl._v_guide_cols:
            offset = float(widget._sequence_viewer.horizontalScrollBar().value())
            vp_w = float(widget.width())
            pen = QPen(theme_manager.current.guide_line_color, 1, Qt.DashLine)
            pen.setDashPattern([4, 3])
            painter.setPen(pen)
            for gcol in ctrl._v_guide_cols:
                vp_x = gcol * char_width - offset
                if -10 <= vp_x <= vp_w + 10:
                    painter.drawLine(QPointF(vp_x, 0), QPointF(vp_x, float(widget.height())))

        caret = getattr(widget._sequence_viewer, "_caret", None)
        if caret is not None and caret[1] == -1:
            offset = float(widget._sequence_viewer.horizontalScrollBar().value())
            vp_w = float(widget.width())
            vp_x = caret[0] * char_width - offset
            if -10 <= vp_x <= vp_w + 10:
                caret_color = QColor(theme_manager.current.i_beam)
                caret_color.setAlpha(255)
                pen = QPen(caret_color, 3, Qt.SolidLine)
                pen.setCapStyle(Qt.FlatCap)
                painter.setPen(pen)
                painter.drawLine(QPointF(vp_x, seq_top), QPointF(vp_x, seq_top + seq_char_h))

    def _paint_dim_overlay(self, painter, sequence_viewer, char_width, widget_w, widget_h, theme):
        dim_ranges = getattr(sequence_viewer, "selection_dim_ranges", [])
        if not dim_ranges or char_width <= 0:
            return
        offset = float(sequence_viewer.horizontalScrollBar().value())
        dim_color = QColor(theme.selection_dim_color)
        sorted_ranges = sorted(dim_ranges, key=lambda r: r[0])
        painter.setPen(Qt.NoPen)
        prev_right_px = 0.0
        for left_col, right_col in sorted_ranges:
            left_px = left_col * char_width - offset
            right_px = right_col * char_width - offset
            if left_px > prev_right_px:
                x = max(prev_right_px, 0.0)
                width = min(left_px, widget_w) - x
                if width > 0:
                    painter.fillRect(QRectF(x, 0.0, width, widget_h), dim_color)
            prev_right_px = max(prev_right_px, right_px)
        if prev_right_px < widget_w:
            right = max(prev_right_px, 0.0)
            painter.fillRect(QRectF(right, 0.0, widget_w - right, widget_h), dim_color)
