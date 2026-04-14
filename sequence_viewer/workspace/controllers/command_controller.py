# sequence_viewer/workspace/controllers/command_controller.py
from __future__ import annotations

from PyQt5.QtCore import Qt

from sequence_viewer.model.undo_stack import ModelSnapshotCommand


class WorkspaceCommandController:
    """Handles delete/undo command flows and interaction-state resets."""

    def __init__(self, workspace, undo_stack):
        self.workspace = workspace
        self.undo_stack = undo_stack

    def handle_keypress(self, event) -> bool:
        ctrl = bool(event.modifiers() & Qt.ControlModifier)
        shift = bool(event.modifiers() & Qt.ShiftModifier)
        if ctrl and not shift and event.key() == Qt.Key_Z:
            if self.undo_stack.undo():
                event.accept()
                return True
        if ctrl and shift and event.key() == Qt.Key_C:
            self.workspace._copy_fasta()
            event.accept()
            return True
        if ctrl and not shift and event.key() == Qt.Key_C:
            self.workspace._copy_sequences()
            event.accept()
            return True
        if event.key() == Qt.Key_Delete:
            has_coord = bool(self.workspace._action_dialogs._selected_annotations)
            has_cons = bool(self.workspace.consensus_row._selected_ann_ids)
            if has_coord or has_cons:
                if has_coord:
                    self.workspace._action_dialogs.delete_selected_annotation()
                if has_cons:
                    self.workspace.consensus_row.delete_selected_annotations()
                event.accept()
                return True
        return False

    def clear_interaction_state(self) -> None:
        ws = self.workspace
        ws._action_dialogs._selected_annotations.clear()
        ws._annotation_presentation.clear_annotation_selection()
        ws.annotation_layer.clear_annotation_selection()
        ws.sequence_viewer.clear_visual_selection()
        try:
            ws.sequence_viewer._model.clear_selection()
        except Exception:
            pass
        ws.sequence_viewer.clear_h_guides()
        ws.sequence_viewer.clear_v_guides()
        ws.sequence_viewer.clear_selection_dim_range()
        changed = ws.header_viewer._selection.clear()
        ws.header_viewer.apply_selection_to_items(changed)
        ws.consensus_spacer.set_selected(False)
        ws.consensus_row.clear_selection()

    def push_delete_command(self, text: str, mutate) -> None:
        self.undo_stack.push(
            ModelSnapshotCommand(
                text=text,
                model=self.workspace.model,
                mutate=mutate,
                after_restore=self.clear_interaction_state,
            )
        )

    def delete_rows_with_undo(self, rows) -> None:
        rows = sorted(set(rows), reverse=True)
        if not rows:
            return

        def mutate():
            for row in rows:
                try:
                    self.workspace.header_viewer._selection.remove_row(row)
                    self.workspace.model.remove_row(row)
                except IndexError:
                    pass

        self.push_delete_command("Delete rows", mutate)

    def delete_annotations_with_undo(self, annotations) -> None:
        to_delete = list(annotations)
        if not to_delete:
            return

        def mutate():
            ws = self.workspace
            ws._action_dialogs._selected_annotations.clear()
            ws._action_dialogs._clear_all_annotation_visuals()
            ws.sequence_viewer.clear_visual_selection()
            try:
                ws.sequence_viewer._model.clear_selection()
            except Exception:
                pass
            ws.sequence_viewer.clear_h_guides()
            ws.sequence_viewer.clear_v_guides()
            ws.sequence_viewer.clear_selection_dim_range()
            for ann, row_index in to_delete:
                try:
                    if row_index is None:
                        ws.model.remove_global_annotation(ann.id)
                    else:
                        ws.model.remove_annotation(row_index, ann.id)
                except (KeyError, IndexError):
                    pass

        self.push_delete_command("Delete annotations", mutate)

    def delete_consensus_annotations_with_undo(self, annotation_ids) -> None:
        ann_ids = list(annotation_ids)
        if not ann_ids:
            return

        def mutate():
            ws = self.workspace
            ws.consensus_row._selected_ann_ids.clear()
            ws.consensus_row._selection_ranges = []
            ws.consensus_row._is_selected = False
            ws.consensus_spacer.set_selected(False)
            ws.sequence_viewer.clear_selection_dim_range()
            ctrl = getattr(ws.sequence_viewer, "_controller", None)
            if ctrl is not None:
                ctrl._v_guide_cols = []
            ws.sequence_viewer.set_v_guides([])
            ws.consensus_row.update()
            for ann_id in ann_ids:
                try:
                    ws.model.remove_consensus_annotation(ann_id)
                except (KeyError, Exception):
                    pass

        self.push_delete_command("Delete consensus annotations", mutate)

