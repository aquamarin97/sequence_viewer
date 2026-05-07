from __future__ import annotations

from sequence_viewer.model.annotation import Annotation, AnnotationType
from sequence_viewer.settings.mouse_binding_manager import MouseAction
from sequence_viewer.workspace.coordinators.selection import row_selection_coordinator
from sequence_viewer.workspace.coordinators.selection.row_selection_coordinator import (
    WorkspaceRowSelectionCoordinator,
)


def make_annotation() -> Annotation:
    return Annotation(type=AnnotationType.PRIMER, start=0, end=3, id="ann-1")


def test_on_seq_row_clicked_drag_clears_annotation_selection(
    ctx, state, monkeypatch
) -> None:
    state.selected_annotations = [(make_annotation(), 0)]
    coordinator = WorkspaceRowSelectionCoordinator(ctx, state)
    monkeypatch.setattr(
        row_selection_coordinator.mouse_binding_manager,
        "resolve_header_click",
        lambda *_args, **_kwargs: MouseAction.ROW_SELECT,
    )

    coordinator.on_seq_row_clicked(0, 1)

    assert state.selected_annotations == []
    ctx.annotation_selection.clear_all_annotation_visuals.assert_called_once()


def test_on_consensus_spacer_clicked_without_ctrl_clears_header_selection(
    ctx, state
) -> None:
    coordinator = WorkspaceRowSelectionCoordinator(ctx, state)

    coordinator.on_consensus_spacer_clicked(ctrl=False)

    ctx.header_viewer.clear_selection.assert_called_once()
    ctx.header_viewer.apply_selection_to_items.assert_called_once()


def test_on_consensus_spacer_clicked_ctrl_selected_deselects(ctx, state) -> None:
    ctx.consensus_spacer.is_selected = True
    coordinator = WorkspaceRowSelectionCoordinator(ctx, state)

    coordinator.on_consensus_spacer_clicked(ctrl=True)

    ctx.consensus_spacer.set_selected.assert_called_once_with(False)
    ctx.consensus_row.set_selected.assert_not_called()
