# features/annotation_layer/annotation_layer_widget.py
"""
Sabit annotasyon şeridi — position ruler altında, consensus üstünde.

Adım 2 değişikliği
------------------
Artık AnnotationStore yerine AlignmentDataModel'den besleniyor.
- model.is_aligned = True  → model.global_annotations gösterilir
- model.is_aligned = False → widget gizlenir (yükseklik 0)
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from PyQt5.QtCore import Qt, QRectF, QPoint, pyqtSignal
from PyQt5.QtGui import QPainter, QPen, QBrush, QColor
from PyQt5.QtWidgets import QWidget, QScrollBar, QToolTip

from features.annotation_layer.annotation_layout_engine import (
    assign_lanes, lane_count,
)
from features.annotation_layer.annotation_painter import (
    draw_primer, draw_probe, draw_repeated_region,
)
from model.alignment_data_model import AlignmentDataModel
from model.annotation import Annotation, AnnotationType
from settings.theme import theme_manager

_LANE_HEIGHT  = 20
_LANE_PADDING =  3
_MIN_HEIGHT   = 24


class AnnotationLayerWidget(QWidget):

    annotationClicked       = pyqtSignal(object)   # Annotation
    annotationDoubleClicked = pyqtSignal(object)   # Annotation

    def __init__(
        self,
        model: AlignmentDataModel,
        sequence_viewer,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)

        self._model           = model
        self._sequence_viewer = sequence_viewer

        self._lane_assignment: Dict[str, int]               = {}
        self._annotations:     List[Annotation]             = []
        self._hit_rects:       List[Tuple[QRectF, Annotation]] = []

        self.setMouseTracking(True)
        self._sync_from_model()

        # Global annotation sinyalleri
        self._model.globalAnnotationAdded.connect(self._on_global_changed)
        self._model.globalAnnotationRemoved.connect(self._on_global_changed)
        self._model.globalAnnotationUpdated.connect(self._on_global_changed)
        # Hizalama durumu değişince göster/gizle
        self._model.alignmentStateChanged.connect(self._on_alignment_changed)
        # Model reset
        self._model.modelReset.connect(self._on_global_changed)

        hbar: QScrollBar = self._sequence_viewer.horizontalScrollBar()
        hbar.valueChanged.connect(self.update)
        hbar.rangeChanged.connect(self.update)

        anim = getattr(self._sequence_viewer, "_zoom_animation", None)
        if anim is not None:
            anim.valueChanged.connect(self.update)

        theme_manager.themeChanged.connect(lambda _: self.update())
        try:
            from settings.annotation_styles import annotation_style_manager as _asm
            _asm.stylesChanged.connect(lambda: self.update())
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Model senkronizasyonu
    # ------------------------------------------------------------------

    def _sync_from_model(self) -> None:
        """Model'den global annotation'ları oku ve layout'u güncelle."""
        if self._model.is_aligned:
            self._annotations    = list(self._model.global_annotations)
        else:
            self._annotations    = []
        self._lane_assignment = assign_lanes(self._annotations)
        self._update_visibility()
        self.update()

    def _update_visibility(self) -> None:
        """is_aligned ve annotation sayısına göre yüksekliği ayarla."""
        if not self._model.is_aligned or not self._annotations:
            self.setFixedHeight(0)
            self.setVisible(False)
            return
        n = lane_count(self._lane_assignment)
        h = max(_MIN_HEIGHT, n * (_LANE_HEIGHT + _LANE_PADDING) + _LANE_PADDING)
        self.setFixedHeight(h)
        self.setVisible(True)

    # ------------------------------------------------------------------
    # Slot'lar
    # ------------------------------------------------------------------

    def _on_global_changed(self, *_args) -> None:
        self._sync_from_model()

    def _on_alignment_changed(self, is_aligned: bool) -> None:
        self._sync_from_model()

    # ------------------------------------------------------------------
    # Geometri
    # ------------------------------------------------------------------

    def _get_char_width(self) -> float:
        if hasattr(self._sequence_viewer, "_get_current_char_width"):
            return float(self._sequence_viewer._get_current_char_width())
        return float(self._sequence_viewer.char_width)

    def _get_view_left(self) -> float:
        return float(self._sequence_viewer.horizontalScrollBar().value())

    def _annotation_viewport_rect(
        self, ann: Annotation, lane: int, cw: float, view_left: float
    ) -> Optional[QRectF]:
        x = ann.start * cw - view_left
        w = ann.length() * cw
        y = _LANE_PADDING + lane * (_LANE_HEIGHT + _LANE_PADDING)
        h = _LANE_HEIGHT
        widget_w = float(self.width())
        if x + w < 0 or x > widget_w:
            return None
        if x < 0:
            w += x; x = 0.0
        if x + w > widget_w:
            w = widget_w - x
        if w <= 0:
            return None
        return QRectF(x, y, w, h)

    # ------------------------------------------------------------------
    # paintEvent
    # ------------------------------------------------------------------

    def paintEvent(self, event) -> None:
        if not self.isVisible() or self.height() == 0:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.TextAntialiasing, True)

        t    = theme_manager.current
        rect = self.rect()

        painter.fillRect(rect, QBrush(t.row_bg_even))
        painter.setPen(QPen(t.border_normal))
        painter.drawLine(0, rect.bottom() - 1, rect.right(), rect.bottom() - 1)

        if not self._annotations:
            painter.setPen(QPen(QColor(t.text_primary).lighter(150)))
            painter.drawText(rect.adjusted(6, 0, 0, 0),
                             Qt.AlignVCenter | Qt.AlignLeft, "Global Annotations")
            painter.end()
            return

        cw        = self._get_char_width()
        view_left = self._get_view_left()

        self._hit_rects.clear()

        for ann in self._annotations:
            lane = self._lane_assignment.get(ann.id, 0)
            vp   = self._annotation_viewport_rect(ann, lane, cw, view_left)
            if vp is None:
                continue

            painter.save()

            ann_char_w = vp.width() / max(ann.length(), 1)
            if ann.type == AnnotationType.PRIMER:
                draw_primer(painter, vp.x(), vp.y(), vp.width(), vp.height(),
                            ann.resolved_color(), ann.label,
                            strand=ann.strand, char_width=ann_char_w)
            elif ann.type == AnnotationType.PROBE:
                draw_probe(painter, vp.x(), vp.y(), vp.width(), vp.height(),
                           ann.resolved_color(), ann.label,
                           strand=ann.strand, char_width=ann_char_w)
            else:  # REPEATED_REGION
                draw_repeated_region(painter, vp.x(), vp.y(), vp.width(), vp.height(),
                                     ann.resolved_color(), ann.label)

            painter.restore()
            self._hit_rects.append((vp, ann))

        painter.end()

    # ------------------------------------------------------------------
    # Mouse
    # ------------------------------------------------------------------

    def _annotation_at(self, pos: QPoint) -> Optional[Annotation]:
        p = QRectF(pos.x(), pos.y(), 1, 1)
        for rect, ann in self._hit_rects:
            if rect.intersects(p):
                return ann
        return None

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            ann = self._annotation_at(event.pos())
            if ann is not None:
                self.annotationClicked.emit(ann)
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            ann = self._annotation_at(event.pos())
            if ann is not None:
                self.annotationDoubleClicked.emit(ann)
            event.accept()
        else:
            super().mouseDoubleClickEvent(event)

    def mouseMoveEvent(self, event) -> None:
        ann = self._annotation_at(event.pos())
        if ann is not None:
            QToolTip.showText(event.globalPos(), ann.tooltip_text(), self)
        else:
            QToolTip.hideText()
        super().mouseMoveEvent(event)