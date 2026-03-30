# features/sequence_viewer/sequence_viewer_view.py
"""
MODIFIED: 
- drawForeground paints row_band_highlight between h_guide rows
- Annotation strip area supports selection drag (mousePressEvent forwards 
  to controller when in annot strip and ctrl not held)
"""
from __future__ import annotations
from typing import TYPE_CHECKING, List, Optional, Tuple, Any
from PyQt5.QtCore import Qt, QPointF, QRectF, QEasingCurve, QVariantAnimation
from PyQt5.QtGui import QPainter, QPen, QColor, QBrush
from PyQt5.QtWidgets import QGraphicsView, QGraphicsScene, QScrollBar
from graphics.sequence_item.sequence_item import SequenceGraphicsItem
from settings.theme import theme_manager

if TYPE_CHECKING:
    from widgets.row_layout import RowLayout

_GUIDE_COLOR = QColor(80, 130, 220, 160)
_GUIDE_WIDTH = 1

class SequenceViewerView(QGraphicsView):
    def __init__(self, parent=None, *, char_width=12.0, char_height=18.0):
        super().__init__(parent)
        self.scene = QGraphicsScene(self); self.setScene(self.scene)
        self.char_width = float(char_width)
        self.char_height = int(round(char_height))
        self._per_row_annot_h = 0
        self._row_layout = None
        self.trailing_padding_line_px = 80.0
        self.trailing_padding_text_px = 30.0
        self.max_sequence_length = 0
        self.sequence_items = []
        # Çoklu dikey guide (col index listesi)
        self._v_guide_cols: list = []
        self._h_guide_rows = frozenset()
        self._zoom_animation = QVariantAnimation(self)
        self._zoom_animation.setEasingCurve(QEasingCurve.OutCubic)
        self._zoom_animation.valueChanged.connect(self._on_zoom_value_changed)
        self._zoom_center_nt = None; self._zoom_view_width_px = None
        self.setRenderHint(QPainter.Antialiasing, False)
        self.setRenderHint(QPainter.TextAntialiasing, True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setDragMode(QGraphicsView.NoDrag)
        self.setMouseTracking(True)
        self.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        from PyQt5.QtWidgets import QFrame
        self.setFrameShape(QFrame.NoFrame)
        self._controller = None
        # I-beam cursor
        self.viewport().setCursor(Qt.IBeamCursor)
        theme_manager.themeChanged.connect(self._on_theme_changed)
        self._apply_scene_background()

    def _apply_scene_background(self):
        from PyQt5.QtGui import QBrush as _QBrush
        self.scene.setBackgroundBrush(_QBrush(theme_manager.current.seq_bg))

    def _on_theme_changed(self, _theme):
        self._apply_scene_background(); self.scene.invalidate(); self.viewport().update()

    def drawBackground(self, painter, rect):
        t = theme_manager.current
        layout = self._row_layout
        if layout is None or layout.row_count == 0:
            painter.fillRect(rect, t.seq_bg); return
        vis_top, vis_bottom = rect.top(), rect.bottom()
        painter.fillRect(rect, t.seq_bg)
        for i in range(layout.row_count):
            y_top = float(layout.y_offsets[i])
            y_bottom = y_top + float(layout.row_strides[i])
            if y_bottom < vis_top or y_top > vis_bottom: continue
            row_bg = t.row_bg_even if i % 2 == 0 else t.row_bg_odd
            painter.fillRect(QRectF(rect.left(), y_top, rect.width(), y_bottom - y_top), row_bg)

    def apply_row_layout(self, layout):
        self._row_layout = layout; self._per_row_annot_h = 0
        self._reposition_items(); self._update_scene_rect()

    @property
    def row_stride(self):
        if self._row_layout and self._row_layout.row_count > 0:
            return self._row_layout.row_strides[0]
        return self._per_row_annot_h + self.char_height

    def set_per_row_annot_height(self, h):
        if self._row_layout is not None: return
        if self._per_row_annot_h == h: return
        self._per_row_annot_h = h; self._reposition_items(); self._update_scene_rect()

    def _reposition_items(self):
        layout = self._row_layout
        if layout is not None:
            for i, item in enumerate(self.sequence_items):
                if i < layout.row_count: item.setPos(0, float(layout.seq_y_offsets[i]))
        else:
            stride = self._per_row_annot_h + self.char_height
            for i, item in enumerate(self.sequence_items):
                item.setPos(0, float(i * stride + self._per_row_annot_h))

    def set_v_guides(self, cols: list):
        """Dikey guide kolonlarını ayarla (boş liste = temizle)."""
        self._v_guide_cols = list(cols); self.viewport().update()
    def clear_v_guides(self):
        self._v_guide_cols = []; self.viewport().update()

    # Geriye dönük uyumluluk — eski tek-guide API'si
    def set_guide_cols(self, start_col, end_col):
        self._v_guide_cols = [start_col, end_col + 1]; self.viewport().update()
    def clear_guide_cols(self):
        self._v_guide_cols = []; self.viewport().update()

    def set_h_guides(self, row_indices):
        self._h_guide_rows = row_indices; self.viewport().update()
    def clear_h_guides(self):
        if self._h_guide_rows: self._h_guide_rows = frozenset(); self.viewport().update()

    def drawForeground(self, painter, rect):
        super().drawForeground(painter, rect)
        t = theme_manager.current

        # ---- Row band highlight (header satır seçimi) ----
        if self._h_guide_rows:
            layout = self._row_layout
            vbar = self.verticalScrollBar()
            v_off = float(vbar.value())
            vp_w = float(self.viewport().width())
            vp_h = float(self.viewport().height())

            painter.save()
            painter.resetTransform()

            # Bant arkaplanı — row_band_highlight rengi ile doldur
            band_color = QColor(t.row_band_highlight)
            for row in self._h_guide_rows:
                if layout is not None and row < layout.row_count:
                    top_scene = float(layout.y_offsets[row])
                    bottom_scene = top_scene + float(layout.row_strides[row])
                else:
                    stride = self._per_row_annot_h + self.char_height
                    top_scene = float(row * stride)
                    bottom_scene = top_scene + float(stride)
                top_vp = top_scene - v_off
                bottom_vp = bottom_scene - v_off
                # Clip to viewport
                t_vp = max(0.0, top_vp)
                b_vp = min(vp_h, bottom_vp)
                if b_vp > t_vp:
                    painter.fillRect(QRectF(0, t_vp, vp_w, b_vp - t_vp), QBrush(band_color))

            # Kılavuz çizgileri
            h_pen = QPen(_GUIDE_COLOR, _GUIDE_WIDTH, Qt.SolidLine)
            painter.setPen(h_pen)
            for row in self._h_guide_rows:
                if layout is not None and row < layout.row_count:
                    top_scene = float(layout.y_offsets[row])
                    bottom_scene = top_scene + float(layout.row_strides[row])
                else:
                    stride = self._per_row_annot_h + self.char_height
                    top_scene = float(row * stride)
                    bottom_scene = top_scene + float(stride)
                for vp_y in (top_scene - v_off, bottom_scene - v_off):
                    if -2 <= vp_y <= vp_h + 2:
                        painter.drawLine(QPointF(0, vp_y), QPointF(vp_w, vp_y))
            painter.restore()

        # ---- Dikey kılavuz çizgileri (boundary tıklama) ----
        if self._v_guide_cols:
            cw = self._effective_char_width()
            if cw > 0:
                hbar = self.horizontalScrollBar()
                offset = float(hbar.value())
                vp_w2 = float(self.viewport().width())

                # Çizgilerin tüm yüksekliği kaplaması için parent widget
                # hiyerarşisini kullanarak position ruler'ın altından başla.
                # viewport koordinatında: üst = position ruler altı.
                # Bunu sağlamak için parent zincirinde pos_ruler'ı buluyoruz;
                # bulamazsak viewport yüksekliğini kullanırız.
                parent_widget = self.parent()
                ruler_bottom_in_vp = 0.0  # default: viewport'un en üstü
                try:
                    from features.position_ruler.position_ruler_widget import SequencePositionRulerWidget
                    p = parent_widget
                    while p is not None:
                        for child in p.children():
                            if isinstance(child, SequencePositionRulerWidget):
                                # child'ın alt kenarını bu viewport'a map et
                                child_bottom_global = child.mapToGlobal(
                                    child.rect().bottomLeft())
                                vp_top_global = self.viewport().mapToGlobal(
                                    self.viewport().rect().topLeft())
                                ruler_bottom_in_vp = float(
                                    child_bottom_global.y() - vp_top_global.y())
                                raise StopIteration
                        p = p.parent()
                except StopIteration:
                    pass

                draw_top = min(ruler_bottom_in_vp, 0.0)  # viewport'un üstünden başla
                draw_bottom = float(self.viewport().height())

                painter.save(); painter.resetTransform()
                pen = QPen(_GUIDE_COLOR, _GUIDE_WIDTH, Qt.DashLine)
                pen.setDashPattern([4, 3]); painter.setPen(pen)
                for col in self._v_guide_cols:
                    vp_x = col * cw - offset
                    if -10 <= vp_x <= vp_w2 + 10:
                        painter.drawLine(QPointF(vp_x, draw_top),
                                         QPointF(vp_x, draw_bottom))
                painter.restore()

    def set_controller(self, controller): self._controller = controller

    def add_sequence_item(self, sequence_string):
        row_index = len(self.sequence_items)
        item = SequenceGraphicsItem(sequence=sequence_string, char_width=self.char_width, char_height=self.char_height, row_index=row_index)
        layout = self._row_layout
        if layout is not None and row_index < layout.row_count:
            y = float(layout.seq_y_offsets[row_index])
        else:
            y = float(row_index * (self._per_row_annot_h + self.char_height) + self._per_row_annot_h)
        item.setPos(0, y); self.scene.addItem(item)
        self.sequence_items.append(item); self._update_scene_rect()
        return item

    def clear_items(self):
        self.sequence_items.clear(); self.scene.clear()
        self.max_sequence_length = 0; self._row_layout = None
        self.scene.setSceneRect(0, 0, 0, 0); self.scene.invalidate()

    def current_char_width(self): return self._effective_char_width()

    def compute_min_char_width(self):
        if not self.sequence_items: return self.char_width
        max_len = self.max_sequence_length
        if max_len <= 0: return self.char_width
        vp_w = self.viewport().width()
        if vp_w <= 0: return self.char_width
        trailing = max(self.trailing_padding_line_px, self._current_trailing_padding())
        available = vp_w - trailing
        if available <= 0: return 0.000001
        return max(available / float(max_len), 0.000001)

    def apply_char_width(self, new_char_width, center_nt=None, view_width_px=None):
        if view_width_px is None: view_width_px = float(self.viewport().width())
        if abs(new_char_width - self.char_width) < 0.0001 and center_nt is None: return
        applied = float(new_char_width)
        for item in self.sequence_items: item.set_char_width(applied)
        if self.sequence_items: applied = float(self.sequence_items[0].char_width)
        self.char_width = applied; self._update_scene_rect()
        if center_nt is not None: self._recenter_horizontally(center_nt, view_width_px)
        self.scene.invalidate(); self.viewport().update()

    def start_zoom_animation(self, target_char_width, center_nt, view_width_px=None):
        if view_width_px is None: view_width_px = float(self.viewport().width())
        current = self._get_current_char_width()
        if abs(target_char_width - current) < 0.0001:
            self.apply_char_width(target_char_width, center_nt, view_width_px); return
        if self._zoom_animation.state() == QVariantAnimation.Running:
            self._zoom_view_width_px = view_width_px
            self._zoom_animation.setEndValue(target_char_width); return
        self._zoom_center_nt = center_nt; self._zoom_view_width_px = view_width_px
        self._zoom_animation.setDuration(180)
        self._zoom_animation.setStartValue(current)
        self._zoom_animation.setEndValue(target_char_width)
        self._zoom_animation.start()

    def zoom_to_nt_range(self, start_nt, end_nt):
        if not self.sequence_items: return
        a, b = float(start_nt), float(end_nt)
        if a == b: span_nt, center_nt = 1.0, a
        else: span_nt, center_nt = max(abs(b-a), 1.0), (min(a,b)+max(a,b))/2.0
        vp_w = float(self.viewport().width())
        if vp_w <= 0: return
        desired = vp_w / span_nt
        new_cw = max(self.compute_min_char_width(), min(desired, 90.0))
        if abs(new_cw - self.char_width) > 0.0001:
            self.char_width = new_cw
            for item in self.sequence_items: item.set_char_width(self.char_width)
            self._update_scene_rect()
        self._recenter_horizontally(center_nt, vp_w)
        self.scene.invalidate(); self.viewport().update()

    def clear_visual_selection(self):
        for item in self.sequence_items: item.clear_selection()
        self.scene.invalidate(); self.viewport().update()

    def set_visual_selection(self, row_start, row_end, col_start, col_end):
        for i, item in enumerate(self.sequence_items):
            if row_start <= i <= row_end and col_start >= 0 and col_end >= 0:
                item.set_selection(col_start, col_end)
            else: item.clear_selection()
        self.scene.invalidate(); self.viewport().update()

    def _update_scene_rect(self):
        if not self.sequence_items:
            self.scene.setSceneRect(0,0,0,0); self.max_sequence_length = 0; return
        max_len = max(len(item.sequence) for item in self.sequence_items)
        self.max_sequence_length = max_len
        trailing = self._current_trailing_padding()
        width = max_len * self.char_width + trailing
        layout = self._row_layout
        if layout is not None and layout.row_count > 0: height = float(layout.total_height)
        else:
            stride = self._per_row_annot_h + self.char_height
            height = float(len(self.sequence_items) * stride)
        self.scene.setSceneRect(0, 0, width, height); self.scene.invalidate()

    def _current_trailing_padding(self):
        if not self.sequence_items: return self.trailing_padding_text_px
        for item in self.sequence_items:
            if item.display_mode == SequenceGraphicsItem.LINE_MODE: return self.trailing_padding_line_px
        return self.trailing_padding_text_px

    def _effective_char_width(self):
        if self._zoom_animation.state() == QVariantAnimation.Running:
            v = self._zoom_animation.currentValue()
            if v is not None: return float(v)
        if self.sequence_items: return float(self.sequence_items[0].char_width)
        return float(self.char_width)

    def _get_current_char_width(self): return self._effective_char_width()

    def _recenter_horizontally(self, center_nt, view_width_px):
        if view_width_px <= 0: view_width_px = float(self.viewport().width())
        if view_width_px <= 0: return
        scene_w = float(self.scene.sceneRect().width())
        if scene_w <= 0: return
        if self.max_sequence_length > 0:
            center_nt = max(0.0, min(center_nt, float(self.max_sequence_length)))
        cw = self._effective_char_width()
        ideal_left = center_nt * cw - view_width_px / 2.0
        max_left = max(0.0, scene_w - view_width_px)
        ideal_left = max(0.0, min(ideal_left, max_left))
        hbar = self.horizontalScrollBar()
        if abs(float(hbar.value()) - ideal_left) >= 0.5: hbar.setValue(int(round(ideal_left)))

    def _on_zoom_value_changed(self, value):
        if self._zoom_center_nt is None or self._zoom_view_width_px is None: return
        try: self.apply_char_width(float(value), self._zoom_center_nt, float(self._zoom_view_width_px))
        except: pass

    def scene_pos_to_row_col(self, scene_pos):
        layout = self._row_layout
        if layout is not None and layout.row_count > 0:
            raw_row = layout.row_at_y(scene_pos.y())
        else:
            stride = self._per_row_annot_h + self.char_height
            raw_row = int(scene_pos.y() // stride) if stride > 0 else 0
        cw = self._get_current_char_width()
        if cw <= 0: cw = max(self.char_width, 0.000001)
        col = int(scene_pos.x() // cw)
        return raw_row, col

    # --- MODIFIED: annotation strip area supports selection drag ---
    def wheelEvent(self, event):
        if self._controller:
            handled = getattr(self._controller, "handle_wheel_event", None)
            if callable(handled) and handled(event): return
        super().wheelEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            layout = self._row_layout
            scene_pos = self.mapToScene(event.pos())
            in_annot = False

            if layout is not None and layout.row_count > 0:
                row = layout.row_at_y(scene_pos.y())
                if layout.is_in_annot_strip(scene_pos.y(), row):
                    in_annot = True
            elif self._per_row_annot_h > 0:
                stride = self._per_row_annot_h + self.char_height
                y_in_row = scene_pos.y() % stride if stride > 0 else 0
                if 0 <= y_in_row < self._per_row_annot_h:
                    in_annot = True

            if in_annot:
                # First let scene items (AnnotationGraphicsItem) handle it
                items_at = self.scene.items(scene_pos)
                from features.annotation_layer.annotation_graphics_item import AnnotationGraphicsItem
                ann_item_hit = any(isinstance(it, AnnotationGraphicsItem) for it in items_at)
                if ann_item_hit:
                    super().mousePressEvent(event)
                    return
                # No annotation item hit — start sequence selection from annot strip
                if self._controller:
                    handled = getattr(self._controller, "handle_mouse_press", None)
                    if callable(handled) and handled(event): return
                super().mousePressEvent(event)
                return

        if event.button() == Qt.LeftButton:
            if self._controller:
                handled = getattr(self._controller, "handle_mouse_press", None)
                if callable(handled) and handled(event): return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._controller:
            handled = getattr(self._controller, "handle_mouse_move", None)
            if callable(handled) and handled(event): return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._controller:
            handled = getattr(self._controller, "handle_mouse_release", None)
            if callable(handled) and handled(event): return
        super().mouseReleaseEvent(event)