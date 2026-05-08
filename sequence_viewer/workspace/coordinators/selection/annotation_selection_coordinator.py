from __future__ import annotations

from typing import TYPE_CHECKING

from sequence_viewer.model.annotation import AnnotationType
from sequence_viewer.settings.mouse_binding_manager import MouseAction, mouse_binding_manager

if TYPE_CHECKING:
    from sequence_viewer.workspace.context import WorkspaceContext
    from sequence_viewer.workspace.coordinators.selection.selection_state import (
        WorkspaceSelectionState,
    )


class WorkspaceAnnotationSelectionCoordinator:
    def __init__(
        self, ctx: "WorkspaceContext", state: "WorkspaceSelectionState"
    ) -> None:
        self._ctx = ctx
        self._state = state

    # Secim durumu sorgu / degisim

    def has_selected_annotations(self) -> bool:
        return bool(self._state.selected_annotations)

    def get_selected_annotations(self) -> list:
        return list(self._state.selected_annotations)

    def clear_selected_annotations(self) -> None:
        self._state.selected_annotations.clear()

    def delete_selected_annotation(self) -> None:
        if not self._state.selected_annotations:
            return
        self._ctx.command_controller.delete_annotations_with_undo(
            self._state.selected_annotations
        )

    # Secim gorsel senkronizasyonu

    def _update_selection_visuals(self, ann_id, is_layer: bool, ctrl: bool = False) -> None:
        self._ctx.annotation_presentation.set_selected_annotation(
            ann_id if not is_layer else None, ctrl=ctrl
        )
        self._ctx.annotation_layer.set_selected_annotation(
            ann_id if is_layer else None, ctrl=ctrl
        )

    @staticmethod
    def _annotation_focus_range(annotation):
        return (
            (annotation.start, annotation.start + 1)
            if annotation.type == AnnotationType.MISMATCH_MARKER
            else (annotation.start, annotation.end + 1)
        )

    @staticmethod
    def _annotation_guide_boundaries(annotation):
        return (
            [annotation.start]
            if annotation.type == AnnotationType.MISMATCH_MARKER
            else [annotation.start, annotation.end + 1]
        )

    def clear_all_annotation_visuals(self) -> None:
        self._ctx.annotation_presentation.clear_annotation_selection()
        self._ctx.annotation_layer.clear_annotation_selection()
        self._ctx.sequence_viewer.clear_selection_dim_range()

    def apply_union_selection(self) -> None:
        ctx = self._ctx
        n = ctx.model.row_count()
        ctx.sequence_viewer.clear_visual_selection()
        ctx.sequence_viewer.clear_selection_model()
        ctx.sequence_viewer.clear_selection_dim_range()

        cr_ann_ids = ctx.consensus_row.get_selected_annotation_ids()
        cr_anns: list = []
        if cr_ann_ids and getattr(ctx.model, "is_aligned", False):
            ann_map = {a.id: a for a in ctx.model.consensus_annotations}
            cr_anns = [ann_map[aid] for aid in cr_ann_ids if aid in ann_map]

        has_any = bool(self._state.selected_annotations or cr_anns)
        if not has_any or n == 0:
            ctx.sequence_viewer.clear_h_guides()
            changed = ctx.header_viewer.clear_selection()
            ctx.header_viewer.apply_selection_to_items(changed)
            return

        pool_by_row = {
            item.row_index: item
            for item in ctx.sequence_viewer.sequence_items
            if item.isVisible()
        }
        row_ranges_map: dict = {}
        per_row_indices: set = set()
        for ann, row_index in self._state.selected_annotations:
            if row_index is None:
                for i in range(n):
                    row_ranges_map.setdefault(i, []).append((ann.start, ann.end))
            elif 0 <= row_index < n:
                per_row_indices.add(row_index)
                row_ranges_map.setdefault(row_index, []).append((ann.start, ann.end))

        for row_index, ranges in row_ranges_map.items():
            item = pool_by_row.get(row_index)
            if item is None:
                continue
            if len(ranges) == 1:
                item.set_selection(ranges[0][0], ranges[0][1])
            else:
                item.set_multi_selection(ranges)
        ctx.sequence_viewer.scene.invalidate()
        ctx.sequence_viewer.viewport().update()

        boundaries: list = []
        focus_ranges: list = []
        for ann, _ in self._state.selected_annotations:
            for boundary in self._annotation_guide_boundaries(ann):
                if boundary not in boundaries:
                    boundaries.append(boundary)
            focus_ranges.append(self._annotation_focus_range(ann))
        for ann in cr_anns:
            for boundary in self._annotation_guide_boundaries(ann):
                if boundary not in boundaries:
                    boundaries.append(boundary)
            focus_ranges.append(self._annotation_focus_range(ann))
        boundaries.sort()

        ctx.sequence_viewer.set_v_guides(boundaries)
        if focus_ranges:
            ctx.sequence_viewer.set_selection_focus_ranges(focus_ranges)

        if per_row_indices:
            ctx.sequence_viewer.set_h_guides(frozenset(per_row_indices))
        else:
            ctx.sequence_viewer.clear_h_guides()
        changed = ctx.header_viewer.clear_selection()
        for row_index in per_row_indices:
            changed = changed | ctx.header_viewer.toggle_row(row_index, n)
        ctx.header_viewer.apply_selection_to_items(changed)

    # Annotation layer click handler'lari

    def on_annotation_layer_clicked(self, annotation) -> None:
        from PyQt5.QtWidgets import QApplication

        action = mouse_binding_manager.resolve_annotation_click(QApplication.keyboardModifiers())
        is_multi = action == MouseAction.ANNOTATION_MULTI_SELECT
        if is_multi:
            existing = next(
                (
                    i
                    for i, (a, _) in enumerate(self._state.selected_annotations)
                    if a.id == annotation.id
                ),
                -1,
            )
            if existing >= 0:
                self._state.selected_annotations.pop(existing)
            else:
                self._state.selected_annotations.append((annotation, None))
            self._ctx.annotation_layer.set_selected_annotation(annotation.id, ctrl=True)
            self.apply_union_selection()
            return
        self._ctx.consensus_row.clear_selection()
        self._state.selected_annotations = [(annotation, None)]
        self._update_selection_visuals(annotation.id, is_layer=True)
        self._ctx.root_widget.setFocus()
        boundaries = self._annotation_guide_boundaries(annotation)
        self._ctx.sequence_viewer.set_v_guides(boundaries)
        focus_start, focus_end = self._annotation_focus_range(annotation)
        self._ctx.sequence_viewer.set_selection_dim_range(focus_start, focus_end)
        n = self._ctx.model.row_count()
        if n > 0:
            self._ctx.sequence_viewer.set_visual_selection(0, n - 1, focus_start, focus_end - 1)
            self._ctx.sequence_viewer.start_selection(0, focus_start)
            self._ctx.sequence_viewer.update_selection(n - 1, focus_end - 1)
            self._ctx.sequence_viewer.show_info_panel(0, n - 1, focus_start, focus_end - 1)

    def on_annotation_layer_double_clicked(self, annotation) -> None:
        if annotation.type == AnnotationType.MISMATCH_MARKER:
            return
        self._ctx.action_dialogs.do_edit_dialog(annotation, row_index=None)

    # Per-row annotation item click handler'lari

    def on_ann_item_clicked(self, annotation, row_index) -> None:
        from PyQt5.QtWidgets import QApplication

        ctx = self._ctx
        action = mouse_binding_manager.resolve_annotation_click(QApplication.keyboardModifiers())
        is_multi = action == MouseAction.ANNOTATION_MULTI_SELECT
        if is_multi:
            ctx.sequence_viewer.clear_caret()
            existing = next(
                (
                    i
                    for i, (a, _) in enumerate(self._state.selected_annotations)
                    if a.id == annotation.id
                ),
                -1,
            )
            if existing >= 0:
                self._state.selected_annotations.pop(existing)
            else:
                self._state.selected_annotations.append((annotation, row_index))
            ctx.annotation_presentation.set_selected_annotation(annotation.id, ctrl=True)
            self.apply_union_selection()
            return
        ctx.consensus_row.clear_selection()
        ctx.sequence_viewer.clear_caret()
        self._state.selected_annotations = [(annotation, row_index)]
        self._update_selection_visuals(annotation.id, is_layer=False)
        ctx.root_widget.setFocus()
        n = ctx.model.row_count()

        clear_changed = ctx.header_viewer.clear_selection()
        if 0 <= row_index < n:
            click_changed = ctx.header_viewer.select_row(row_index, n)
            ctx.header_viewer.apply_selection_to_items(clear_changed | click_changed)
        else:
            ctx.header_viewer.apply_selection_to_items(clear_changed)

        ctx.consensus_spacer.set_selected(False)
        ctx.consensus_row.clear_selection()

        if 0 <= row_index < n:
            ctx.sequence_viewer.set_h_guides(frozenset({row_index}))
        else:
            ctx.sequence_viewer.clear_h_guides()

        boundaries = self._annotation_guide_boundaries(annotation)
        ctx.sequence_viewer.set_v_guides(boundaries)
        focus_start, focus_end = self._annotation_focus_range(annotation)
        ctx.sequence_viewer.set_selection_dim_range(focus_start, focus_end)

        if 0 <= row_index < n:
            ctx.sequence_viewer.set_visual_selection(row_index, row_index, focus_start, focus_end - 1)
            ctx.sequence_viewer.start_selection(row_index, focus_start)
            ctx.sequence_viewer.update_selection(row_index, focus_end - 1)
            ctx.sequence_viewer.show_info_panel(row_index, row_index, focus_start, focus_end - 1)

    def on_ann_item_double_clicked(self, annotation, _row_index) -> None:
        if annotation.type == AnnotationType.MISMATCH_MARKER:
            return
        self._ctx.action_dialogs.open_edit_annotation_dialog(annotation)
