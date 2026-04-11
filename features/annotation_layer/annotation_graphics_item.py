# features/annotation_layer/annotation_graphics_item.py
from __future__ import annotations
import weakref
from typing import Callable, Optional
from PyQt5.QtCore import Qt, QRectF
from PyQt5.QtGui import QPainter
from PyQt5.QtWidgets import QGraphicsItem, QStyleOptionGraphicsItem, QToolTip
from features.annotation_layer.annotation_painter import (
    draw_primer, draw_probe, draw_repeated_region, draw_mismatch_marker,
    draw_selection_outline, draw_hover_overlay,
)
from model.annotation import Annotation, AnnotationType
from settings.mouse_binding_manager import mouse_binding_manager, MouseAction
from settings.theme import theme_manager

ClickCallback = Callable[[Annotation, int], None]

class AnnotationGraphicsItem(QGraphicsItem):
    def __init__(self, annotation, row_index, ann_width, ann_height, on_click=None, on_double_click=None, parent=None):
        super().__init__(parent)
        self.annotation = annotation
        self.row_index = row_index
        self._w = float(ann_width); self._h = float(ann_height)
        self._on_click = on_click; self._on_double_click = on_double_click
        self.setAcceptedMouseButtons(Qt.LeftButton)
        self.setAcceptHoverEvents(True); self.setZValue(10.0)
        self._selected = False
        self._hovered  = False
        _ref = weakref.ref(self)
        theme_manager.themeChanged.connect(lambda _, r=_ref: (s := r()) and s.update())
        try:
            from settings.annotation_styles import annotation_style_manager as _asm
            _asm.stylesChanged.connect(lambda r=_ref: (s := r()) and s.update())
        except: pass

    def update_size(self, ann_width, ann_height):
        if abs(self._w - ann_width) < 0.01 and abs(self._h - ann_height) < 0.01:
            return
        self.prepareGeometryChange()
        self._w = float(ann_width)
        self._h = float(ann_height)
        self.update()

    def set_selected_visual(self, selected):
        if self._selected == selected:
            return
        self._selected = selected
        self.update()

    def boundingRect(self):
        return QRectF(0, 0, self._w, self._h)

    def paint(self, painter, option, widget=None):
        ann = self.annotation
        color = ann.resolved_color()
        painter.setRenderHint(QPainter.Antialiasing, True)
        char_width = self._w / max(ann.length(), 1)
        strand = getattr(ann, "strand", "+")
        if ann.type == AnnotationType.PRIMER:
            draw_primer(painter, 0, 0, self._w, self._h, color, ann.label,
                        strand=strand, char_width=char_width)
        elif ann.type == AnnotationType.PROBE:
            draw_probe(painter, 0, 0, self._w, self._h, color, ann.label,
                       strand=strand, char_width=char_width)
        elif ann.type == AnnotationType.MISMATCH_MARKER:
            from settings.display_settings_manager import display_settings_manager as _dsm
            draw_mismatch_marker(
                painter, 0, 0, self._w, self._h, color,
                ann.expected_base or ann.mismatch_base or ann.label,
                char_width=self._w,
                font_family=_dsm.sequence_font_family,
                font_size=_dsm.sequence_font_size_base,
            )
        else:
            draw_repeated_region(painter, 0, 0, self._w, self._h, color, ann.label)
        if self._hovered and not self._selected:
            draw_hover_overlay(painter, 0, 0, self._w, self._h, ann.type, color,
                               strand=strand, char_width=char_width)
        if self._selected:
            draw_selection_outline(painter, 0, 0, self._w, self._h, ann.type, color,
                                   strand=strand, char_width=char_width)

    def mousePressEvent(self, event):
        action = mouse_binding_manager.resolve_annotation_click(event.modifiers(), event.button())
        if action in (MouseAction.ANNOTATION_SELECT, MouseAction.ANNOTATION_MULTI_SELECT):
            if self._on_click:
                self._on_click(self.annotation, self.row_index)
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        if self.annotation.type == AnnotationType.MISMATCH_MARKER:
            event.accept()
            return
        if mouse_binding_manager.is_annotation_edit_event(event.modifiers(), event.button()):
            if self._on_double_click:
                self._on_double_click(self.annotation, self.row_index)
            event.accept()
        else:
            super().mouseDoubleClickEvent(event)

    def hoverEnterEvent(self, event):
        self._hovered = True
        self.setCursor(Qt.PointingHandCursor)
        self.update()
        scene_views = self.scene().views() if self.scene() else []
        if scene_views:
            vp = scene_views[0].viewport()
            global_pos = vp.mapToGlobal(scene_views[0].mapFromScene(event.scenePos()))
            QToolTip.showText(global_pos, self.annotation.tooltip_text(), vp)
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self._hovered = False
        self.unsetCursor()
        self.update()
        QToolTip.hideText()
        super().hoverLeaveEvent(event)
