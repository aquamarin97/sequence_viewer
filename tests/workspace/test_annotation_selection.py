from __future__ import annotations

from sequence_viewer.model.annotation import Annotation, AnnotationType
from settings.bindings.mouse import MouseAction
from sequence_viewer.workspace.coordinators.selection import annotation_selection_coordinator
from sequence_viewer.workspace.coordinators.selection.annotation_selection_coordinator import (
    WorkspaceAnnotationSelectionCoordinator,
)


def make_annotation(annotation_id: str = "ann-1") -> Annotation:
    return Annotation(
        type=AnnotationType.PRIMER,
        start=2,
        end=5,
        label="Primer",
        id=annotation_id,
    )


def test_on_annotation_layer_clicked_updates_selected_annotations(
    ctx, state, monkeypatch
) -> None:
    annotation = make_annotation()
    coordinator = WorkspaceAnnotationSelectionCoordinator(ctx, state)
    monkeypatch.setattr(
        annotation_selection_coordinator.mouse_binding_manager,
        "resolve_annotation_click",
        lambda *_args, **_kwargs: MouseAction.ANNOTATION_SELECT,
    )

    coordinator.on_annotation_layer_clicked(annotation)

    assert state.selected_annotations == [(annotation, None)]


def test_annotation_layer_multi_select_clicking_same_annotation_removes_it(
    ctx, state, monkeypatch
) -> None:
    annotation = make_annotation()
    state.selected_annotations = [(annotation, None)]
    coordinator = WorkspaceAnnotationSelectionCoordinator(ctx, state)
    monkeypatch.setattr(
        annotation_selection_coordinator.mouse_binding_manager,
        "resolve_annotation_click",
        lambda *_args, **_kwargs: MouseAction.ANNOTATION_MULTI_SELECT,
    )

    coordinator.on_annotation_layer_clicked(annotation)

    assert state.selected_annotations == []


def test_clear_selected_annotations_empties_state(ctx, state) -> None:
    annotation = make_annotation()
    state.selected_annotations = [(annotation, None)]
    coordinator = WorkspaceAnnotationSelectionCoordinator(ctx, state)

    coordinator.clear_selected_annotations()

    assert state.selected_annotations == []


def test_apply_union_selection_empty_state_clears_h_guides(ctx, state) -> None:
    coordinator = WorkspaceAnnotationSelectionCoordinator(ctx, state)

    coordinator.apply_union_selection()

    ctx.sequence_viewer.clear_h_guides.assert_called_once()
