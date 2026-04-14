from __future__ import annotations

from PyQt5.QtCore import QPoint, Qt

from sequence_viewer.settings.mouse_binding_manager import MouseAction, mouse_binding_manager

from .sequence_viewer_controller_state import MouseSelectionState


class SequenceViewerMouseController:
    def __init__(
        self,
        model,
        view,
        tooltip_controller,
        hover_controller,
        *,
        on_selection_changed=None,
        on_row_clicked=None,
    ) -> None:
        self._model = model
        self._view = view
        self._tooltip_controller = tooltip_controller
        self._hover_controller = hover_controller
        self._on_selection_changed = on_selection_changed
        self._on_row_clicked = on_row_clicked
        self._state = MouseSelectionState()
        self._v_guide_cols: list[int] = []

    @property
    def is_selecting(self) -> bool:
        return self._state.is_selecting

    @property
    def v_guide_cols(self) -> list[int]:
        return list(self._v_guide_cols)

    def set_v_guides(self, cols: list[int]) -> None:
        self._v_guide_cols = list(cols)
        self._view.set_v_guides(self._v_guide_cols)

    def clear_v_guides(self) -> None:
        self._v_guide_cols.clear()
        self._view.set_v_guides(self._v_guide_cols)

    def clear(self) -> None:
        self._state = MouseSelectionState()
        self.clear_v_guides()

    def notify_selection_changed(self) -> None:
        self._notify_selection_changed()

    def handle_mouse_press(self, event) -> bool:
        if event.button() != Qt.LeftButton:
            return False
        row_count = self._model.get_row_count()

        if row_count == 0:
            self._model.clear_selection()
            self._view.clear_visual_selection()
            self.clear_v_guides()
            self._notify_selection_changed()
            return True

        self._view.clear_hover_caret()
        scene_pos = self._view.mapToScene(event.pos())
        row, col = self._view.scene_pos_to_row_col(scene_pos)

        self._state.press_pos = QPoint(event.pos())
        self._state.press_scene_row = row
        self._state.press_scene_col = col
        self._state.drag_started = False
        return True

    def handle_mouse_move(self, event) -> bool:
        if self._state.press_pos is None:
            self._hover_controller.handle_hover(event)
            return False

        delta = (event.pos() - self._state.press_pos).manhattanLength()
        if not self._state.drag_started:
            if not self._maybe_start_drag(event, delta):
                return False

        if self._state.drag_started and self._state.is_selecting:
            return self._update_drag_selection(event)
        return False

    def handle_mouse_release(self, event) -> bool:
        if event.button() != Qt.LeftButton:
            return False

        self._view.viewport().unsetCursor()
        self._view.viewport().setCursor(Qt.IBeamCursor)

        if self._state.drag_started:
            return self._finish_drag_selection(event)
        if self._state.press_pos is not None and self._view.sequence_items:
            return self._handle_boundary_click(event)

        self._state.press_pos = None
        self._state.drag_started = False
        return True

    def _maybe_start_drag(self, event, delta: int) -> bool:
        if delta < mouse_binding_manager.drag_threshold("sequence_viewer"):
            return False
        drag_action = mouse_binding_manager.resolve_sequence_drag(event.modifiers(), Qt.LeftButton)
        if drag_action == MouseAction.NONE:
            return False

        self._state.drag_started = True
        self._state.is_selecting = True
        row = self._state.press_scene_row
        col = self._state.press_scene_col
        row_count = self._model.get_row_count()
        if row is not None and 0 <= row < row_count and col is not None and col >= 0:
            self._model.start_selection(row, col)
        if drag_action == MouseAction.DRAG_SELECT:
            self.clear_v_guides()
        self._view.clear_caret()
        self._view.clear_hover_caret()
        self._view.viewport().setCursor(Qt.SizeHorCursor)
        return True

    def _update_drag_selection(self, event) -> bool:
        scene_pos = self._view.mapToScene(event.pos())
        row, col = self._view.scene_pos_to_row_col(scene_pos)
        self._state.drag_end_row = row
        sel_range = self._model.update_selection(row, col)
        if sel_range:
            self._view.set_visual_selection(*sel_range)
            col_start, col_end = sel_range[2], sel_range[3]
            if col_end > col_start:
                left_b, right_b = col_start, col_end + 1
                self.set_v_guides([left_b, right_b])
                self._view.set_selection_dim_range(left_b, right_b)
            else:
                self.clear_v_guides()
                self._view.clear_selection_dim_range()
        else:
            self._view.clear_visual_selection()
            self._view.set_v_guides(self._v_guide_cols)
        self._notify_selection_changed()
        self._tooltip_controller.update_drag_tooltip(sel_range)
        self._notify_row_range(row)
        return True

    def _finish_drag_selection(self, event) -> bool:
        self._state.is_selecting = False
        self._state.drag_started = False
        row_start = self._state.press_scene_row
        row_end = self._state.drag_end_row if self._state.drag_end_row is not None else row_start
        self._state.drag_end_row = None
        self._state.last_notified_row_range = None
        self._state.press_pos = None

        self._tooltip_controller.restore_last_panel_or_clear()
        sel = self._model.get_selection_column_range()
        if sel is not None:
            col_start, col_end = sel
            if col_end > col_start:
                drag_action = mouse_binding_manager.resolve_sequence_drag(event.modifiers(), Qt.LeftButton)
                if drag_action == MouseAction.DRAG_SELECT:
                    self._v_guide_cols.clear()
                left_boundary = col_start
                right_boundary = col_end + 1
                for boundary in (left_boundary, right_boundary):
                    if boundary not in self._v_guide_cols:
                        self._v_guide_cols.append(boundary)
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

    def _handle_boundary_click(self, event) -> bool:
        scene_pos = self._view.mapToScene(event.pos())
        boundary_col = self._boundary_col_at(float(scene_pos.x()))
        click_action = mouse_binding_manager.resolve_sequence_click(event.modifiers(), Qt.LeftButton)
        if click_action == MouseAction.NONE:
            self._state.press_pos = None
            self._state.drag_started = False
            return False

        row_start = self._state.press_scene_row
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
        self._model.clear_selection()
        self._view.clear_visual_selection()
        self._notify_selection_changed()
        self._notify_row_clicked(row_start, row_end)
        self._state.press_pos = None
        self._state.drag_started = False
        return True

    def _notify_selection_changed(self) -> None:
        if self._on_selection_changed:
            self._on_selection_changed()
        self._tooltip_controller.hide_if_selection_cleared(self._state.is_selecting)

    def _notify_row_range(self, row: int) -> None:
        row_start = self._state.press_scene_row
        if row_start is None:
            return
        current_range = (row_start, row)
        if current_range != self._state.last_notified_row_range:
            self._state.last_notified_row_range = current_range
            self._notify_row_clicked(row_start, row)

    def _notify_row_clicked(self, row_start, row_end) -> None:
        if self._on_row_clicked and row_start is not None:
            row_count = self._model.get_row_count()
            r0 = max(0, min(row_start, row_end) if row_end is not None else row_start)
            r1 = min(row_count - 1, max(row_start, row_end) if row_end is not None else row_start)
            if 0 <= r0 <= r1 < row_count:
                self._on_row_clicked(r0, r1)

    def _boundary_col_at(self, scene_x: float) -> int:
        char_width = self._view._effective_char_width()
        if char_width <= 0:
            return 0
        return int(round(scene_x / char_width))
