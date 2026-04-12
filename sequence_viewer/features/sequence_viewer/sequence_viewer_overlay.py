# features/sequence_viewer/sequence_viewer_overlay.py
from __future__ import annotations
from PyQt5.QtCore import Qt, QPointF, QRectF
from PyQt5.QtGui import QPainter, QPen, QColor, QBrush
from sequence_viewer.settings.theme import theme_manager

_GUIDE_WIDTH = 1


class OverlayMixin:
    """
    Drawing / overlay state for SequenceViewerView.

    Handles:
      - Row-band highlight (horizontal guides from header selection)
      - Selection dim overlay
      - Vertical guide lines

    Depends on the host providing:
        self.viewport()
        self.horizontalScrollBar()
        self.verticalScrollBar()
        self._row_layout
        self._per_row_annot_h
        self.char_height
        self.parent()
        self._effective_char_width()
    """

    def _init_overlay(self):
        self._v_guide_cols: list = []
        self._v_guide_observers: list = []
        self._h_guide_rows: frozenset = frozenset()
        self._selection_dim_ranges: list = []  # [(left_col, right_col), ...] focus alanlarÄ±
        self._caret = None  # (col, row) veya None â€” tek tÄ±klama pozisyonu

    # ------------------------------------------------------------------
    # Vertical guide public API
    # ------------------------------------------------------------------

    def set_v_guides(self, cols: list):
        self._v_guide_cols = list(cols)
        self.viewport().update()
        for cb in self._v_guide_observers:
            cb()

    def clear_v_guides(self):
        self._v_guide_cols = []
        self.viewport().update()
        for cb in self._v_guide_observers:
            cb()

    def add_v_guide_observer(self, callback):
        self._v_guide_observers.append(callback)

    # ------------------------------------------------------------------
    # Caret (metin kursÃ¶rÃ¼) public API
    # ------------------------------------------------------------------

    def set_caret(self, col: int, row: int):
        """Belirtilen kolon/satÄ±r kesiÅŸimine I-beam caret koy."""
        self._caret = (col, row)
        self.viewport().update()

    def clear_caret(self):
        if self._caret is not None:
            self._caret = None
            self.viewport().update()

    # Backwards-compat single-guide API
    def set_guide_cols(self, start_col, end_col):
        self._v_guide_cols = [start_col, end_col + 1]
        self.viewport().update()

    def clear_guide_cols(self):
        self._v_guide_cols = []
        self.viewport().update()

    # ------------------------------------------------------------------
    # Horizontal guide public API
    # ------------------------------------------------------------------

    def set_h_guides(self, row_indices):
        self._h_guide_rows = row_indices
        for i, item in enumerate(getattr(self, "sequence_items", [])):
            item.set_row_highlighted(i in self._h_guide_rows)
        self.viewport().update()

    def clear_h_guides(self):
        if self._h_guide_rows:
            self._h_guide_rows = frozenset()
            for item in getattr(self, "sequence_items", []):
                item.set_row_highlighted(False)
            self.viewport().update()

    # ------------------------------------------------------------------
    # Selection dim public API
    # ------------------------------------------------------------------

    def set_selection_dim_range(self, left_col: int, right_col: int):
        self._selection_dim_ranges = [(left_col, right_col)]
        self.viewport().update()
        for cb in self._v_guide_observers:
            cb()

    def set_selection_focus_ranges(self, ranges: list):
        """Birden fazla focus aralÄ±ÄŸÄ± ayarla â€” aralarÄ±ndaki boÅŸluklar karartÄ±lÄ±r."""
        self._selection_dim_ranges = list(ranges)
        self.viewport().update()
        for cb in self._v_guide_observers:
            cb()

    def clear_selection_dim_range(self):
        if self._selection_dim_ranges:
            self._selection_dim_ranges = []
            self.viewport().update()
            for cb in self._v_guide_observers:
                cb()

    @property
    def _selection_dim_range(self):
        """Geriye dÃ¶nÃ¼k uyumluluk: ilk aralÄ±ÄŸÄ± dÃ¶ndÃ¼rÃ¼r veya None."""
        return self._selection_dim_ranges[0] if self._selection_dim_ranges else None

    # ------------------------------------------------------------------
    # QGraphicsView paint hooks
    # ------------------------------------------------------------------

    def drawBackground(self, painter, rect):
        t = theme_manager.current
        layout = self._row_layout
        if layout is None or layout.row_count == 0:
            painter.fillRect(rect, t.seq_bg)
            return
        vis_top, vis_bottom = rect.top(), rect.bottom()
        painter.fillRect(rect, t.seq_bg)
        for i in range(layout.row_count):
            y_top = float(layout.y_offsets[i])
            y_bottom = y_top + float(layout.row_strides[i])
            if y_bottom < vis_top or y_top > vis_bottom:
                continue
            # SeÃ§ili satÄ±r ise row_band_highlight, deÄŸilse normal arka plan
            if i in self._h_guide_rows:
                row_bg = QColor(t.row_band_highlight)
            else:
                row_bg = t.row_bg_even if i % 2 == 0 else t.row_bg_odd
            painter.fillRect(QRectF(rect.left(), y_top, rect.width(), y_bottom - y_top), row_bg)

    def drawForeground(self, painter, rect):
        super().drawForeground(painter, rect)
        t = theme_manager.current
        self._draw_row_band_border_lines(painter, t)
        self._draw_selection_dim_overlay(painter, t)
        self._draw_vertical_guides(painter, t)
        self._draw_caret(painter, t)

    # ------------------------------------------------------------------
    # drawForeground sub-renderers
    # ------------------------------------------------------------------

    def _draw_row_band_border_lines(self, painter, t):
        """SeÃ§ili satÄ±rlarÄ±n Ã¼st ve alt kenar Ã§izgilerini Ã§izer."""
        if not self._h_guide_rows:
            return
        layout = self._row_layout
        vp_w = float(self.viewport().width())
        vp_h = float(self.viewport().height())
        v_off = self._viewport_vertical_offset()

        painter.save()
        painter.resetTransform()

        # Sadece kenar Ã§izgilerini Ã§iz
        h_pen = QPen(theme_manager.current.guide_line_color, _GUIDE_WIDTH, Qt.SolidLine)
        painter.setPen(h_pen)
        for row in self._h_guide_rows:
            top_scene, bottom_scene = self._row_scene_extent(row, layout)
            for vp_y in (top_scene - v_off, bottom_scene - v_off):
                if -2 <= vp_y <= vp_h + 2:
                    painter.drawLine(QPointF(0, vp_y), QPointF(vp_w, vp_y))

        painter.restore()

    def _draw_selection_dim_overlay(self, painter, t):
        if not self._selection_dim_ranges:
            return
        cw = self._effective_char_width()
        if cw <= 0:
            return
        offset = self._viewport_horizontal_offset()
        vp_w = float(self.viewport().width())
        vp_h = float(self.viewport().height())
        dim_color = QColor(t.selection_dim_color)
        sorted_ranges = sorted(self._selection_dim_ranges, key=lambda r: r[0])

        painter.save()
        painter.resetTransform()
        painter.setPen(Qt.NoPen)

        prev_right_px = 0.0
        for left_col, right_col in sorted_ranges:
            left_px = left_col * cw - offset
            right_px = right_col * cw - offset
            # Focus aralÄ±ÄŸÄ±nÄ±n solundaki boÅŸluÄŸu karart
            if left_px > prev_right_px:
                x = max(prev_right_px, 0.0)
                w = min(left_px, vp_w) - x
                if w > 0:
                    painter.fillRect(QRectF(x, 0.0, w, vp_h), dim_color)
            prev_right_px = max(prev_right_px, right_px)

        # Son focus aralÄ±ÄŸÄ±nÄ±n saÄŸÄ±ndaki her ÅŸeyi karart
        if prev_right_px < vp_w:
            r = max(prev_right_px, 0.0)
            painter.fillRect(QRectF(r, 0.0, vp_w - r, vp_h), dim_color)

        painter.restore()

    def _draw_vertical_guides(self, painter, t):
        if not self._v_guide_cols:
            return
        cw = self._effective_char_width()
        if cw <= 0:
            return
        offset = self._viewport_horizontal_offset()
        vp_w = float(self.viewport().width())

        draw_top = min(self._find_ruler_bottom_in_viewport(), 0.0)
        draw_bottom = float(self.viewport().height())
        consensus_bottom = self._find_consensus_bottom_in_viewport()
        if consensus_bottom > draw_bottom:
            draw_bottom = consensus_bottom

        painter.save()
        painter.resetTransform()
        pen = QPen(theme_manager.current.guide_line_color, _GUIDE_WIDTH, Qt.DashLine)
        pen.setDashPattern([4, 3])
        painter.setPen(pen)
        for col in self._v_guide_cols:
            vp_x = col * cw - offset
            if -10 <= vp_x <= vp_w + 10:
                painter.drawLine(QPointF(vp_x, draw_top), QPointF(vp_x, draw_bottom))
        painter.restore()

    def _draw_caret(self, painter, t):
        """TÄ±klanan satÄ±rda dÃ¼z I-beam (metin kursÃ¶rÃ¼) Ã§izer."""
        if self._caret is None:
            return
        col, row = self._caret
        cw = self._effective_char_width()
        if cw <= 0:
            return
        layout = self._row_layout
        if layout is None or row < 0 or row >= layout.row_count:
            return

        offset_h = self._viewport_horizontal_offset()
        offset_v = self._viewport_vertical_offset()
        vp_w = float(self.viewport().width())
        vp_h = float(self.viewport().height())

        x = col * cw - offset_h
        if not (-10 <= x <= vp_w + 10):
            return

        y_top = float(layout.seq_y_offsets[row]) - offset_v
        y_bottom = float(layout.below_y_offsets[row]) - offset_v
        if y_bottom < 0 or y_top > vp_h:
            return

        caret_color = QColor(theme_manager.current.i_beam)
        caret_color.setAlpha(255)

        painter.save()
        painter.resetTransform()
        pen = QPen(caret_color, 3, Qt.SolidLine)
        pen.setCapStyle(Qt.FlatCap)
        painter.setPen(pen)
        painter.drawLine(QPointF(x, y_top), QPointF(x, y_bottom))
        painter.restore()

    # ------------------------------------------------------------------
    # Viewport coordinate helpers
    # ------------------------------------------------------------------

    def _viewport_vertical_offset(self) -> float:
        return float(self.verticalScrollBar().value())

    def _viewport_horizontal_offset(self) -> float:
        return float(self.horizontalScrollBar().value())

    def _row_scene_extent(self, row, layout):
        """Returns (top_scene_y, bottom_scene_y) for the given row."""
        if layout is not None and row < layout.row_count:
            top = float(layout.y_offsets[row])
            bottom = top + float(layout.row_strides[row])
        else:
            stride = self._per_row_annot_h + self.char_height
            top = float(row * stride)
            bottom = top + float(stride)
        return top, bottom

    def _find_ruler_bottom_in_viewport(self) -> float:
        """
        Returns the y coordinate (in viewport space) of the bottom edge of the
        SequencePositionRulerWidget sibling, or 0.0 if not found.
        """
        try:
            from sequence_viewer.features.position_ruler.position_ruler_widget import SequencePositionRulerWidget
            p = self.parent()
            while p is not None:
                for child in p.children():
                    if isinstance(child, SequencePositionRulerWidget):
                        child_bottom_global = child.mapToGlobal(child.rect().bottomLeft())
                        vp_top_global = self.viewport().mapToGlobal(self.viewport().rect().topLeft())
                        return float(child_bottom_global.y() - vp_top_global.y())
                p = p.parent()
        except Exception:
            pass
        return 0.0

    def _find_consensus_bottom_in_viewport(self) -> float:
        """
        Returns the y coordinate (in viewport space) of the bottom edge of the
        ConsensusRowWidget sibling, or viewport height if not found.
        """
        default = float(self.viewport().height())
        try:
            from sequence_viewer.features.consensus_row.consensus_row_widget import ConsensusRowWidget
            p = self.parent()
            while p is not None:
                for child in p.children():
                    if isinstance(child, ConsensusRowWidget) and child.isVisible() and child.height() > 0:
                        child_bottom_global = child.mapToGlobal(child.rect().bottomLeft())
                        vp_top_global = self.viewport().mapToGlobal(self.viewport().rect().topLeft())
                        return float(child_bottom_global.y() - vp_top_global.y())
                p = p.parent()
        except Exception:
            pass
        return default


