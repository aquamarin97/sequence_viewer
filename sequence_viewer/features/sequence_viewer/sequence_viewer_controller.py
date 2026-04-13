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
        self._press_pos: Optional[QPoint] = None
        self._press_scene_col: Optional[int] = None
        self._press_scene_row: Optional[int] = None
        self._drag_started = False
        self._drag_end_row: Optional[int] = None
        self._last_notified_row_range: Optional[tuple] = None
        self._wheel_zoom_streak_dir = None; self._wheel_zoom_streak_len = 0
        self._on_selection_changed = on_selection_changed
        self._on_row_clicked = on_row_clicked
        self._v_guide_cols: List[int] = []
        # Viewport çocuk widget'ı olarak oluştur — top-level değil
        self._drag_tooltip = DragTooltip(parent=self._view.viewport())
        # Son bilinen seçim aralığı: (row_start, row_end, col_start, col_end)
        self._last_sel_range: Optional[tuple] = None

    # ------------------------------------------------------------------
    # Yardımcı: viewport px → sahne kolonu
    # ------------------------------------------------------------------
    def _boundary_col_at(self, scene_x: float) -> int:
        cw = self._view._effective_char_width()
        if cw <= 0: return 0
        return int(round(scene_x / cw))

    def _is_boundary_click(self, viewport_pos) -> bool:
        return bool(self._view.sequence_items)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def add_sequence(self, sequence_string):
        self._model.add_sequence(sequence_string)
        self._view.add_sequence_item(sequence_string)

    def clear(self):
        self._drag_tooltip.clear_panel()
        self._last_sel_range = None
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

        self._press_pos = QPoint(event.pos())
        self._press_scene_row = row
        self._press_scene_col = col
        self._drag_started = False

        return True

    def handle_mouse_move(self, event):
        # Drag yoksa → hover kontrolü
        if self._press_pos is None:
            self._handle_hover(event)
            return False

        delta = (event.pos() - self._press_pos).manhattanLength()

        if not self._drag_started and delta >= mouse_binding_manager.drag_threshold("sequence_viewer"):
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
            self._view.viewport().setCursor(Qt.SizeHorCursor)

        if self._drag_started and self._is_selecting:
            scene_pos = self._view.mapToScene(event.pos())
            row, col = self._view.scene_pos_to_row_col(scene_pos)
            self._drag_end_row = row
            sel_range = self._model.update_selection(row, col)
            if sel_range:
                self._view.set_visual_selection(*sel_range)
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
            self._update_drag_tooltip(sel_range)
            r0 = self._press_scene_row
            r1 = row
            if (r0, r1) != self._last_notified_row_range:
                self._last_notified_row_range = (r0, r1)
                self._notify_row_clicked(r0, r1)
            return True

        return False

    def handle_mouse_release(self, event):
        if event.button() != Qt.LeftButton: return False

        self._view.viewport().unsetCursor()
        self._view.viewport().setCursor(Qt.IBeamCursor)

        if self._drag_started:
            self._is_selecting = False
            self._drag_started = False
            row_start = self._press_scene_row
            row_end = self._drag_end_row if self._drag_end_row is not None else row_start
            self._drag_end_row = None
            self._last_notified_row_range = None
            self._press_pos = None
            # Seçim varsa paneli seçimin sağ-altında sabitle
            if self._last_sel_range is not None:
                self._show_info_panel(self._last_sel_range)
            else:
                self._drag_tooltip.clear_panel()
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

        # Drag olmadan bırakıldı → boundary tıklama
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
                self._view.clear_caret()
                if boundary_col in self._v_guide_cols:
                    self._v_guide_cols.remove(boundary_col)
                else:
                    self._v_guide_cols.append(boundary_col)
            else:
                self._v_guide_cols = [boundary_col]
                self._view.set_caret(boundary_col, row_start)

            self._view.clear_selection_dim_range()
            self._view.set_v_guides(self._v_guide_cols)
            # Tıklama seçimi temizler → paneli gizle
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
                # Yatay scroll → paneli gizle (hover ile tekrar gösterilebilir)
                self._drag_tooltip.clear_panel()
                hbar = self._view.horizontalScrollBar()
                step = max(1, int(self._view._effective_char_width() * 3))
                hbar.setValue(hbar.value() - int(delta / 120.0 * step))
            return True
        if not mouse_binding_manager.is_zoom_event(event.modifiers()): return False
        delta = event.angleDelta().y()
        if delta == 0 or not self._view.sequence_items: return True
        # Zoom → paneli gizle (hover ile tekrar gösterilebilir)
        self._drag_tooltip.clear_panel()
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
    # Info panel — seçim sağ-altında bp / Tm gösterimi
    # ------------------------------------------------------------------

    def _show_info_panel(self, sel_range: tuple) -> None:
        """
        sel_range = (row_start, row_end, col_start, col_end).
        Paneli seçimin sağ-alt köşesine konumlandırır.
        """
        row_start, row_end, col_start, col_end = sel_range
        if col_end <= col_start:
            self._drag_tooltip.clear_panel()
            return
        bp = selection_bp(col_start, col_end)
        anchor = self._view.selection_viewport_anchor(row_end, col_end)
        if row_start == row_end:
            sequences = self._model.get_sequences()
            tm = None
            if 0 <= row_start < len(sequences):
                fragment = sequences[row_start][col_start:col_end + 1]
                tm = calculate_tm(fragment)
            self._drag_tooltip.show_bp_tm(anchor, bp, tm)
        else:
            self._drag_tooltip.show_bp_only(anchor, bp)

    def show_info_panel(self, row_start: int, row_end: int,
                        col_start: int, col_end: int) -> None:
        """Dışarıdan (annotation click vb.) seçim için paneli gösterir."""
        sel_range = (row_start, row_end, col_start, col_end)
        self._last_sel_range = sel_range
        self._show_info_panel(sel_range)

    def _update_drag_tooltip(self, sel_range) -> None:
        """Drag sırasında paneli seçimin sağ-altında günceller."""
        if sel_range is None or sel_range[3] <= sel_range[2]:
            self._drag_tooltip.clear_panel()
            self._last_sel_range = None
            return
        self._last_sel_range = sel_range
        self._show_info_panel(sel_range)

    def _handle_hover(self, event) -> None:
        """
        Drag dışı mouse hareketi: seçim alanı üzerindeyse paneli göster,
        dışındaysa gizle. Zoom/scroll sonrası hover ile panel yeniden açılır.
        """
        sel = self._model.get_selection_column_range()
        if sel is None or self._last_sel_range is None:
            if self._drag_tooltip.isVisible():
                self._drag_tooltip.clear_panel()
            return

        col_start, col_end = sel
        row_start, row_end = self._last_sel_range[0], self._last_sel_range[1]

        scene_pos = self._view.mapToScene(event.pos())
        hover_row, hover_col = self._view.scene_pos_to_row_col(scene_pos)

        over_selection = (
            row_start <= hover_row <= row_end
            and col_start <= hover_col <= col_end
        )

        if over_selection:
            if not self._drag_tooltip.isVisible():
                self._show_info_panel(self._last_sel_range)
        else:
            if self._drag_tooltip.isVisible():
                self._drag_tooltip.clear_panel()

    # ------------------------------------------------------------------
    # Bildirimler
    # ------------------------------------------------------------------

    def _notify_selection_changed(self):
        if self._on_selection_changed: self._on_selection_changed()
        # Drag dışında seçim kalmadıysa paneli gizle
        if not self._is_selecting:
            sel = self._model.get_selection_column_range()
            if sel is None:
                self._drag_tooltip.clear_panel()
                self._last_sel_range = None

    def _notify_row_clicked(self, row_start, row_end):
        if self._on_row_clicked and row_start is not None:
            row_count = self._model.get_row_count()
            r0 = max(0, min(row_start, row_end) if row_end is not None else row_start)
            r1 = min(row_count - 1, max(row_start, row_end) if row_end is not None else row_start)
            if 0 <= r0 <= r1 < row_count:
                self._on_row_clicked(r0, r1)
