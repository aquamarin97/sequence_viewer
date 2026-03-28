# features/sequence_viewer/sequence_viewer_view.py

from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional, Tuple, Any

from PyQt5.QtCore import Qt, QPointF, QRectF, QEasingCurve, QVariantAnimation
from PyQt5.QtGui import QPainter, QPen, QColor
from PyQt5.QtWidgets import QGraphicsView, QGraphicsScene, QScrollBar

from graphics.sequence_item.sequence_item import SequenceGraphicsItem
from settings.theme import theme_manager

if TYPE_CHECKING:
    from widgets.row_layout import RowLayout

_GUIDE_COLOR = QColor(80, 130, 220, 160)
_GUIDE_WIDTH = 1


class SequenceViewerView(QGraphicsView):
    """
    Sekans satırlarını çizen view.

    Adım 2 değişikliği — variable stride
    --------------------------------------
    apply_row_layout(layout)  — workspace her annotation değişiminde çağırır.
    set_per_row_annot_height(h) — geriye dönük shim, tüm satırlara aynı yükseklik.
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

        self.char_width:  float = float(char_width)
        self.char_height: int   = int(round(char_height))

        self._per_row_annot_h: int = 0          # uniform shim
        self._row_layout: Optional["RowLayout"] = None   # per-row layout

        self.trailing_padding_line_px: float = 80.0
        self.trailing_padding_text_px: float = 30.0

        self.max_sequence_length: int = 0
        self.sequence_items: List[SequenceGraphicsItem] = []

        self._guide_cols: Optional[Tuple[int, int]] = None
        # Yatay kılavuz çizgileri: seçili satır indeksleri (frozenset)
        self._h_guide_rows: frozenset = frozenset()

        self._zoom_animation = QVariantAnimation(self)
        self._zoom_animation.setEasingCurve(QEasingCurve.OutCubic)
        self._zoom_animation.valueChanged.connect(self._on_zoom_value_changed)

        self._zoom_center_nt:     Optional[float] = None
        self._zoom_view_width_px: Optional[float] = None

        self.setRenderHint(QPainter.Antialiasing, False)
        self.setRenderHint(QPainter.TextAntialiasing, True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setDragMode(QGraphicsView.NoDrag)
        self.setMouseTracking(True)
        self.setAlignment(Qt.AlignLeft | Qt.AlignTop)

        self._controller: Optional[Any] = None

        # Tema değişince sahne arka planını ve viewport'u güncelle
        theme_manager.themeChanged.connect(self._on_theme_changed)
        self._apply_scene_background()

    # ------------------------------------------------------------------
    # Tema yönetimi
    # ------------------------------------------------------------------

    def _apply_scene_background(self) -> None:
        """Sahne arka planını mevcut temaya göre ayarla."""
        from PyQt5.QtGui import QBrush as _QBrush
        t = theme_manager.current
        self.scene.setBackgroundBrush(_QBrush(t.seq_bg))

    def _on_theme_changed(self, _theme) -> None:
        self._apply_scene_background()
        self.scene.invalidate()
        self.viewport().update()

    def drawBackground(self, painter, rect) -> None:
        """
        Sahne arka planı — zebra şeritleri.
        SequenceGraphicsItem'lar kendi seq alanını çizer;
        bu metod annotation şeritleri ve satırlar arası boşlukları kapsar.
        """
        t      = theme_manager.current
        layout = self._row_layout

        # Layout yoksa (dizi yok / henüz hesaplanmadı) düz arka plan
        if layout is None or layout.row_count == 0:
            painter.fillRect(rect, t.seq_bg)
            return

        # Görünür rect ile kesişen satırları bul
        vis_top    = rect.top()
        vis_bottom = rect.bottom()

        # Önce tüm alanı temel renkle doldur (boşluklar için)
        painter.fillRect(rect, t.seq_bg)

        # Her satır bloğunu (above_ann + seq + below_ann) zebra renkle boyat
        for i in range(layout.row_count):
            y_top    = float(layout.y_offsets[i])
            y_bottom = y_top + float(layout.row_strides[i])

            if y_bottom < vis_top or y_top > vis_bottom:
                continue   # görünür alanda değil

            row_bg = t.row_bg_even if i % 2 == 0 else t.row_bg_odd
            from PyQt5.QtCore import QRectF as _R
            painter.fillRect(
                _R(rect.left(), y_top, rect.width(), y_bottom - y_top),
                row_bg,
            )

    # ------------------------------------------------------------------
    # Per-row layout — yeni API
    # ------------------------------------------------------------------

    def apply_row_layout(self, layout: "RowLayout") -> None:
        """Per-row değişken yükseklik uygular."""
        self._row_layout       = layout
        self._per_row_annot_h  = 0
        self._reposition_items()
        self._update_scene_rect()

    # ------------------------------------------------------------------
    # Per-row layout — geriye dönük shim
    # ------------------------------------------------------------------

    @property
    def row_stride(self) -> int:
        if self._row_layout and self._row_layout.row_count > 0:
            return self._row_layout.row_strides[0]
        return self._per_row_annot_h + self.char_height

    def set_per_row_annot_height(self, h: int) -> None:
        if self._row_layout is not None:
            return
        if self._per_row_annot_h == h:
            return
        self._per_row_annot_h = h
        self._reposition_items()
        self._update_scene_rect()

    def _reposition_items(self) -> None:
        layout = self._row_layout
        if layout is not None:
            for i, item in enumerate(self.sequence_items):
                if i < layout.row_count:
                    item.setPos(0, float(layout.seq_y_offsets[i]))
        else:
            stride = self._per_row_annot_h + self.char_height
            for i, item in enumerate(self.sequence_items):
                item.setPos(0, float(i * stride + self._per_row_annot_h))

    # ------------------------------------------------------------------
    # Kılavuz çizgileri
    # ------------------------------------------------------------------

    def set_guide_cols(self, start_col: int, end_col: int) -> None:
        self._guide_cols = (start_col, end_col)
        self.viewport().update()

    def clear_guide_cols(self) -> None:
        self._guide_cols = None
        self.viewport().update()

    # ------------------------------------------------------------------
    # Yatay kılavuz çizgileri (satır seçimi)
    # ------------------------------------------------------------------

    def set_h_guides(self, row_indices: frozenset) -> None:
        """Seçili satır(lar)ın üst ve alt kenarına yatay kılavuz çiz."""
        self._h_guide_rows = row_indices
        self.viewport().update()

    def clear_h_guides(self) -> None:
        if self._h_guide_rows:
            self._h_guide_rows = frozenset()
            self.viewport().update()

    def drawForeground(self, painter: QPainter, rect: QRectF) -> None:
        super().drawForeground(painter, rect)

        # ---- Dikey kılavuz çizgileri (annotation seçimi) ----
        if self._guide_cols is not None:
            start_col, end_col = self._guide_cols
            cw = self._effective_char_width()
            if cw > 0:
                hbar   = self.horizontalScrollBar()
                vp_h   = float(self.viewport().height())
                vp_w   = float(self.viewport().width())
                offset = float(hbar.value())
                start_vp_x = start_col * cw - offset
                end_vp_x   = (end_col + 1) * cw - offset
                painter.save()
                painter.resetTransform()
                pen = QPen(_GUIDE_COLOR, _GUIDE_WIDTH, Qt.DashLine)
                pen.setDashPattern([4, 3])
                painter.setPen(pen)
                for vp_x in (start_vp_x, end_vp_x):
                    if -10 <= vp_x <= vp_w + 10:
                        painter.drawLine(QPointF(vp_x, 0), QPointF(vp_x, vp_h))
                painter.restore()

        # ---- Yatay kılavuz çizgileri (header satır seçimi) ----
        # guide_cols durumundan bağımsız — her zaman kontrol edilir.
        if self._h_guide_rows:
            layout = self._row_layout
            vbar   = self.verticalScrollBar()
            v_off  = float(vbar.value())
            vp_w2  = float(self.viewport().width())

            painter.save()
            painter.resetTransform()

            h_pen = QPen(_GUIDE_COLOR, _GUIDE_WIDTH, Qt.SolidLine)
            painter.setPen(h_pen)

            for row in self._h_guide_rows:
                if layout is not None and row < layout.row_count:
                    top_scene    = float(layout.y_offsets[row])
                    bottom_scene = top_scene + float(layout.row_strides[row])
                else:
                    stride       = self._per_row_annot_h + self.char_height
                    top_scene    = float(row * stride)
                    bottom_scene = top_scene + float(stride)

                top_vp    = top_scene    - v_off
                bottom_vp = bottom_scene - v_off

                for vp_y in (top_vp, bottom_vp):
                    if -2 <= vp_y <= float(self.viewport().height()) + 2:
                        painter.drawLine(
                            QPointF(0, vp_y),
                            QPointF(vp_w2, vp_y),
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
            row_index=row_index,
        )
        layout = self._row_layout
        if layout is not None and row_index < layout.row_count:
            y = float(layout.seq_y_offsets[row_index])
        else:
            y = float(row_index * (self._per_row_annot_h + self.char_height)
                      + self._per_row_annot_h)
        item.setPos(0, y)
        self.scene.addItem(item)
        self.sequence_items.append(item)
        self._update_scene_rect()
        return item

    def clear_items(self) -> None:
        self.sequence_items.clear()
        self.scene.clear()
        self.max_sequence_length = 0
        self._row_layout         = None
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
        trailing  = max(self.trailing_padding_line_px, self._current_trailing_padding())
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
        self._zoom_center_nt      = center_nt
        self._zoom_view_width_px  = view_width_px
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
            span_nt   = max(abs(b - a), 1.0)
            center_nt = (min(a, b) + max(a, b)) / 2.0
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
        max_len  = max(len(item.sequence) for item in self.sequence_items)
        self.max_sequence_length = max_len
        trailing = self._current_trailing_padding()
        width    = max_len * self.char_width + trailing

        layout = self._row_layout
        if layout is not None and layout.row_count > 0:
            height = float(layout.total_height)
        else:
            stride = self._per_row_annot_h + self.char_height
            height = float(len(self.sequence_items) * stride)

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
        cw         = self._effective_char_width()
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
    # Koordinat dönüşümü — variable stride destekli
    # ------------------------------------------------------------------

    def scene_pos_to_row_col(self, scene_pos: QPointF) -> Tuple[int, int]:
        layout = self._row_layout
        if layout is not None and layout.row_count > 0:
            raw_row = layout.row_at_y(scene_pos.y())
        else:
            stride  = self._per_row_annot_h + self.char_height
            raw_row = int(scene_pos.y() // stride) if stride > 0 else 0

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
        """
        Annotation şerit alanına yapılan sol tıklamaları
        sahne item'larına (AnnotationGraphicsItem) ilet.
        Variable stride destekli.
        """
        if event.button() == Qt.LeftButton:
            layout = self._row_layout
            if layout is not None and layout.row_count > 0:
                scene_pos = self.mapToScene(event.pos())
                row       = layout.row_at_y(scene_pos.y())
                if layout.is_in_annot_strip(scene_pos.y(), row):
                    super().mousePressEvent(event)
                    return
            elif self._per_row_annot_h > 0:
                scene_pos = self.mapToScene(event.pos())
                stride    = self._per_row_annot_h + self.char_height
                y_in_row  = scene_pos.y() % stride if stride > 0 else 0
                if 0 <= y_in_row < self._per_row_annot_h:
                    super().mousePressEvent(event)
                    return

        # Sequence alanına tıklama: yalnızca dikey kılavuzu temizle.
        # Yatay kılavuzlar (h_guides) header seçimiyle yönetilir,
        # burada dokunulmaz.
        if event.button() == Qt.LeftButton:
            if self._guide_cols is not None:
                self._guide_cols = None
                self.viewport().update()

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