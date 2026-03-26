# features/annotation_layer/annotation_layer_widget.py
"""
Sabit annotasyon şeridi widget'ı.

Position ruler'ın altında, consensus row'un üstünde yer alır.
Dikey scroll etkilemez. Yatay olarak SequenceViewer ile tam senkron.

Lane sayısına göre yüksekliği dinamik olarak güncellenir.
Annotasyon yokken minimum yükseklikte görünür (boş şerit).

Kullanıcı bir annotasyona tıklarsa annotationClicked(Annotation) sinyali
yayınlanır — workspace bunu tooltip / panel'e yönlendirir.
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
    draw_forward_primer, draw_reverse_primer, draw_probe, draw_region,
)
from model.annotation import Annotation, AnnotationType
from model.annotation_store import AnnotationStore
from settings.theme import theme_manager


_LANE_HEIGHT  = 20    # px — tek lane yüksekliği
_LANE_PADDING =  3    # px — lane'ler arası boşluk
_MIN_HEIGHT   = 24    # px — annotasyon yokken yükseklik


class AnnotationLayerWidget(QWidget):
    """Sabit annotasyon şeridi."""

    annotationClicked = pyqtSignal(object)   # Annotation

    def __init__(
        self,
        store: AnnotationStore,
        sequence_viewer,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)

        self._store          = store
        self._sequence_viewer = sequence_viewer

        # Cache: lane ataması ve annotasyon listesi
        self._lane_assignment: Dict[str, int] = {}
        self._annotations:     List[Annotation] = []

        # Hit test için: {annotation_id: viewport_rect}
        self._hit_rects: List[Tuple[QRectF, Annotation]] = []

        # Mouse tracking (hover tooltip)
        self.setMouseTracking(True)

        # Başlangıç yüksekliği
        self._update_height()

        # Store sinyalleri → yeniden hesapla
        self._store.annotationAdded.connect(self._on_store_changed)
        self._store.annotationRemoved.connect(self._on_store_changed)
        self._store.annotationUpdated.connect(self._on_store_changed)
        self._store.storeReset.connect(self._on_store_changed)

        # Scroll / zoom senkronizasyonu
        hbar: QScrollBar = self._sequence_viewer.horizontalScrollBar()
        hbar.valueChanged.connect(self.update)
        hbar.rangeChanged.connect(self.update)

        anim = getattr(self._sequence_viewer, "_zoom_animation", None)
        if anim is not None:
            anim.valueChanged.connect(self.update)

        # Tema
        theme_manager.themeChanged.connect(self.update)

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _update_height(self) -> None:
        n = lane_count(self._lane_assignment)
        h = max(_MIN_HEIGHT, n * (_LANE_HEIGHT + _LANE_PADDING) + _LANE_PADDING)
        self.setFixedHeight(h)

    def _recompute_layout(self) -> None:
        self._annotations    = self._store.all()
        self._lane_assignment = assign_lanes(self._annotations)
        self._update_height()
        self.update()

    # ------------------------------------------------------------------
    # Slot'lar
    # ------------------------------------------------------------------

    def _on_store_changed(self, *_args) -> None:
        self._recompute_layout()

    # ------------------------------------------------------------------
    # Geometri yardımcıları
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
        """Annotasyonun viewport'taki dikdörtgenini hesaplar."""
        x = ann.start * cw - view_left
        w = ann.length() * cw
        y = _LANE_PADDING + lane * (_LANE_HEIGHT + _LANE_PADDING)
        h = _LANE_HEIGHT

        # Tamamen görünür alanın dışındaysa None
        widget_w = float(self.width())
        if x + w < 0 or x > widget_w:
            return None

        # Kırp — soldan çıkıyorsa
        if x < 0:
            w += x
            x  = 0.0
        # Sağdan çıkıyorsa
        if x + w > widget_w:
            w = widget_w - x

        if w <= 0:
            return None

        return QRectF(x, y, w, h)

    # ------------------------------------------------------------------
    # paintEvent
    # ------------------------------------------------------------------

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.TextAntialiasing, True)

        t      = theme_manager.current
        rect   = self.rect()
        width  = float(rect.width())
        height = float(rect.height())

        # Arkaplan
        painter.fillRect(rect, QBrush(t.row_bg_even))

        # Alt çizgi
        painter.setPen(QPen(t.border_normal))
        painter.drawLine(0, rect.bottom() - 1, rect.right(), rect.bottom() - 1)

        if not self._annotations:
            # Boş — hafif "Annotations" hint metni
            painter.setPen(QPen(QColor(t.text_primary).lighter(150)))
            painter.drawText(rect.adjusted(6, 0, 0, 0),
                             Qt.AlignVCenter | Qt.AlignLeft, "Annotations")
            painter.end()
            return

        cw        = self._get_char_width()
        view_left = self._get_view_left()

        self._hit_rects.clear()

        _DRAW_FN = {
            AnnotationType.FORWARD_PRIMER: draw_forward_primer,
            AnnotationType.REVERSE_PRIMER: draw_reverse_primer,
            AnnotationType.PROBE:          draw_probe,
            AnnotationType.REGION:         draw_region,
        }

        for ann in self._annotations:
            lane = self._lane_assignment.get(ann.id, 0)
            vp   = self._annotation_viewport_rect(ann, lane, cw, view_left)
            if vp is None:
                continue

            draw_fn = _DRAW_FN.get(ann.type, draw_probe)

            painter.save()
            draw_fn(
                painter,
                vp.x(), vp.y(), vp.width(), vp.height(),
                ann.resolved_color(), ann.label,
            )
            painter.restore()

            # Hit test kaydı (tam genişlik — kırpılmamış)
            self._hit_rects.append((vp, ann))

        painter.end()

    # ------------------------------------------------------------------
    # Mouse
    # ------------------------------------------------------------------

    def _annotation_at(self, pos: QPoint) -> Optional[Annotation]:
        """Verilen viewport pozisyonundaki annotasyonu döner."""
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

    def mouseMoveEvent(self, event) -> None:
        ann = self._annotation_at(event.pos())
        if ann is not None:
            QToolTip.showText(
                event.globalPos(),
                ann.tooltip_text(),
                self,
            )
        else:
            QToolTip.hideText()
        super().mouseMoveEvent(event)