# features/annotation_layer/annotation_graphics_item.py
from __future__ import annotations
from typing import Callable, Optional
from PyQt5.QtCore import Qt, QRectF
from PyQt5.QtGui import QPainter
from PyQt5.QtWidgets import QGraphicsItem, QStyleOptionGraphicsItem, QToolTip
from features.annotation_layer.annotation_painter import (
    draw_primer, draw_probe, draw_repeated_region,
)
from model.annotation import Annotation, AnnotationType
from settings.theme import theme_manager

ClickCallback = Callable[[Annotation, int], None]

class AnnotationGraphicsItem(QGraphicsItem):
    def __init__(
        self,
        annotation: Annotation,
        row_index:  int,
        ann_width:  float,
        ann_height: float,
        on_click:        Optional[ClickCallback] = None,
        on_double_click: Optional[ClickCallback] = None,
        parent: Optional[QGraphicsItem] = None,
    ) -> None:
        super().__init__(parent)
        self.annotation = annotation
        self.row_index  = row_index
        self._w         = float(ann_width)
        self._h         = float(ann_height)
        self._on_click        = on_click
        self._on_double_click = on_double_click
        self.setAcceptedMouseButtons(Qt.LeftButton)
        self.setAcceptHoverEvents(True)
        self.setZValue(10.0)
        self._selected: bool = False
        theme_manager.themeChanged.connect(self.update)

    def update_size(self, ann_width: float, ann_height: float) -> None:
        if abs(self._w - ann_width) < 0.01 and abs(self._h - ann_height) < 0.01:
            return
        self.prepareGeometryChange()
        self._w = float(ann_width)
        self._h = float(ann_height)
        self.update()

    def set_selected_visual(self, selected: bool) -> None:
        if self._selected == selected:
            return
        self._selected = selected
        self.update()

    def boundingRect(self) -> QRectF:
        return QRectF(0, 0, self._w, self._h)

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget=None) -> None:
        ann   = self.annotation
        color = ann.resolved_color()

        if self._selected:
            from PyQt5.QtGui import QPen, QColor
            painter.setPen(QPen(QColor(255, 255, 255), 1.5))
        else:
            painter.setPen(Qt.NoPen)

        painter.setRenderHint(QPainter.Antialiasing, True)

        # char_width: annotation genişliğini annotation uzunluğuna bölerek elde edilir
        char_width = self._w / max(ann.length(), 1)

        if ann.type == AnnotationType.PRIMER:
            draw_primer(painter, 0, 0, self._w, self._h, color, ann.label,
                        strand=ann.strand, char_width=char_width)
        elif ann.type == AnnotationType.PROBE:
            draw_probe(painter, 0, 0, self._w, self._h, color, ann.label,
                       strand=ann.strand, char_width=char_width)
        else:  # REPEATED_REGION
            draw_repeated_region(painter, 0, 0, self._w, self._h, color, ann.label)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            if self._on_click is not None:
                self._on_click(self.annotation, self.row_index)
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            if self._on_double_click is not None:
                self._on_double_click(self.annotation, self.row_index)
            event.accept()
        else:
            super().mouseDoubleClickEvent(event)

    def hoverEnterEvent(self, event) -> None:
        scene_views = self.scene().views() if self.scene() else []
        if scene_views:
            vp = scene_views[0].viewport()
            global_pos = vp.mapToGlobal(scene_views[0].mapFromScene(event.scenePos()))
            QToolTip.showText(global_pos, self.annotation.tooltip_text(), vp)
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event) -> None:
        QToolTip.hideText()
        super().hoverLeaveEvent(event)