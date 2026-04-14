from __future__ import annotations

from sequence_viewer.utils.drag_tooltip import DragTooltip
from sequence_viewer.utils.sequence_utils import calculate_tm, selection_bp

from .sequence_viewer_controller_state import TooltipState


class SequenceViewerTooltipController:
    def __init__(self, model, view) -> None:
        self._model = model
        self._view = view
        self._state = TooltipState()
        self._drag_tooltip = DragTooltip(parent=self._view.viewport())

    @property
    def drag_tooltip(self) -> DragTooltip:
        return self._drag_tooltip

    @property
    def last_sel_range(self):
        return self._state.last_sel_range

    @last_sel_range.setter
    def last_sel_range(self, value) -> None:
        self._state.last_sel_range = value

    def clear(self) -> None:
        self._drag_tooltip.clear_panel()
        self._state.last_sel_range = None

    def clear_panel(self) -> None:
        self._drag_tooltip.clear_panel()

    def show_info_panel(self, row_start: int, row_end: int, col_start: int, col_end: int) -> None:
        sel_range = (row_start, row_end, col_start, col_end)
        self._state.last_sel_range = sel_range
        self._show_info_panel(sel_range)

    def update_drag_tooltip(self, sel_range) -> None:
        if sel_range is None or sel_range[3] <= sel_range[2]:
            self._drag_tooltip.clear_panel()
            self._state.last_sel_range = None
            return
        self._state.last_sel_range = sel_range
        self._show_info_panel(sel_range)

    def restore_last_panel_or_clear(self) -> None:
        if self._state.last_sel_range is not None:
            self._show_info_panel(self._state.last_sel_range)
        else:
            self._drag_tooltip.clear_panel()

    def hide_if_selection_cleared(self, is_selecting: bool) -> None:
        if is_selecting:
            return
        sel = self._model.get_selection_column_range()
        if sel is None:
            self._drag_tooltip.clear_panel()
            self._state.last_sel_range = None

    def _show_info_panel(self, sel_range: tuple[int, int, int, int]) -> None:
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


class SequenceViewerHoverController:
    def __init__(self, model, view, tooltip_controller: SequenceViewerTooltipController) -> None:
        self._model = model
        self._view = view
        self._tooltip_controller = tooltip_controller

    def handle_hover(self, event) -> None:
        scene_pos = self._view.mapToScene(event.pos())
        hover_row, hover_col = self._view.scene_pos_to_row_col(scene_pos)
        row_count = self._model.get_row_count()

        if row_count > 0 and 0 <= hover_row < row_count:
            boundary_col = self._boundary_col_at(float(scene_pos.x()))
            self._view.set_hover_caret(boundary_col, hover_row)
        else:
            self._view.clear_hover_caret()

        sel = self._model.get_selection_column_range()
        last_sel_range = self._tooltip_controller.last_sel_range
        drag_tooltip = self._tooltip_controller.drag_tooltip
        if sel is None or last_sel_range is None:
            if drag_tooltip.isVisible():
                drag_tooltip.clear_panel()
            return

        col_start, col_end = sel
        row_start, row_end = last_sel_range[0], last_sel_range[1]
        over_selection = (
            row_start <= hover_row <= row_end
            and col_start <= hover_col <= col_end
        )

        if over_selection:
            if not drag_tooltip.isVisible():
                self._tooltip_controller.show_info_panel(*last_sel_range)
        elif drag_tooltip.isVisible():
            drag_tooltip.clear_panel()

    def _boundary_col_at(self, scene_x: float) -> int:
        char_width = self._view._effective_char_width()
        if char_width <= 0:
            return 0
        return int(round(scene_x / char_width))
