from __future__ import annotations

# sequence_viewer/workspace/coordinators/action_dialog.py

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sequence_viewer.workspace.context import WorkspaceContext

logger = logging.getLogger(__name__)


class WorkspaceActionDialogCoordinator:
    def __init__(self, ctx: "WorkspaceContext") -> None:
        self._ctx = ctx

    # Consensus annotation

    def on_consensus_annotation_double_clicked(self, annotation) -> None:
        from sequence_viewer.dialogs.edit_annotation_dialog import EditAnnotationDialog

        dlg = EditAnnotationDialog(annotation=annotation, parent=self._ctx.root_widget)
        if dlg.exec_() == EditAnnotationDialog.Accepted:
            updated = dlg.result_annotation()
            if updated is None:
                return
            try:
                self._ctx.model.update_consensus_annotation(updated)
            except Exception as e:
                logger.warning("Consensus annotation update failed: %s", e)

    # Dialog acma

    def open_find_motifs_dialog(self) -> None:
        from sequence_viewer.dialogs.find_motifs_dialog import FindMotifsDialog

        FindMotifsDialog(model=self._ctx.model, parent=self._ctx.root_widget).exec_()

    def open_edit_annotation_dialog(self, annotation) -> None:
        result = self._ctx.model.find_annotation(annotation.id)
        if result is None:
            return
        row_index, _ = result
        self.do_edit_dialog(annotation, row_index=row_index)

    def do_edit_dialog(self, annotation, row_index=None) -> None:
        from sequence_viewer.dialogs.edit_annotation_dialog import EditAnnotationDialog

        dlg = EditAnnotationDialog(annotation=annotation, parent=self._ctx.root_widget)
        if dlg.exec_() == EditAnnotationDialog.Accepted:
            updated = dlg.result_annotation()
            if updated is None:
                return
            try:
                if row_index is not None:
                    self._ctx.model.update_annotation(row_index, updated)
                else:
                    self._ctx.model.update_global_annotation(updated)
            except Exception as e:
                logger.warning("Annotation update failed: %s", e)

    # Header & model event handler'lari

    def on_header_edited(self, row_index: int, new_text: str) -> None:
        try:
            self._ctx.model.set_header(row_index, new_text)
        except IndexError:
            pass

    def on_row_move_requested(self, from_index: int, to_index: int) -> None:
        try:
            self._ctx.model.move_row(from_index, to_index)
        except IndexError:
            pass

    def on_rows_delete_requested(self, rows) -> None:
        self._ctx.command_controller.delete_rows_with_undo(rows)

    def on_row_appended(self, index: int, header: str) -> None:
        ctx = self._ctx
        ctx.header_viewer.add_header(header)
        ctx.sequence_viewer.add_sequence(ctx.model.get_record(index).sequence)
        ctx.ruler.update()
        ctx.layout_sync.update_header_max_width()
        layout = ctx.layout_sync.compute_row_layout()
        ctx.layout_sync.apply_layout(layout)
        ctx.annotation_presentation.rebuild_ann_items(layout)

    def on_row_removed(self, index: int) -> None:
        ctx = self._ctx
        ctx.header_viewer.remove_header_item(index)
        ctx.sequence_viewer.remove_sequence(index)
        ctx.header_viewer.renumber_from(index)
        layout = ctx.layout_sync.compute_row_layout()
        ctx.layout_sync.apply_layout(layout)
        ctx.annotation_presentation.rebuild_ann_items(layout)
        ctx.layout_sync.update_header_max_width()
        selected_rows = ctx.header_viewer.selected_rows()
        if selected_rows:
            ctx.sequence_viewer.set_h_guides(frozenset(selected_rows))
        else:
            ctx.sequence_viewer.clear_h_guides()
        ctx.ruler.update()

    def on_row_moved(self, from_index: int, to_index: int) -> None:
        ctx = self._ctx
        ctx.header_viewer.move_header_item(from_index, to_index)
        ctx.sequence_viewer.move_sequence(from_index, to_index)
        ctx.header_viewer.renumber_from(min(from_index, to_index))
        layout = ctx.layout_sync.compute_row_layout()
        ctx.layout_sync.apply_layout(layout)
        ctx.annotation_presentation.rebuild_ann_items(layout)
        selected_rows = ctx.header_viewer.selected_rows()
        if selected_rows:
            ctx.sequence_viewer.set_h_guides(frozenset(selected_rows))
        else:
            ctx.sequence_viewer.clear_h_guides()

    def on_header_changed(self, index: int, new_header: str) -> None:
        ctx = self._ctx
        try:
            ctx.header_viewer.set_header_item_text(index, f"{index + 1}. {new_header}")
        except IndexError:
            return
        ctx.layout_sync.update_header_max_width()

    def on_model_reset(self) -> None:
        self.rebuild_views()

    # View yeniden insasi

    def rebuild_views(self) -> None:
        ctx = self._ctx
        h_scroll = ctx.sequence_viewer.horizontalScrollBar().value()
        v_scroll = ctx.sequence_viewer.verticalScrollBar().value()
        ctx.annotation_presentation.remove_all_ann_items()
        ctx.header_viewer.clear()
        ctx.sequence_viewer.clear()
        for record in ctx.model.all_records():
            ctx.header_viewer.add_header(record.header)
            ctx.sequence_viewer.add_sequence(record.sequence)
        layout = ctx.layout_sync.compute_row_layout()
        ctx.layout_sync.apply_layout(layout)
        ctx.ruler.update()
        ctx.layout_sync.update_header_max_width()
        ctx.annotation_presentation.rebuild_ann_items(layout)
        ctx.sequence_viewer.horizontalScrollBar().setValue(h_scroll)
        ctx.sequence_viewer.verticalScrollBar().setValue(v_scroll)
        selected_rows = ctx.header_viewer.selected_rows()
        if selected_rows:
            ctx.sequence_viewer.set_h_guides(frozenset(selected_rows))
        else:
            ctx.sequence_viewer.clear_h_guides()
