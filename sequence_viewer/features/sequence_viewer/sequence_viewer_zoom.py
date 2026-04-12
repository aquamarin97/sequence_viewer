# features/sequence_viewer/sequence_viewer_zoom.py
from __future__ import annotations
from PyQt5.QtCore import QEasingCurve, QVariantAnimation


class ZoomMixin:
    """
    Zoom / char-width / horizontal-centering logic for SequenceViewerView.

    Depends on the host class providing:
        self.char_width          (float, settable)
        self.sequence_items      (list of SequenceGraphicsItem)
        self.scene               (QGraphicsScene)
        self.viewport()          (QWidget)
        self.horizontalScrollBar()
        self.trailing_padding_line_px / trailing_padding_text_px
        self.max_sequence_length (int, settable)
        self._per_row_annot_h    (int)
        self._update_scene_rect()
        SequenceGraphicsItem.LINE_MODE
    """

    def _init_zoom(self):
        self._zoom_animation = QVariantAnimation(self)
        self._zoom_animation.setEasingCurve(QEasingCurve.OutCubic)
        self._zoom_animation.valueChanged.connect(self._on_zoom_value_changed)
        self._zoom_center_nt = None
        self._zoom_view_width_px = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def current_char_width(self):
        return self._effective_char_width()

    def compute_min_char_width(self):
        if not self.sequence_items:
            return self.char_width
        max_len = self.max_sequence_length
        if max_len <= 0:
            return self.char_width
        vp_w = self.viewport().width()
        if vp_w <= 0:
            return self.char_width
        trailing = max(self.trailing_padding_line_px, self._current_trailing_padding())
        available = vp_w - trailing
        if available <= 0:
            return 0.000001
        return max(available / float(max_len), 0.000001)

    def apply_char_width(self, new_char_width, center_nt=None, view_width_px=None):
        if view_width_px is None:
            view_width_px = float(self.viewport().width())
        if abs(new_char_width - self.char_width) < 0.0001 and center_nt is None:
            return
        applied = float(new_char_width)
        for item in self.sequence_items:
            item.set_char_width(applied)
        if self.sequence_items:
            applied = float(self.sequence_items[0].char_width)
        self.char_width = applied
        self._update_scene_rect()
        if center_nt is not None:
            self._recenter_horizontally(center_nt, view_width_px)
        self.scene.invalidate()
        self.viewport().update()

    def start_zoom_animation(self, target_char_width, center_nt, view_width_px=None):
        if view_width_px is None:
            view_width_px = float(self.viewport().width())
        current = self._get_current_char_width()
        if abs(target_char_width - current) < 0.0001:
            self.apply_char_width(target_char_width, center_nt, view_width_px)
            return
        if self._zoom_animation.state() == QVariantAnimation.Running:
            self._zoom_view_width_px = view_width_px
            self._zoom_animation.setEndValue(target_char_width)
            return
        self._zoom_center_nt = center_nt
        self._zoom_view_width_px = view_width_px
        self._zoom_animation.setDuration(180)
        self._zoom_animation.setStartValue(current)
        self._zoom_animation.setEndValue(target_char_width)
        self._zoom_animation.start()

    def zoom_to_nt_range(self, start_nt, end_nt):
        if not self.sequence_items:
            return
        a, b = float(start_nt), float(end_nt)
        if a == b:
            span_nt, center_nt = 1.0, a
        else:
            span_nt, center_nt = max(abs(b - a), 1.0), (min(a, b) + max(a, b)) / 2.0
        vp_w = float(self.viewport().width())
        if vp_w <= 0:
            return
        desired = vp_w / span_nt
        new_cw = max(self.compute_min_char_width(), min(desired, 90.0))
        if abs(new_cw - self.char_width) > 0.0001:
            self.char_width = new_cw
            for item in self.sequence_items:
                item.set_char_width(self.char_width)
            self._update_scene_rect()
        self._recenter_horizontally(center_nt, vp_w)
        self.scene.invalidate()
        self.viewport().update()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _effective_char_width(self):
        if self._zoom_animation.state() == QVariantAnimation.Running:
            v = self._zoom_animation.currentValue()
            if v is not None:
                return float(v)
        if self.sequence_items:
            return float(self.sequence_items[0].char_width)
        return float(self.char_width)

    def _get_current_char_width(self):
        return self._effective_char_width()

    def _recenter_horizontally(self, center_nt, view_width_px):
        if view_width_px <= 0:
            view_width_px = float(self.viewport().width())
        if view_width_px <= 0:
            return
        scene_w = float(self.scene.sceneRect().width())
        if scene_w <= 0:
            return
        if self.max_sequence_length > 0:
            center_nt = max(0.0, min(center_nt, float(self.max_sequence_length)))
        cw = self._effective_char_width()
        ideal_left = center_nt * cw - view_width_px / 2.0
        max_left = max(0.0, scene_w - view_width_px)
        ideal_left = max(0.0, min(ideal_left, max_left))
        hbar = self.horizontalScrollBar()
        if abs(float(hbar.value()) - ideal_left) >= 0.5:
            hbar.setValue(int(round(ideal_left)))

    def _on_zoom_value_changed(self, value):
        if self._zoom_center_nt is None or self._zoom_view_width_px is None:
            return
        try:
            self.apply_char_width(float(value), self._zoom_center_nt, float(self._zoom_view_width_px))
        except Exception:
            pass

    def _current_trailing_padding(self):
        from sequence_viewer.graphics.sequence_item.sequence_item import SequenceGraphicsItem
        if not self.sequence_items:
            return self.trailing_padding_text_px
        for item in self.sequence_items:
            if item.display_mode == SequenceGraphicsItem.LINE_MODE:
                return self.trailing_padding_line_px
        return self.trailing_padding_text_px


