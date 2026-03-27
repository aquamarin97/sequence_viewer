# features/annotation_layer/annotation_graphics_item.py
"""
Bireysel annotasyon QGraphicsItem'ı.

Her (annotation, row_index) çifti için ayrı bir örnek oluşturulur.
Böylece:
- Her item bağımsız tıklanabilir.
- row_index bilgisi item içinde taşınır → hangi dizi seçileceği net.
- İleride visibility toggle (workspace tree) trivial olur.
"""

from __future__ import annotations

from typing import Callable, Optional

from PyQt5.QtCore import Qt, QRectF
from PyQt5.QtGui import QPainter
from PyQt5.QtWidgets import QGraphicsItem, QStyleOptionGraphicsItem, QToolTip

from features.annotation_layer.annotation_painter import (
    draw_forward_primer, draw_reverse_primer, draw_probe, draw_region,
)
from model.annotation import Annotation, AnnotationType
from settings.theme import theme_manager


# Tıklama callback tipi: (annotation, row_index) → None
ClickCallback = Callable[[Annotation, int], None]


class AnnotationGraphicsItem(QGraphicsItem):
    """
    Sequence viewer sahnesinde tek bir annotasyon şeklini temsil eder.

    Parametreler
    ------------
    annotation : Annotation
    row_index  : int   — hangi dizi satırına ait olduğu
    ann_width  : float — annotation.length() * char_width (px)
    ann_height : float — lane yüksekliği (px)

    Callbacks
    ---------
    on_click       : (ann, row) → None
    on_double_click: (ann, row) → None
    """

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

        # Seçili görsel state
        self._selected: bool = False

        theme_manager.themeChanged.connect(self.update)

    # ------------------------------------------------------------------
    # Geometri güncelleme (zoom değişince workspace çağırır)
    # ------------------------------------------------------------------

    def update_size(self, ann_width: float, ann_height: float) -> None:
        if abs(self._w - ann_width) < 0.01 and abs(self._h - ann_height) < 0.01:
            return
        self.prepareGeometryChange()
        self._w = float(ann_width)
        self._h = float(ann_height)
        self.update()

    # ------------------------------------------------------------------
    # Seçim durumu
    # ------------------------------------------------------------------

    def set_selected_visual(self, selected: bool) -> None:
        if self._selected == selected:
            return
        self._selected = selected
        self.update()

    # ------------------------------------------------------------------
    # QGraphicsItem
    # ------------------------------------------------------------------

    def boundingRect(self) -> QRectF:
        return QRectF(0, 0, self._w, self._h)

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionGraphicsItem,
        widget=None,
    ) -> None:
        ann    = self.annotation
        color  = ann.resolved_color()

        # Seçiliyse hafif highlight kenarlık
        if self._selected:
            from PyQt5.QtGui import QPen, QColor
            from PyQt5.QtCore import Qt as _Qt
            painter.setPen(QPen(QColor(255, 255, 255), 1.5))
        else:
            from PyQt5.QtCore import Qt as _Qt
            painter.setPen(_Qt.NoPen)

        painter.setRenderHint(QPainter.Antialiasing, True)

        if ann.type == AnnotationType.FORWARD_PRIMER:
            draw_forward_primer(
                painter, 0, 0, self._w, self._h, color, ann.label
            )
        elif ann.type == AnnotationType.REVERSE_PRIMER:
            draw_reverse_primer(
                painter, 0, 0, self._w, self._h, color, ann.label
            )
        elif ann.type == AnnotationType.PROBE:
            draw_probe(
                painter, 0, 0, self._w, self._h, color, ann.label,
                strand=ann.strand,
            )
        else:  # REGION
            draw_region(
                painter, 0, 0, self._w, self._h, color, ann.label
            )

    # ------------------------------------------------------------------
    # Mouse
    # ------------------------------------------------------------------

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
            global_pos = vp.mapToGlobal(
                scene_views[0].mapFromScene(event.scenePos()) 
            )
            QToolTip.showText(global_pos, self.annotation.tooltip_text(), vp)
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event) -> None:
        QToolTip.hideText()
        super().hoverLeaveEvent(event)