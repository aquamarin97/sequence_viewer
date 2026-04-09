# features/annotation_layer/annotation_layer_widget.py
from __future__ import annotations
from typing import Dict, List, Optional, Tuple
from PyQt5.QtCore import Qt, QRectF, QPoint, pyqtSignal
from PyQt5.QtGui import QPainter, QPen, QBrush, QColor
from PyQt5.QtWidgets import QWidget, QScrollBar, QToolTip
from features.annotation_layer.annotation_layout_engine import assign_lanes, lane_count
from features.annotation_layer.annotation_painter import draw_primer, draw_probe, draw_repeated_region, draw_selection_outline
from model.alignment_data_model import AlignmentDataModel
from model.annotation import Annotation, AnnotationType
from settings.theme import theme_manager

_LANE_HEIGHT = 20; _LANE_PADDING = 6; _MIN_HEIGHT = 24

class AnnotationLayerWidget(QWidget):
    annotationClicked = pyqtSignal(object)
    annotationDoubleClicked = pyqtSignal(object)

    def __init__(self, model, sequence_viewer, parent=None):
        super().__init__(parent)
        self._model = model; self._sequence_viewer = sequence_viewer
        self._lane_assignment = {}; self._annotations = []; self._hit_rects = []
        self._selected_ann_id = None
        self.setMouseTracking(True); self._sync_from_model()
        self._model.globalAnnotationAdded.connect(self._on_global_changed)
        self._model.globalAnnotationRemoved.connect(self._on_global_changed)
        self._model.globalAnnotationUpdated.connect(self._on_global_changed)
        self._model.alignmentStateChanged.connect(self._on_alignment_changed)
        self._model.modelReset.connect(self._on_global_changed)
        hbar = self._sequence_viewer.horizontalScrollBar()
        hbar.valueChanged.connect(self.update); hbar.rangeChanged.connect(self.update)
        anim = getattr(self._sequence_viewer, "_zoom_animation", None)
        if anim: anim.valueChanged.connect(self.update)
        if hasattr(sequence_viewer, 'add_v_guide_observer'):
            sequence_viewer.add_v_guide_observer(self.update)
        theme_manager.themeChanged.connect(lambda _: self.update())
        try:
            from settings.annotation_styles import annotation_style_manager as _asm
            _asm.stylesChanged.connect(lambda: self.update())
        except: pass

    def _sync_from_model(self):
        if self._model.is_aligned: self._annotations = list(self._model.global_annotations)
        else: self._annotations = []
        self._lane_assignment = assign_lanes(self._annotations)
        self._update_visibility(); self.update()

    def _update_visibility(self):
        if not self._model.is_aligned or not self._annotations:
            self.setFixedHeight(0); self.setVisible(False); return
        n = lane_count(self._lane_assignment)
        h = max(_MIN_HEIGHT, n * (_LANE_HEIGHT + _LANE_PADDING) + _LANE_PADDING)
        self.setFixedHeight(h); self.setVisible(True)

    def set_selected_annotation(self, ann_id):
        if self._selected_ann_id == ann_id: return
        self._selected_ann_id = ann_id; self.update()

    def _on_global_changed(self, *_): self._sync_from_model()
    def _on_alignment_changed(self, is_aligned): self._sync_from_model()

    def _get_char_width(self):
        if hasattr(self._sequence_viewer, "_get_current_char_width"):
            return float(self._sequence_viewer._get_current_char_width())
        return float(self._sequence_viewer.char_width)

    def _get_view_left(self): return float(self._sequence_viewer.horizontalScrollBar().value())

    def _annotation_viewport_rect(self, ann, lane, cw, view_left):
        x = ann.start * cw - view_left; w = ann.length() * cw
        y = _LANE_PADDING + lane * (_LANE_HEIGHT + _LANE_PADDING); h = _LANE_HEIGHT
        widget_w = float(self.width())
        if x + w < 0 or x > widget_w: return None
        if x < 0: w += x; x = 0.0
        if x + w > widget_w: w = widget_w - x
        if w <= 0: return None
        return QRectF(x, y, w, h)

    def paintEvent(self, event):
        if not self.isVisible() or self.height() == 0: return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True); painter.setRenderHint(QPainter.TextAntialiasing, True)
        t = theme_manager.current; rect = self.rect()
        painter.fillRect(rect, QBrush(t.row_bg_even))
        painter.setPen(QPen(t.border_normal)); painter.drawLine(0, rect.bottom()-1, rect.right(), rect.bottom()-1)
        if not self._annotations:
            painter.setPen(QPen(QColor(t.text_primary).lighter(150)))
            painter.drawText(rect.adjusted(6,0,0,0), Qt.AlignVCenter|Qt.AlignLeft, "Global Annotations")
            painter.end(); return
        cw = self._get_char_width(); view_left = self._get_view_left()
        self._hit_rects.clear()
        for ann in self._annotations:
            lane = self._lane_assignment.get(ann.id, 0)
            vp = self._annotation_viewport_rect(ann, lane, cw, view_left)
            if vp is None: continue
            painter.save()
            ann_char_w = vp.width() / max(ann.length(), 1)
            if ann.type == AnnotationType.PRIMER:
                draw_primer(painter, vp.x(), vp.y(), vp.width(), vp.height(), ann.resolved_color(), ann.label, strand=ann.strand, char_width=ann_char_w)
            elif ann.type == AnnotationType.PROBE:
                draw_probe(painter, vp.x(), vp.y(), vp.width(), vp.height(), ann.resolved_color(), ann.label, strand=ann.strand, char_width=ann_char_w)
            else:
                draw_repeated_region(painter, vp.x(), vp.y(), vp.width(), vp.height(), ann.resolved_color(), ann.label)
            if ann.id == self._selected_ann_id:
                draw_selection_outline(painter, vp.x(), vp.y(), vp.width(), vp.height(),
                                       ann.type, ann.resolved_color(),
                                       strand=getattr(ann, 'strand', '+'), char_width=ann_char_w)
            painter.restore(); self._hit_rects.append((vp, ann))
        # ---- Seçim odak efekti ----
        dim_range = getattr(self._sequence_viewer, '_selection_dim_range', None)
        if dim_range is not None and cw > 0:
            left_col, right_col = dim_range
            offset = float(self._sequence_viewer.horizontalScrollBar().value())
            ww = float(self.width()); wh = float(self.height())
            dim_color = QColor(t.selection_dim_color)
            left_px = left_col * cw - offset
            right_px = right_col * cw - offset
            painter.setPen(Qt.NoPen)
            if left_px > 0:
                painter.fillRect(QRectF(0.0, 0.0, min(left_px, ww), wh), dim_color)
            if right_px < ww:
                r = max(right_px, 0.0)
                painter.fillRect(QRectF(r, 0.0, ww - r, wh), dim_color)
        painter.end()

    def _annotation_at(self, pos):
        p = QRectF(pos.x(), pos.y(), 1, 1)
        for rect, ann in self._hit_rects:
            if rect.intersects(p): return ann
        return None

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            ann = self._annotation_at(event.pos())
            if ann: self.annotationClicked.emit(ann)
            event.accept()
        else: super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            ann = self._annotation_at(event.pos())
            if ann: self.annotationDoubleClicked.emit(ann)
            event.accept()
        else: super().mouseDoubleClickEvent(event)

    def mouseMoveEvent(self, event):
        ann = self._annotation_at(event.pos())
        if ann: QToolTip.showText(event.globalPos(), ann.tooltip_text(), self)
        else: QToolTip.hideText()
        super().mouseMoveEvent(event)
