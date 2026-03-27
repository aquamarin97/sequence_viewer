# features/sequence_viewer/sequence_viewer_view.py

from __future__ import annotations

from typing import List, Optional, Tuple, Any

from PyQt5.QtCore import Qt, QPointF, QRectF, QEasingCurve, QVariantAnimation
from PyQt5.QtGui import QPainter, QPen, QColor
from PyQt5.QtWidgets import QGraphicsView, QGraphicsScene, QScrollBar

from graphics.sequence_item.sequence_item import SequenceGraphicsItem
from settings.theme import theme_manager

# Per-row annotation sabitleri — per_row_annotation_item ile senkron
from features.annotation_layer.per_row_annotation_item import (
    LANE_HEIGHT, LANE_PADDING,
)

# Kılavuz çizgisi görünümü
_GUIDE_COLOR = QColor(80, 130, 220, 160)   # yarı saydam mavi
_GUIDE_WIDTH = 1


class SequenceViewerView(QGraphicsView):
    """
    Sekans satırlarını çizen view.

    Yeni özellikler (v2)
    --------------------
    * Per-row annotation alanı: her satırın üstünde `_per_row_annot_h` px
      boşluk bırakılır. Satır Y = row_index * row_stride.
    * Kılavuz çizgileri: annotasyon tıklandığında start/end pozisyonlarında
      dikey çizgi çizilir (drawForeground).
    * _per_row_annot_h dışarıdan set edilir (workspace günceller).
    """

    def __init__(
        self,
        parent=None,
        *,
        char_width: float = 12.0,
        char_height: float = 18.0,
    ) -> None:
        super().__init__(parent)

        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)

        self.char_width:   float = float(char_width)
        self.char_height:  int   = int(round(char_height))

        # Per-row annotation yüksekliği (dışarıdan ayarlanır)
        self._per_row_annot_h: int = 0

        self.trailing_padding_line_px: float = 80.0
        self.trailing_padding_text_px: float = 30.0

        self.max_sequence_length: int = 0
        self.sequence_items: List[SequenceGraphicsItem] = []

        # Kılavuz çizgisi state'i: (start_col, end_col) veya None
        self._guide_cols: Optional[Tuple[int, int]] = None

        # Zoom animasyonu
        self._zoom_animation = QVariantAnimation(self)
        self._zoom_animation.setEasingCurve(QEasingCurve.OutCubic)
        self._zoom_animation.valueChanged.connect(self._on_zoom_value_changed)

        self._zoom_center_nt:    Optional[float] = None
        self._zoom_view_width_px: Optional[float] = None

        self.setRenderHint(QPainter.Antialiasing, False)
        self.setRenderHint(QPainter.TextAntialiasing, True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setDragMode(QGraphicsView.NoDrag)
        self.setMouseTracking(True)
        self.setAlignment(Qt.AlignLeft | Qt.AlignTop)

        self._controller: Optional[Any] = None

    # ------------------------------------------------------------------
    # Per-row annotation yüksekliği
    # ------------------------------------------------------------------

    @property
    def row_stride(self) -> int:
        """Bir satırın toplam Y alanı: annotation strip + char_height."""
        return self._per_row_annot_h + self.char_height

    def set_per_row_annot_height(self, h: int) -> None:
        """
        Workspace / annotation store değişince çağrılır.
        Tüm item'ların Y pozisyonlarını günceller.
        """
        if self._per_row_annot_h == h:
            return
        self._per_row_annot_h = h
        self._reposition_items()
        self._update_scene_rect()

    def _reposition_items(self) -> None:
        """Tüm sequence item'larını yeni row_stride ile yeniden konumlandır."""
        stride = self.row_stride
        for i, item in enumerate(self.sequence_items):
            item.setPos(0, i * stride + self._per_row_annot_h)

    # ------------------------------------------------------------------
    # Kılavuz çizgileri
    # ------------------------------------------------------------------

    def set_guide_cols(self, start_col: int, end_col: int) -> None:
        """Annotasyon tıklandığında workspace çağırır."""
        self._guide_cols = (start_col, end_col)
        self.viewport().update()

    def clear_guide_cols(self) -> None:
        self._guide_cols = None
        self.viewport().update()
        
    def drawForeground(self, painter: QPainter, rect: QRectF) -> None:
        super().drawForeground(painter, rect)
 
        if self._guide_cols is None:
            return
 
        start_col, end_col = self._guide_cols
        cw = self._effective_char_width()
        if cw <= 0:
            return
 
        hbar   = self.horizontalScrollBar()
        vp_h   = float(self.viewport().height())
        vp_w   = float(self.viewport().width())
        offset = float(hbar.value())
 
        # FIX: merkez yerine kenar pozisyonları
        # start_col'un SOL kenarı   → annotasyonun başlangıcını soldan çerçevele
        # end_col'un  SAĞ kenarı    → annotasyonun sonunu sağdan çerçevele
        start_scene_x = start_col * cw               # sol kenar
        end_scene_x   = (end_col + 1) * cw           # sağ kenar
 
        start_vp_x = start_scene_x - offset
        end_vp_x   = end_scene_x   - offset
 
        painter.save()
        painter.resetTransform()
 
        pen = QPen(_GUIDE_COLOR, _GUIDE_WIDTH, Qt.DashLine)
        pen.setDashPattern([4, 3])
        painter.setPen(pen)
 
        for vp_x in (start_vp_x, end_vp_x):
            if -10 <= vp_x <= vp_w + 10:
                painter.drawLine(
                    QPointF(vp_x, 0),
                    QPointF(vp_x, vp_h),
                )
 
        painter.restore()
    # ------------------------------------------------------------------
    # Controller
    # ------------------------------------------------------------------

    def set_controller(self, controller: Any) -> None:
        self._controller = controller

    # ------------------------------------------------------------------
    # Public API: item yönetimi
    # ------------------------------------------------------------------

    def add_sequence_item(self, sequence_string: str) -> SequenceGraphicsItem:
        row_index = len(self.sequence_items)
        item = SequenceGraphicsItem(
            sequence=sequence_string,
            char_width=self.char_width,
            char_height=self.char_height,
        )
        # Y = annotation strip + sequence row
        item.setPos(0, row_index * self.row_stride + self._per_row_annot_h)
        self.scene.addItem(item)
        self.sequence_items.append(item)
        self._update_scene_rect()
        return item

    def clear_items(self) -> None:
        self.sequence_items.clear()
        self.scene.clear()
        self.max_sequence_length = 0
        self.scene.setSceneRect(0, 0, 0, 0)
        self.scene.invalidate()

    # ------------------------------------------------------------------
    # Geometri / zoom
    # ------------------------------------------------------------------

    def current_char_width(self) -> float:
        return self._effective_char_width()

    def compute_min_char_width(self) -> float:
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

    def apply_char_width(
        self,
        new_char_width: float,
        center_nt: Optional[float] = None,
        view_width_px: Optional[float] = None,
    ) -> None:
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

    def start_zoom_animation(
        self,
        target_char_width: float,
        center_nt: float,
        view_width_px: Optional[float] = None,
    ) -> None:
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
        self._zoom_center_nt     = center_nt
        self._zoom_view_width_px = view_width_px
        self._zoom_animation.setDuration(180)
        self._zoom_animation.setStartValue(current)
        self._zoom_animation.setEndValue(target_char_width)
        self._zoom_animation.start()

    def zoom_to_nt_range(self, start_nt: float, end_nt: float) -> None:
        if not self.sequence_items:
            return
        a, b = float(start_nt), float(end_nt)
        if a == b:
            span_nt, center_nt = 1.0, a
        else:
            span_nt    = max(abs(b - a), 1.0)
            center_nt  = (min(a, b) + max(a, b)) / 2.0
        vp_w = float(self.viewport().width())
        if vp_w <= 0:
            return
        desired = vp_w / span_nt
        new_cw  = max(self.compute_min_char_width(), min(desired, 90.0))
        if abs(new_cw - self.char_width) > 0.0001:
            self.char_width = new_cw
            for item in self.sequence_items:
                item.set_char_width(self.char_width)
            self._update_scene_rect()
        self._recenter_horizontally(center_nt, vp_w)
        self.scene.invalidate()
        self.viewport().update()

    # ------------------------------------------------------------------
    # Seçim
    # ------------------------------------------------------------------

    def clear_visual_selection(self) -> None:
        for item in self.sequence_items:
            item.clear_selection()
        self.scene.invalidate()
        self.viewport().update()

    def set_visual_selection(
        self, row_start: int, row_end: int, col_start: int, col_end: int,
    ) -> None:
        for i, item in enumerate(self.sequence_items):
            if row_start <= i <= row_end and col_start >= 0 and col_end >= 0:
                item.set_selection(col_start, col_end)
            else:
                item.clear_selection()
        self.scene.invalidate()
        self.viewport().update()

    # ------------------------------------------------------------------
    # Scene rect
    # ------------------------------------------------------------------

    def _update_scene_rect(self) -> None:
        if not self.sequence_items:
            self.scene.setSceneRect(0, 0, 0, 0)
            self.max_sequence_length = 0
            return
        max_len = max(len(item.sequence) for item in self.sequence_items)
        self.max_sequence_length = max_len
        trailing = self._current_trailing_padding()
        width    = max_len * self.char_width + trailing
        height   = len(self.sequence_items) * self.row_stride
        self.scene.setSceneRect(0, 0, width, height)
        self.scene.invalidate()

    def _current_trailing_padding(self) -> float:
        if not self.sequence_items:
            return self.trailing_padding_text_px
        for item in self.sequence_items:
            if item.display_mode == SequenceGraphicsItem.LINE_MODE:
                return self.trailing_padding_line_px
        return self.trailing_padding_text_px

    # ------------------------------------------------------------------
    # Zoom yardımcıları
    # ------------------------------------------------------------------

    def _effective_char_width(self) -> float:
        if self._zoom_animation.state() == QVariantAnimation.Running:
            v = self._zoom_animation.currentValue()
            if v is not None:
                return float(v)
        if self.sequence_items:
            return float(self.sequence_items[0].char_width)
        return float(self.char_width)

    def _get_current_char_width(self) -> float:
        return self._effective_char_width()

    def _recenter_horizontally(self, center_nt: float, view_width_px: float) -> None:
        if view_width_px <= 0:
            view_width_px = float(self.viewport().width())
            if view_width_px <= 0:
                return
        scene_w = float(self.scene.sceneRect().width())
        if scene_w <= 0:
            return
        if self.max_sequence_length > 0:
            center_nt = max(0.0, min(center_nt, float(self.max_sequence_length)))
        cw        = self._effective_char_width()
        ideal_left = center_nt * cw - view_width_px / 2.0
        max_left   = max(0.0, scene_w - view_width_px)
        ideal_left = max(0.0, min(ideal_left, max_left))
        hbar: QScrollBar = self.horizontalScrollBar()
        if abs(float(hbar.value()) - ideal_left) >= 0.5:
            hbar.setValue(int(round(ideal_left)))

    def _on_zoom_value_changed(self, value) -> None:
        if self._zoom_center_nt is None or self._zoom_view_width_px is None:
            return
        try:
            self.apply_char_width(
                float(value),
                self._zoom_center_nt,
                float(self._zoom_view_width_px),
            )
        except (TypeError, ValueError):
            pass

    # ------------------------------------------------------------------
    # Koordinat dönüşümü
    # ------------------------------------------------------------------

    def scene_pos_to_row_col(self, scene_pos: QPointF) -> Tuple[int, int]:
        stride = self.row_stride
        if stride <= 0:
            return 0, 0
        raw_row = int(scene_pos.y() // stride)
        cw = self._get_current_char_width()
        if cw <= 0:
            cw = max(self.char_width, 0.000001)
        col = int(scene_pos.x() // cw)
        return raw_row, col

    # ------------------------------------------------------------------
    # Event yönlendirme
    # ------------------------------------------------------------------

    def wheelEvent(self, event) -> None:
        if self._controller is not None:
            handled = getattr(self._controller, "handle_wheel_event", None)
            if callable(handled) and handled(event):
                return
        super().wheelEvent(event)

    def mousePressEvent(self, event) -> None:
        if self._controller is not None:
            handled = getattr(self._controller, "handle_mouse_press", None)
            if callable(handled) and handled(event):
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._controller is not None:
            handled = getattr(self._controller, "handle_mouse_move", None)
            if callable(handled) and handled(event):
                return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if self._controller is not None:
            handled = getattr(self._controller, "handle_mouse_release", None)
            if callable(handled) and handled(event):
                return
        super().mouseReleaseEvent(event)