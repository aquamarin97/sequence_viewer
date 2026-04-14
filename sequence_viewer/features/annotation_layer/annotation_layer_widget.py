from __future__ import annotations

from PyQt5.QtCore import QPoint, QRectF, Qt, pyqtSignal
from PyQt5.QtGui import QBrush, QColor, QPainter, QPen
from PyQt5.QtWidgets import QToolTip, QWidget

from sequence_viewer.features.annotation_layer.annotation_layout_engine import build_side_geometry
from sequence_viewer.features.annotation_layer.annotation_renderer import AnnotationRenderer
from sequence_viewer.features.annotation_layer.annotation_viewport_calculator import (
    AnnotationViewportCalculator,
)
from sequence_viewer.model.annotation import AnnotationType
from sequence_viewer.settings.mouse_binding_manager import MouseAction, mouse_binding_manager
from sequence_viewer.settings.theme import theme_manager

_LANE_PADDING = 6
_MIN_HEIGHT = 24


def _lane_height() -> int:
    from sequence_viewer.settings.annotation_styles import annotation_style_manager

    return annotation_style_manager.get_lane_height()


class AnnotationLayerWidget(QWidget):
    annotationClicked = pyqtSignal(object)
    annotationDoubleClicked = pyqtSignal(object)

    def __init__(self, model, sequence_viewer, parent=None):
        super().__init__(parent)
        self._model = model
        self._sequence_viewer = sequence_viewer
        self._lane_assignment = {}
        self._annotations = []
        self._hit_rects = []
        self._side_geometry = build_side_geometry([])
        self._viewport_calculator = AnnotationViewportCalculator(
            self._side_geometry,
            self._lane_assignment,
        )
        self._renderer = AnnotationRenderer()
        self._selected_ann_ids: set = set()

        self.setMouseTracking(True)
        self._sync_from_model()
        self._model.globalAnnotationAdded.connect(self._on_global_changed)
        self._model.globalAnnotationRemoved.connect(self._on_global_changed)
        self._model.globalAnnotationUpdated.connect(self._on_global_changed)
        self._model.alignmentStateChanged.connect(self._on_alignment_changed)
        self._model.modelReset.connect(self._on_global_changed)

        hbar = self._sequence_viewer.horizontalScrollBar()
        hbar.valueChanged.connect(self.update)
        hbar.rangeChanged.connect(self.update)
        anim = getattr(self._sequence_viewer, "_zoom_animation", None)
        if anim:
            anim.valueChanged.connect(self.update)
        if hasattr(sequence_viewer, "add_v_guide_observer"):
            sequence_viewer.add_v_guide_observer(self.update)
        theme_manager.themeChanged.connect(lambda _: self.update())
        try:
            from sequence_viewer.settings.annotation_styles import (
                annotation_style_manager as _asm,
            )

            _asm.stylesChanged.connect(self._sync_from_model)
        except Exception:
            pass

    def _sync_from_model(self):
        self._annotations = list(self._model.global_annotations) if self._model.is_aligned else []
        self._side_geometry = build_side_geometry(self._annotations)
        self._lane_assignment = self._side_geometry.lane_assignment
        self._viewport_calculator = AnnotationViewportCalculator(
            self._side_geometry,
            self._lane_assignment,
        )
        self._update_visibility()
        self.update()

    def _update_visibility(self):
        if not self._model.is_aligned or not self._annotations:
            self.setFixedHeight(0)
            self.setVisible(False)
            return
        lane_count = self._side_geometry.total_lanes
        height = max(_MIN_HEIGHT, lane_count * (_lane_height() + _LANE_PADDING) + _LANE_PADDING)
        self.setFixedHeight(height)
        self.setVisible(True)

    def set_selected_annotation(self, ann_id, ctrl=False):
        if ctrl:
            if ann_id is None:
                return
            if ann_id in self._selected_ann_ids:
                self._selected_ann_ids.discard(ann_id)
            else:
                self._selected_ann_ids.add(ann_id)
        else:
            self._selected_ann_ids = {ann_id} if ann_id is not None else set()
        self.update()

    def clear_annotation_selection(self):
        if not self._selected_ann_ids:
            return
        self._selected_ann_ids.clear()
        self.update()

    def _on_global_changed(self, *_):
        self._sync_from_model()

    def _on_alignment_changed(self, _is_aligned):
        self._sync_from_model()

    def _get_char_width(self):
        return float(self._sequence_viewer.current_char_width())

    def _get_view_left(self):
        return float(self._sequence_viewer.horizontalScrollBar().value())

    def _annotation_viewport_rect(self, annotation, lane, char_width, view_left):
        return self._viewport_calculator.calc_rect(
            annotation,
            lane,
            char_width=char_width,
            view_left=view_left,
            widget_width=float(self.width()),
            lane_height=_lane_height(),
            lane_padding=_LANE_PADDING,
        )

    def _paint_background(self, painter, rect) -> None:
        theme = theme_manager.current
        painter.fillRect(rect, QBrush(theme.row_bg_even))
        painter.setPen(QPen(theme.border_normal))
        painter.drawLine(0, rect.bottom() - 1, rect.right(), rect.bottom() - 1)

    def _paint_empty_state(self, painter, rect) -> None:
        painter.setPen(QPen(QColor(theme_manager.current.text_primary).lighter(150)))
        painter.drawText(rect.adjusted(6, 0, 0, 0), Qt.AlignVCenter | Qt.AlignLeft, "Global Annotations")

    def _paint_annotations(self, painter, *, char_width: float, view_left: float) -> None:
        self._hit_rects.clear()
        for annotation in self._annotations:
            lane = self._lane_assignment.get(annotation.id, 0)
            rect = self._annotation_viewport_rect(annotation, lane, char_width, view_left)
            if rect is None:
                continue
            self._renderer.render_annotation(
                painter,
                annotation,
                rect,
                selected=(annotation.id in self._selected_ann_ids),
            )
            self._hit_rects.append((rect, annotation))

    def _paint_dim_overlay(self, painter, *, char_width: float) -> None:
        self._renderer.render_dim_effect(
            painter,
            self._sequence_viewer.selection_dim_range,
            char_width=char_width,
            offset=self._get_view_left(),
            widget_width=float(self.width()),
            widget_height=float(self.height()),
            dim_color=QColor(theme_manager.current.selection_dim_color),
        )

    def paintEvent(self, event):
        if not self.isVisible() or self.height() == 0:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.TextAntialiasing, True)
        rect = self.rect()
        self._paint_background(painter, rect)
        if not self._annotations:
            self._paint_empty_state(painter, rect)
            painter.end()
            return

        char_width = self._get_char_width()
        view_left = self._get_view_left()
        self._paint_annotations(painter, char_width=char_width, view_left=view_left)
        self._paint_dim_overlay(painter, char_width=char_width)
        painter.end()

    def _annotation_at(self, pos):
        point_rect = QRectF(pos.x(), pos.y(), 1, 1)
        for rect, annotation in self._hit_rects:
            if rect.intersects(point_rect):
                return annotation
        return None

    def mousePressEvent(self, event):
        action = mouse_binding_manager.resolve_annotation_click(event.modifiers(), event.button())
        handlers = {
            MouseAction.ANNOTATION_SELECT: self._handle_annotation_click,
            MouseAction.ANNOTATION_MULTI_SELECT: self._handle_annotation_click,
        }
        handler = handlers.get(action)
        if handler is None:
            super().mousePressEvent(event)
            return
        handler(event)
        event.accept()

    def _handle_annotation_click(self, event) -> None:
        annotation = self._annotation_at(event.pos())
        if annotation is not None:
            self._sequence_viewer.clear_caret()
            self.annotationClicked.emit(annotation)

    def mouseDoubleClickEvent(self, event):
        if mouse_binding_manager.is_annotation_edit_event(event.modifiers(), event.button()):
            annotation = self._annotation_at(event.pos())
            if annotation and annotation.type != AnnotationType.MISMATCH_MARKER:
                self.annotationDoubleClicked.emit(annotation)
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def mouseMoveEvent(self, event):
        annotation = self._annotation_at(event.pos())
        if annotation:
            QToolTip.showText(event.globalPos(), annotation.tooltip_text(), self)
        else:
            QToolTip.hideText()
        super().mouseMoveEvent(event)
