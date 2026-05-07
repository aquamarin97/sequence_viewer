from __future__ import annotations

from typing import TYPE_CHECKING

from sequence_viewer.settings.mouse_binding_manager import MouseAction, mouse_binding_manager

if TYPE_CHECKING:
    from sequence_viewer.workspace.context import WorkspaceContext
    from sequence_viewer.workspace.coordinators.selection.selection_state import (
        WorkspaceSelectionState,
    )


class WorkspaceRowSelectionCoordinator:
    def __init__(
        self, ctx: "WorkspaceContext", state: "WorkspaceSelectionState"
    ) -> None:
        self._ctx = ctx
        self._state = state

    def _clear_annotation_selection(self) -> None:
        if not self._state.selected_annotations:
            return
        self._ctx.annotation_selection.clear_all_annotation_visuals()
        self._state.selected_annotations.clear()

    def on_selection_changed(self, selected_rows) -> None:
        from PyQt5.QtWidgets import QApplication

        ctx = self._ctx
        header_action = mouse_binding_manager.resolve_header_click(QApplication.keyboardModifiers())
        is_multi = header_action == MouseAction.ROW_MULTI_SELECT
        self._clear_annotation_selection()
        if not is_multi:
            ctx.consensus_spacer.set_selected(False)
            ctx.consensus_row.clear_selection()
        ctx.sequence_viewer.clear_v_guides()
        ctx.sequence_viewer.clear_selection_dim_range()
        if not selected_rows:
            ctx.sequence_viewer.clear_h_guides()
        else:
            ctx.sequence_viewer.set_h_guides(frozenset(selected_rows))
            n = ctx.model.row_count()
            max_len = ctx.model.max_sequence_length
            if n > 0 and max_len > 0:
                for i, item in enumerate(ctx.sequence_viewer.sequence_items):
                    if i in selected_rows:
                        item.set_selection(0, max_len)
                    else:
                        item.clear_selection()
                ctx.sequence_viewer.scene.invalidate()
                ctx.sequence_viewer.viewport().update()

    def on_seq_row_clicked(self, row_start: int, row_end: int) -> None:
        from PyQt5.QtWidgets import QApplication

        ctx = self._ctx
        n = ctx.model.row_count()
        if n == 0:
            return
        click_action = mouse_binding_manager.resolve_header_click(QApplication.keyboardModifiers())
        is_multi = click_action == MouseAction.ROW_MULTI_SELECT
        is_range = click_action == MouseAction.ROW_RANGE_SELECT
        is_drag = row_start != row_end

        if is_drag or click_action in (MouseAction.ROW_SELECT, MouseAction.NONE):
            self._clear_annotation_selection()
            ctx.consensus_spacer.set_selected(False)
            ctx.consensus_row.clear_selection()
            rows = frozenset(range(row_start, row_end + 1)) if 0 <= row_start < n else frozenset()
            clear_changed = ctx.header_viewer.clear_selection()
            click_changed: frozenset = frozenset()
            if rows:
                for row in rows:
                    click_changed = click_changed | ctx.header_viewer.toggle_row(row, n)
            ctx.header_viewer.apply_selection_to_items(clear_changed | click_changed)
            self._state.last_clicked_row = row_start
            if rows:
                ctx.sequence_viewer.set_h_guides(rows)
            else:
                ctx.sequence_viewer.clear_h_guides()

        elif is_multi:
            row = row_start
            if not (0 <= row < n):
                return
            changed = ctx.header_viewer.toggle_row(row, n)
            ctx.header_viewer.apply_selection_to_items(changed)
            selected = ctx.header_viewer.selected_rows()
            self._state.last_clicked_row = row
            if selected:
                ctx.sequence_viewer.set_h_guides(frozenset(selected))
            else:
                ctx.sequence_viewer.clear_h_guides()

        elif is_range:
            anchor = self._state.last_clicked_row
            lo, hi = min(anchor, row_start), max(anchor, row_start)
            rows = frozenset(range(lo, hi + 1)) if 0 <= lo < n else frozenset()
            if rows:
                click_changed = ctx.header_viewer.range_select(lo, hi, n)
                ctx.header_viewer.apply_selection_to_items(click_changed)
            selected = ctx.header_viewer.selected_rows()
            if selected:
                ctx.sequence_viewer.set_h_guides(frozenset(selected))
            else:
                ctx.sequence_viewer.clear_h_guides()

    def on_consensus_spacer_clicked(self, ctrl: bool = False) -> None:
        self._clear_annotation_selection()
        ctx = self._ctx
        was_selected = ctx.consensus_spacer.is_selected
        ctx.consensus_row.clear_selection()
        ctx.sequence_viewer.clear_v_guides()
        ctx.sequence_viewer.clear_selection_dim_range()
        if ctrl:
            if was_selected:
                ctx.consensus_spacer.set_selected(False)
                ctx.consensus_row.clear_selection()
            else:
                ctx.consensus_spacer.set_selected(True)
                ctx.consensus_spacer.setFocus()
                ctx.consensus_row.set_selected(True)
                ctx.consensus_row.select_all()
        else:
            changed = ctx.header_viewer.clear_selection()
            ctx.header_viewer.apply_selection_to_items(changed)
            ctx.sequence_viewer.clear_h_guides()
            ctx.sequence_viewer.clear_visual_selection()
            ctx.sequence_viewer.clear_selection_model()
            ctx.consensus_spacer.set_selected(True)
            ctx.consensus_spacer.setFocus()
            ctx.consensus_row.set_selected(True)
            ctx.consensus_row.select_all()
