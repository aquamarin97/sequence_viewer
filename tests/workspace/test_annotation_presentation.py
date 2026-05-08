from __future__ import annotations

from sequence_viewer.workspace.coordinators.annotation_presentation import (
    WorkspaceAnnotationPresentation,
)


def test_zoom_changed_without_annotation_items_skips_row_layout(ctx) -> None:
    presentation = WorkspaceAnnotationPresentation(ctx)

    presentation.on_zoom_changed()

    ctx.layout_sync.compute_row_layout.assert_not_called()
