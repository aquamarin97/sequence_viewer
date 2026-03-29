from __future__ import annotations

from typing import FrozenSet, Optional, TYPE_CHECKING

from model.annotation import Annotation

if TYPE_CHECKING:
    from widgets.workspace import SequenceWorkspaceWidget


class WorkspaceActionDialogCoordinator:
    def __init__(self, workspace: "SequenceWorkspaceWidget"):
        self.workspace = workspace

    def on_annotation_layer_clicked(self, annotation: Annotation):
        self.workspace.sequence_viewer.set_guide_cols(annotation.start, annotation.end)
        n = self.workspace.model.row_count()
        if n > 0:
            self.workspace.sequence_viewer.set_visual_selection(0, n - 1, annotation.start, annotation.end)
            self.workspace.sequence_viewer._model.start_selection(0, annotation.start)
            self.workspace.sequence_viewer._model.update_selection(n - 1, annotation.end)

    def on_annotation_layer_double_clicked(self, annotation: Annotation):
        self.do_edit_dialog(annotation, row_index=None)

    def on_ann_item_clicked(self, annotation: Annotation, row_index: int):
        self.workspace.sequence_viewer.set_guide_cols(annotation.start, annotation.end)
        n = self.workspace.model.row_count()
        if 0 <= row_index < n:
            self.workspace.sequence_viewer.set_visual_selection(row_index, row_index, annotation.start, annotation.end)
            self.workspace.sequence_viewer._model.start_selection(row_index, annotation.start)
            self.workspace.sequence_viewer._model.update_selection(row_index, annotation.end)

    def on_ann_item_double_clicked(self, annotation: Annotation, _row_index: int):
        self.workspace.open_edit_annotation_dialog(annotation)

    def open_find_motifs_dialog(self):
        from features.dialogs.find_motifs_dialog import FindMotifsDialog

        FindMotifsDialog(model=self.workspace.model, parent=self.workspace).exec_()

    def open_edit_annotation_dialog(self, annotation: Annotation):
        result = self.workspace.model.find_annotation(annotation.id)
        if result is None:
            return
        row_index, _ = result
        self.do_edit_dialog(annotation, row_index=row_index)

    def do_edit_dialog(self, annotation: Annotation, row_index: Optional[int]):
        from features.dialogs.edit_annotation_dialog import EditAnnotationDialog

        dlg = EditAnnotationDialog(annotation=annotation, parent=self.workspace)
        if dlg.exec_() == EditAnnotationDialog.Accepted:
            updated = dlg.result_annotation()
            if updated is None:
                return
            try:
                if row_index is not None:
                    self.workspace.model.update_annotation(row_index, updated)
                else:
                    self.workspace.model.update_global_annotation(updated)
            except (KeyError, IndexError):
                pass

    def on_header_edited(self, row_index, new_text):
        try:
            self.workspace.model.set_header(row_index, new_text)
        except IndexError:
            pass

    def on_row_move_requested(self, from_index, to_index):
        try:
            self.workspace.model.move_row(from_index, to_index)
        except IndexError:
            pass

    def on_rows_delete_requested(self, rows: FrozenSet[int]):
        for row in sorted(rows, reverse=True):
            try:
                self.workspace.header_viewer._selection.remove_row(row)
                self.workspace.model.remove_row(row)
            except IndexError:
                pass

    def on_selection_changed(self, selected_rows):
        if not selected_rows:
            self.workspace.sequence_viewer.clear_h_guides()
        else:
            self.workspace.sequence_viewer.set_h_guides(frozenset(selected_rows))

    def on_row_appended(self, index, header, sequence):
        self.workspace.header_viewer.add_header_item(f"{index + 1}. {header}")
        self.workspace.sequence_viewer.add_sequence(sequence)
        self.workspace.ruler.update()
        self.workspace._update_header_max_width()
        layout = self.workspace._compute_row_layout()
        self.workspace._apply_layout(layout)
        self.workspace._rebuild_ann_items(layout)

    def on_row_removed(self, _index):
        self.rebuild_views()

    def on_row_moved(self, from_index, to_index):
        self.workspace.header_viewer._selection.move_row(from_index, to_index)
        self.rebuild_views()

    def on_header_changed(self, index, new_header):
        if index < 0 or index >= len(self.workspace.header_viewer.header_items):
            return
        self.workspace.header_viewer.header_items[index]._model.full_text = f"{index + 1}. {new_header}"
        self.workspace.header_viewer.header_items[index].update()
        self.workspace._update_header_max_width()

    def on_model_reset(self):
        self.rebuild_views()

    def rebuild_views(self):
        h_scroll = self.workspace.sequence_viewer.horizontalScrollBar().value()
        v_scroll = self.workspace.sequence_viewer.verticalScrollBar().value()

        self.workspace._remove_all_ann_items()
        self.workspace.header_viewer.clear()
        self.workspace.sequence_viewer.clear()

        for i, (header, sequence) in enumerate(self.workspace.model.all_rows()):
            item = self.workspace.header_viewer.add_header_item(f"{i + 1}. {header}")
            item.set_row_index(i)
            if self.workspace.header_viewer._selection.is_selected(i):
                item.set_selected(True)
            self.workspace.sequence_viewer.add_sequence(sequence)

        layout = self.workspace._compute_row_layout()
        self.workspace._apply_layout(layout)
        self.workspace.ruler.update()
        self.workspace._update_header_max_width()
        self.workspace._rebuild_ann_items(layout)

        self.workspace.sequence_viewer.horizontalScrollBar().setValue(h_scroll)
        self.workspace.sequence_viewer.verticalScrollBar().setValue(v_scroll)
