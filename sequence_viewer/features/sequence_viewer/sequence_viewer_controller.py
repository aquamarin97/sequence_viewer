# features/sequence_viewer/sequence_viewer_controller.py
from typing import Optional, Callable, List
from math import pow
from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtWidgets import QScrollBar
from .sequence_viewer_model import SequenceViewerModel
from .sequence_viewer_view import SequenceViewerView
from sequence_viewer.settings.mouse_binding_manager import mouse_binding_manager, MouseAction
from sequence_viewer.utils.drag_tooltip import DragTooltip
from sequence_viewer.utils.sequence_utils import selection_bp, calculate_tm


class SequenceViewerController:
    def __init__(self, model, view, *, on_selection_changed=None, on_row_clicked=None):
        self._model = model; self._view = view
        self._is_selecting = False
        # drag-threshold takibi
        self._press_pos: Optional[QPoint] = None
        self._press_scene_col: Optional[int] = None
        self._press_scene_row: Optional[int] = None
        self._drag_started = False
        self._drag_end_row: Optional[int] = None
        self._last_notified_row_range: Optional[tuple] = None
        self._wheel_zoom_streak_dir = None; self._wheel_zoom_streak_len = 0
        self._on_selection_changed = on_selection_changed
        self._on_row_clicked = on_row_clicked
        # Ã‡oklu dikey guide: her eleman bir col index (NA'nÄ±n solundaki sÄ±nÄ±r)
        self._v_guide_cols: List[int] = []
        self._drag_tooltip = DragTooltip()

    # ------------------------------------------------------------------
    # YardÄ±mcÄ±: viewport px â†’ sahne kolonu (NA sÄ±nÄ±rÄ± yuvarlama)
    # ------------------------------------------------------------------
    def _boundary_col_at(self, scene_x: float) -> int:
        """
        scene_x pikselinin en yakÄ±n NA sÄ±nÄ±rÄ±nÄ± (kolon solundan) dÃ¶ndÃ¼rÃ¼r.
        Her NA, kendi geniÅŸliÄŸinin yarÄ±sÄ±na kadar sol sÄ±nÄ±ra, yarÄ±sÄ±ndan
        itibaren saÄŸ sÄ±nÄ±ra (= bir sonraki NA'nÄ±n sol sÄ±nÄ±rÄ±) yÃ¶nlendirir.
        """
        cw = self._view._effective_char_width()
        if cw <= 0: return 0
        return int(round(scene_x / cw))

    def _is_boundary_click(self, viewport_pos) -> bool:
        """TÄ±klama konumunda dizi varsa True dÃ¶ner (boÅŸ alan deÄŸil)."""
        return bool(self._view.sequence_items)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def add_sequence(self, sequence_string):
        self._model.add_sequence(sequence_string)
        self._view.add_sequence_item(sequence_string)

    def clear(self):
        self._drag_tooltip.clear_tooltip()
        self._model.clear_sequences(); self._view.clear_items()
        self._is_selecting = False; self._drag_started = False
        self._press_pos = None
        self._v_guide_cols.clear()
        self._view.set_v_guides(self._v_guide_cols)
        self._view.clear_caret()
        self._view.clear_selection_dim_range()
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

        # BasÄ±ÅŸ pozisyonunu sakla â€” drag threshold iÃ§in
        self._press_pos = QPoint(event.pos())
        self._press_scene_row = row
        self._press_scene_col = col
        self._drag_started = False

        return True

    def handle_mouse_move(self, event):
        if self._press_pos is None: return False

        delta = (event.pos() - self._press_pos).manhattanLength()

        if not self._drag_started and delta >= mouse_binding_manager.drag_threshold("sequence_viewer"):
            # Drag baÅŸlÄ±yor â€” guide'larÄ± hemen temizle (aksiyon DRAG_SELECT ise)
            drag_action = mouse_binding_manager.resolve_sequence_drag(event.modifiers(), Qt.LeftButton)
            if drag_action == MouseAction.NONE:
                return False
            self._drag_started = True
            self._is_selecting = True
            row = self._press_scene_row; col = self._press_scene_col
            row_count = self._model.get_row_count()
            if 0 <= row < row_count and col >= 0:
                self._model.start_selection(row, col)
            if drag_action == MouseAction.DRAG_SELECT:
                self._v_guide_cols.clear()
                self._view.set_v_guides(self._v_guide_cols)
            self._view.clear_caret()
            # SizeWE cursor
            self._view.viewport().setCursor(Qt.SizeHorCursor)

        if self._drag_started and self._is_selecting:
            scene_pos = self._view.mapToScene(event.pos())
            row, col = self._view.scene_pos_to_row_col(scene_pos)
            self._drag_end_row = row
            sel_range = self._model.update_selection(row, col)
            if sel_range:
                self._view.set_visual_selection(*sel_range)
                # Drag sÄ±rasÄ±nda guide'larÄ± ve dim range'i canlÄ± gÃ¼ncelle
                col_start, col_end = sel_range[2], sel_range[3]
                if col_end > col_start:
                    left_b, right_b = col_start, col_end + 1
                    self._v_guide_cols = [left_b, right_b]
                    self._view.set_v_guides(self._v_guide_cols)
                    self._view.set_selection_dim_range(left_b, right_b)
                else:
                    self._v_guide_cols.clear()
                    self._view.set_v_guides(self._v_guide_cols)
                    self._view.clear_selection_dim_range()
            else:
                self._view.clear_visual_selection()
                self._view.set_v_guides(self._v_guide_cols)
            self._notify_selection_changed()
            self._update_drag_tooltip(event, sel_range)
            # SatÄ±r aralÄ±ÄŸÄ± deÄŸiÅŸtiyse row highlight'Ä± canlÄ± gÃ¼ncelle
            r0 = self._press_scene_row
            r1 = row
            if (r0, r1) != self._last_notified_row_range:
                self._last_notified_row_range = (r0, r1)
                self._notify_row_clicked(r0, r1)
            return True

        return False

    def handle_mouse_release(self, event):
        if event.button() != Qt.LeftButton: return False

        # Cursor'Ä± geri al
        self._view.viewport().unsetCursor()
        # I-beam'i tekrar uygula
        self._view.viewport().setCursor(Qt.IBeamCursor)

        if self._drag_started:
            self._drag_tooltip.clear_tooltip()
            self._is_selecting = False
            self._drag_started = False
            row_start = self._press_scene_row
            row_end = self._drag_end_row if self._drag_end_row is not None else row_start
            self._drag_end_row = None
            self._last_notified_row_range = None
            self._press_pos = None
            sel = self._model.get_selection_column_range()
            if sel is not None:
                col_start, col_end = sel
                if col_end > col_start:
                    drag_action = mouse_binding_manager.resolve_sequence_drag(event.modifiers(), Qt.LeftButton)
                    if drag_action == MouseAction.DRAG_SELECT:
                        self._v_guide_cols.clear()
                    left_boundary = col_start
                    right_boundary = col_end + 1
                    for b in (left_boundary, right_boundary):
                        if b not in self._v_guide_cols:
                            self._v_guide_cols.append(b)
                    # Dim range'i koru (mouse release'den sonra da efekt kalÄ±r)
                    self._view.set_selection_dim_range(left_boundary, right_boundary)
                else:
                    self._v_guide_cols.clear()
                    self._view.clear_selection_dim_range()
            else:
                self._v_guide_cols.clear()
                self._view.clear_selection_dim_range()
            self._view.set_v_guides(self._v_guide_cols)
            self._notify_selection_changed()
            self._notify_row_clicked(row_start, row_end)
            return True

        # Drag olmadan bÄ±rakÄ±ldÄ± â†’ boundary tÄ±klama
        if self._press_pos is not None and self._view.sequence_items:
            scene_pos = self._view.mapToScene(event.pos())
            boundary_col = self._boundary_col_at(float(scene_pos.x()))
            click_action = mouse_binding_manager.resolve_sequence_click(event.modifiers(), Qt.LeftButton)
            if click_action == MouseAction.NONE:
                self._press_pos = None
                self._drag_started = False
                return False
            row_start = self._press_scene_row
            row_end = row_start

            if click_action == MouseAction.GUIDE_TOGGLE:
                # Toggle â€” aynÄ± col varsa kaldÄ±r, yoksa ekle
                self._view.clear_caret()
                if boundary_col in self._v_guide_cols:
                    self._v_guide_cols.remove(boundary_col)
                else:
                    self._v_guide_cols.append(boundary_col)
            else:
                # Tek guide koy + tÄ±klanan satÄ±ra I-beam caret
                self._v_guide_cols = [boundary_col]
                self._view.set_caret(boundary_col, row_start)

            # Boundary tÄ±klamada dim efektini temizle (yeni seÃ§im yok)
            self._view.clear_selection_dim_range()
            self._view.set_v_guides(self._v_guide_cols)
            # SeÃ§imi temizle
            self._model.clear_selection(); self._view.clear_visual_selection()
            self._notify_selection_changed()
            self._notify_row_clicked(row_start, row_end)

        self._press_pos = None
        self._drag_started = False
        return True

    def handle_wheel_event(self, event):
        if mouse_binding_manager.is_h_scroll_event(event.modifiers()):
            delta = event.angleDelta().y()
            if delta == 0: delta = event.angleDelta().x()
            if delta != 0:
                hbar = self._view.horizontalScrollBar()
                step = max(1, int(self._view._effective_char_width() * 3))
                hbar.setValue(hbar.value() - int(delta / 120.0 * step))
            return True
        if not mouse_binding_manager.is_zoom_event(event.modifiers()): return False
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
        streak_boost = pow(mouse_binding_manager.zoom_accel_factor, max(0, self._wheel_zoom_streak_len - 1))
        per_step_factor = mouse_binding_manager.zoom_base_factor * streak_boost
        magnitude_factor = pow(per_step_factor, abs(steps))
        factor = magnitude_factor if direction > 0 else 1.0 / magnitude_factor
        target_cw = max(self._view.compute_min_char_width(),
                        min(current_cw * factor, mouse_binding_manager.zoom_max_char_width))
        if abs(target_cw - current_cw) < 0.0001: return True
        self._view.start_zoom_animation(target_char_width=target_cw, center_nt=center_nt, view_width_px=view_width_px)
        return True

    # ------------------------------------------------------------------
    # Drag tooltip
    # ------------------------------------------------------------------
    def _update_drag_tooltip(self, event, sel_range):
        """Show / update the floating Bp/Tm panel near the cursor."""
        if sel_range is None:
            self._drag_tooltip.clear_tooltip()
            return
        row_start, row_end, col_start, col_end = sel_range
        if col_end <= col_start:
            self._drag_tooltip.clear_tooltip()
            return
        bp = selection_bp(col_start, col_end)
        global_pos = self._view.viewport().mapToGlobal(event.pos())
        if row_start == row_end:
            sequences = self._model.get_sequences()
            tm = None
            if 0 <= row_start < len(sequences):
                fragment = sequences[row_start][col_start:col_end + 1]
                tm = calculate_tm(fragment)
            self._drag_tooltip.show_bp_tm(global_pos, bp, tm)
        else:
            self._drag_tooltip.show_bp_only(global_pos, bp)

    def _notify_selection_changed(self):
        if self._on_selection_changed: self._on_selection_changed()

    def _notify_row_clicked(self, row_start, row_end):
        if self._on_row_clicked and row_start is not None:
            row_count = self._model.get_row_count()
            r0 = max(0, min(row_start, row_end) if row_end is not None else row_start)
            r1 = min(row_count - 1, max(row_start, row_end) if row_end is not None else row_start)
            if 0 <= r0 <= r1 < row_count:
                self._on_row_clicked(r0, r1)


