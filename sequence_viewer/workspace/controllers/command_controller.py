# sequence_viewer/workspace/controllers/command_controller.py
from __future__ import annotations

from typing import TYPE_CHECKING

from sequence_viewer.model.undo_stack import ModelSnapshotCommand
from sequence_viewer.workspace.controllers.state_cleaner import WorkspaceStateCleaner

if TYPE_CHECKING:
    from sequence_viewer.workspace.context import WorkspaceContext


class WorkspaceCommandController:
    """Silme/undo komut akışlarını ve etkileşim state sıfırlamalarını yönetir."""

    def __init__(self, ctx: "WorkspaceContext") -> None:
        self._ctx = ctx
        self._state_cleaner = WorkspaceStateCleaner(ctx)

    # ── Undo altyapısı ───────────────────────────────────────────────────

    def push_delete_command(self, text: str, mutate) -> None:
        self._ctx.undo_stack.push(
            ModelSnapshotCommand(
                text=text,
                model=self._ctx.model,
                mutate=mutate,
                after_restore=self._state_cleaner.clear_all_interaction_state,
            )
        )

    # ── Row silme ────────────────────────────────────────────────────────

    def delete_rows_with_undo(self, rows) -> None:
        rows = sorted(set(rows), reverse=True)
        if not rows:
            return
        self.push_delete_command("Delete rows", lambda: self._mutate_delete_rows(rows))

    def _mutate_delete_rows(self, rows) -> None:
        for row in rows:
            try:
                self._ctx.header_viewer.deselect_row(row)
                self._ctx.model.remove_row(row)
            except IndexError:
                pass

    # ── Annotation silme ─────────────────────────────────────────────────

    def delete_annotations_with_undo(self, annotations) -> None:
        to_delete = list(annotations)
        if not to_delete:
            return
        self.push_delete_command(
            "Delete annotations", lambda: self._mutate_delete_annotations(to_delete)
        )

    def _mutate_delete_annotations(self, to_delete) -> None:
        self._state_cleaner.clear_annotation_delete_state()
        for ann, row_index in to_delete:
            try:
                if row_index is None:
                    self._ctx.model.remove_global_annotation(ann.id)
                else:
                    self._ctx.model.remove_annotation(row_index, ann.id)
            except (KeyError, IndexError):
                pass

    # ── Consensus annotation silme ───────────────────────────────────────

    def delete_consensus_annotations_with_undo(self, annotation_ids) -> None:
        ann_ids = list(annotation_ids)
        if not ann_ids:
            return
        self.push_delete_command(
            "Delete consensus annotations",
            lambda: self._mutate_delete_consensus_annotations(ann_ids),
        )

    def _mutate_delete_consensus_annotations(self, ann_ids) -> None:
        self._state_cleaner.clear_consensus_delete_state()
        for ann_id in ann_ids:
            try:
                self._ctx.model.remove_consensus_annotation(ann_id)
            except (KeyError, Exception):
                pass

