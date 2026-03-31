from typing import Optional, Callable, List
from math import pow
from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtWidgets import QScrollBar
from .sequence_viewer_model import SequenceViewerModel
from .sequence_viewer_view import SequenceViewerView

# Kaç piksel sürüklenince drag-select başlar
_DRAG_THRESHOLD_PX = 4


class SequenceViewerController:
    def __init__(self, model, view, *, on_selection_changed=None):
        self._model = model; self._view = view
        self._is_selecting = False
        # drag-threshold takibi
        self._press_pos: Optional[QPoint] = None
        self._press_scene_col: Optional[int] = None
        self._press_scene_row: Optional[int] = None
        self._drag_started = False
        self._wheel_zoom_streak_dir = None; self._wheel_zoom_streak_len = 0
        self._wheel_zoom_base_factor = 1.22; self._wheel_zoom_accel_factor = 1.06
        self._on_selection_changed = on_selection_changed
        # Çoklu dikey guide: her eleman bir col index (NA'nın solundaki sınır)
        self._v_guide_cols: List[int] = []

    # ------------------------------------------------------------------
    # Yardımcı: viewport px → sahne kolonu (NA sınırı yuvarlama)
    # ------------------------------------------------------------------
    def _boundary_col_at(self, scene_x: float) -> int:
        """
        scene_x pikselinin en yakın NA sınırını (kolon solundan) döndürür.
        Her NA, kendi genişliğinin yarısına kadar sol sınıra, yarısından
        itibaren sağ sınıra (= bir sonraki NA'nın sol sınırı) yönlendirir.
        """
        cw = self._view._effective_char_width()
        if cw <= 0: return 0
        return int(round(scene_x / cw))

    def _is_boundary_click(self, viewport_pos) -> bool:
        """Tıklama konumunda dizi varsa True döner (boş alan değil)."""
        return bool(self._view.sequence_items)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def add_sequence(self, sequence_string):
        self._model.add_sequence(sequence_string)
        self._view.add_sequence_item(sequence_string)

    def clear(self):
        self._model.clear_sequences(); self._view.clear_items()
        self._is_selecting = False; self._drag_started = False
        self._press_pos = None
        self._v_guide_cols.clear()
        self._view.set_v_guides(self._v_guide_cols)
        self._wheel_zoom_streak_dir = None; self._wheel_zoom_streak_len = 0
        self._notify_selection_changed()

    # ------------------------------------------------------------------
    # Mouse events
    # ------------------------------------------------------------------
    def handle_mouse_press(self, event):
        if event.button() != Qt.LeftButton: return False
        row_count = self._model.get_row_count()

        if row_count == 0:
            self._model.clear_selection(); self._view.clear_visual_selection()
            self._v_guide_cols.clear(); self._view.set_v_guides(self._v_guide_cols)
            self._notify_selection_changed(); return True

        scene_pos = self._view.mapToScene(event.pos())
        row, col = self._view.scene_pos_to_row_col(scene_pos)
        ctrl = bool(event.modifiers() & Qt.ControlModifier)

        # Basış pozisyonunu sakla — drag threshold için
        self._press_pos = QPoint(event.pos())
        self._press_scene_row = row
        self._press_scene_col = col
        self._drag_started = False

        return True

    def handle_mouse_move(self, event):
        if self._press_pos is None: return False

        delta = (event.pos() - self._press_pos).manhattanLength()

        if not self._drag_started and delta >= _DRAG_THRESHOLD_PX:
            # Drag başlıyor — guide'ları hemen temizle (ctrl yoksa)
            self._drag_started = True
            self._is_selecting = True
            row = self._press_scene_row; col = self._press_scene_col
            row_count = self._model.get_row_count()
            if 0 <= row < row_count and col >= 0:
                self._model.start_selection(row, col)
            ctrl = bool(event.modifiers() & Qt.ControlModifier)
            if not ctrl:
                self._v_guide_cols.clear()
                self._view.set_v_guides(self._v_guide_cols)
            # SizeWE cursor
            self._view.viewport().setCursor(Qt.SizeHorCursor)

        if self._drag_started and self._is_selecting:
            scene_pos = self._view.mapToScene(event.pos())
            row, col = self._view.scene_pos_to_row_col(scene_pos)
            sel_range = self._model.update_selection(row, col)
            if sel_range:
                self._view.set_visual_selection(*sel_range)
                # Drag sırasında guide'ları canlı güncelle
                col_start, col_end = sel_range[2], sel_range[3]
                if col_end > col_start:
                    left_b, right_b = col_start, col_end + 1
                    self._v_guide_cols = [left_b, right_b]
                    self._view.set_v_guides(self._v_guide_cols)
                else:
                    self._view.set_v_guides(self._v_guide_cols)
            else:
                self._view.clear_visual_selection()
                self._view.set_v_guides(self._v_guide_cols)
            self._notify_selection_changed()
            return True

        return False

    def handle_mouse_release(self, event):
        if event.button() != Qt.LeftButton: return False

        # Cursor'ı geri al
        self._view.viewport().unsetCursor()
        # I-beam'i tekrar uygula
        self._view.viewport().setCursor(Qt.IBeamCursor)

        if self._drag_started:
            self._is_selecting = False
            self._drag_started = False
            self._press_pos = None
            sel = self._model.get_selection_column_range()
            if sel is not None:
                col_start, col_end = sel
                if col_end > col_start:
                    ctrl = bool(event.modifiers() & Qt.ControlModifier)
                    if not ctrl:
                        self._v_guide_cols.clear()
                    left_boundary = col_start
                    right_boundary = col_end + 1
                    for b in (left_boundary, right_boundary):
                        if b not in self._v_guide_cols:
                            self._v_guide_cols.append(b)
            self._view.set_v_guides(self._v_guide_cols)
            self._notify_selection_changed()
            return True

        # Drag olmadan bırakıldı → boundary tıklama
        if self._press_pos is not None and self._view.sequence_items:
            scene_pos = self._view.mapToScene(event.pos())
            boundary_col = self._boundary_col_at(float(scene_pos.x()))
            ctrl = bool(event.modifiers() & Qt.ControlModifier)

            if ctrl:
                # Ctrl+tık: toggle — aynı col varsa kaldır, yoksa ekle
                if boundary_col in self._v_guide_cols:
                    self._v_guide_cols.remove(boundary_col)
                else:
                    self._v_guide_cols.append(boundary_col)
            else:
                # Normal tık: tek guide
                self._v_guide_cols = [boundary_col]

            self._view.set_v_guides(self._v_guide_cols)
            # Seçimi temizle
            self._model.clear_selection(); self._view.clear_visual_selection()
            self._notify_selection_changed()

        self._press_pos = None
        self._drag_started = False
        return True

    def handle_wheel_event(self, event):
        if not (event.modifiers() & Qt.ControlModifier): return False
        delta = event.angleDelta().y()
        if delta == 0 or not self._view.sequence_items: return True
        steps = delta / 120.0; direction = 1 if steps > 0 else -1
        if self._wheel_zoom_streak_dir == direction: self._wheel_zoom_streak_len += 1
        else: self._wheel_zoom_streak_dir = direction; self._wheel_zoom_streak_len = 1
        hbar = self._view.horizontalScrollBar()
        view_width_px = float(self._view.viewport().width())
        if view_width_px <= 0: return True
        current_cw = self._view.current_char_width()
        if current_cw <= 0: current_cw = max(self._view.char_width, 0.001)
        center_nt = self._model.get_selection_center_nt()
        if center_nt is None:
            old_left_px = float(hbar.value()); cursor_x = float(event.pos().x())
            center_nt = (old_left_px + cursor_x) / current_cw
        streak_boost = pow(self._wheel_zoom_accel_factor, max(0, self._wheel_zoom_streak_len - 1))
        per_step_factor = self._wheel_zoom_base_factor * streak_boost
        magnitude_factor = pow(per_step_factor, abs(steps))
        factor = magnitude_factor if direction > 0 else 1.0 / magnitude_factor
        target_cw = max(self._view.compute_min_char_width(), min(current_cw * factor, 90.0))
        if abs(target_cw - current_cw) < 0.0001: return True
        self._view.start_zoom_animation(target_char_width=target_cw, center_nt=center_nt, view_width_px=view_width_px)
        return True

    def _notify_selection_changed(self):
        if self._on_selection_changed: self._on_selection_changed()