from __future__ import annotations
from typing import FrozenSet, Optional, TYPE_CHECKING
from model.annotation import Annotation
if TYPE_CHECKING:
    from widgets.workspace import SequenceWorkspaceWidget

class WorkspaceActionDialogCoordinator:
    def __init__(self, workspace): self.workspace = workspace

    def on_annotation_layer_clicked(self, annotation):
        self.workspace.sequence_viewer.set_guide_cols(annotation.start, annotation.end)
        n = self.workspace.model.row_count()
        if n > 0:
            self.workspace.sequence_viewer.set_visual_selection(0, n-1, annotation.start, annotation.end)
            self.workspace.sequence_viewer._model.start_selection(0, annotation.start)
            self.workspace.sequence_viewer._model.update_selection(n-1, annotation.end)

    def on_annotation_layer_double_clicked(self, annotation):
        self.do_edit_dialog(annotation, row_index=None)

    def on_ann_item_clicked(self, annotation, row_index):
        ws = self.workspace
        n = ws.model.row_count()

        # Header seçimini temizle + row_index'i vurgula (on_selection_changed tetiklenmeden)
        clear_changed = ws.header_viewer._selection.clear()
        if 0 <= row_index < n:
            click_changed = ws.header_viewer._selection.handle_click(row_index, n)
            ws.header_viewer.apply_selection_to_items(clear_changed | click_changed)
        else:
            ws.header_viewer.apply_selection_to_items(clear_changed)

        # Consensus row/spacer temizle
        ws.consensus_spacer.set_selected(False)
        ws.consensus_row.clear_selection()

        # H-guide: annotation satırını vurgula (bant + üst/alt çizgi)
        if 0 <= row_index < n:
            ws.sequence_viewer.set_h_guides(frozenset({row_index}))
        else:
            ws.sequence_viewer.clear_h_guides()

        # V-guide: annotation sütun aralığı
        ws.sequence_viewer.set_guide_cols(annotation.start, annotation.end)

        # Görsel seçim: sadece annotation sütun aralığı
        if 0 <= row_index < n:
            ws.sequence_viewer.set_visual_selection(row_index, row_index, annotation.start, annotation.end)
            ws.sequence_viewer._model.start_selection(row_index, annotation.start)
            ws.sequence_viewer._model.update_selection(row_index, annotation.end)

    def on_ann_item_double_clicked(self, annotation, _row_index):
        self.workspace.open_edit_annotation_dialog(annotation)

    def on_consensus_annotation_double_clicked(self, annotation):
        from features.dialogs.edit_annotation_dialog import EditAnnotationDialog
        dlg = EditAnnotationDialog(annotation=annotation, parent=self.workspace)
        if dlg.exec_() == EditAnnotationDialog.Accepted:
            updated = dlg.result_annotation()
            if updated is None: return
            try:
                self.workspace.model.update_consensus_annotation(updated)
            except Exception:
                pass

    def open_find_motifs_dialog(self):
        from features.dialogs.find_motifs_dialog import FindMotifsDialog
        FindMotifsDialog(model=self.workspace.model, parent=self.workspace).exec_()

    def open_edit_annotation_dialog(self, annotation):
        result = self.workspace.model.find_annotation(annotation.id)
        if result is None: return
        row_index, _ = result
        self.do_edit_dialog(annotation, row_index=row_index)

    def do_edit_dialog(self, annotation, row_index=None):
        from features.dialogs.edit_annotation_dialog import EditAnnotationDialog
        dlg = EditAnnotationDialog(annotation=annotation, parent=self.workspace)
        if dlg.exec_() == EditAnnotationDialog.Accepted:
            updated = dlg.result_annotation()
            if updated is None: return
            try:
                if row_index is not None: self.workspace.model.update_annotation(row_index, updated)
                else: self.workspace.model.update_global_annotation(updated)
            except: pass

    def on_header_edited(self, row_index, new_text):
        try: self.workspace.model.set_header(row_index, new_text)
        except IndexError: pass

    def on_row_move_requested(self, from_index, to_index):
        try: self.workspace.model.move_row(from_index, to_index)
        except IndexError: pass

    def on_rows_delete_requested(self, rows):
        for row in sorted(rows, reverse=True):
            try:
                self.workspace.header_viewer._selection.remove_row(row)
                self.workspace.model.remove_row(row)
            except IndexError: pass

    def on_selection_changed(self, selected_rows):
        # Herhangi bir header seçilince consensus vurgusunu, seçimini ve guide'ları kaldır
        self.workspace.consensus_spacer.set_selected(False)
        self.workspace.consensus_row.clear_selection()
        self.workspace.sequence_viewer.clear_v_guides()
        if not selected_rows:
            self.workspace.sequence_viewer.clear_h_guides()
        else:
            self.workspace.sequence_viewer.set_h_guides(frozenset(selected_rows))
            # Header seçildiğinde ilgili satırların dizilerini de seçili yap
            n = self.workspace.model.row_count()
            max_len = self.workspace.model.max_sequence_length
            if n > 0 and max_len > 0:
                rows = sorted(selected_rows)
                # Tüm satırların tüm kolonlarını seçili yap
                for i, item in enumerate(self.workspace.sequence_viewer.sequence_items):
                    if i in selected_rows:
                        item.set_selection(0, max_len)
                    else:
                        item.clear_selection()
                self.workspace.sequence_viewer.scene.invalidate()
                self.workspace.sequence_viewer.viewport().update()

    def on_seq_row_clicked(self, row_start, row_end):
        """Sequence view'da satır(lar)a tıklanınca: header highlight + h-guide, full selection yok."""
        ws = self.workspace
        n = ws.model.row_count()
        rows = frozenset(range(row_start, row_end + 1)) if 0 <= row_start < n else frozenset()

        # Header seçimini temizle + seçili satırları görsel olarak işaretle
        # (on_selection_changed tetiklenmez → full sequence selection yapılmaz)
        clear_changed = ws.header_viewer._selection.clear()
        click_changed: frozenset = frozenset()
        if rows:
            for r in rows:
                click_changed = click_changed | ws.header_viewer._selection.handle_ctrl_click(r, n)
        ws.header_viewer.apply_selection_to_items(clear_changed | click_changed)

        # Consensus state temizle
        ws.consensus_spacer.set_selected(False)
        ws.consensus_row.clear_selection()

        # H-guide: seçili satırların tamamı
        if rows:
            ws.sequence_viewer.set_h_guides(rows)
        else:
            ws.sequence_viewer.clear_h_guides()

    def on_row_appended(self, index, header, sequence):
        self.workspace.header_viewer.add_header_item(f"{index + 1}. {header}")
        self.workspace.sequence_viewer.add_sequence(sequence)
        self.workspace.ruler.update()
        self.workspace._update_header_max_width()
        layout = self.workspace._compute_row_layout()
        self.workspace._apply_layout(layout)
        self.workspace._rebuild_ann_items(layout)

    def on_row_removed(self, _index): self.rebuild_views()
    def on_row_moved(self, from_index, to_index):
        self.workspace.header_viewer._selection.move_row(from_index, to_index)
        self.rebuild_views()

    def on_header_changed(self, index, new_header):
        if index < 0 or index >= len(self.workspace.header_viewer.header_items): return
        self.workspace.header_viewer.header_items[index]._model.full_text = f"{index + 1}. {new_header}"
        self.workspace.header_viewer.header_items[index].update()
        self.workspace._update_header_max_width()

    def on_model_reset(self): self.rebuild_views()

    def on_consensus_spacer_clicked(self):
        """Consensus spacer'a tıklama → seçim vurgusu + consensus dizisini tümüyle seçer."""
        ws = self.workspace
        # Header seçimini temizle — ama on_selection_changed'i tetikleme
        # (o fonksiyon consensus_spacer.set_selected(False) yapıyor)
        changed = ws.header_viewer._selection.clear()
        ws.header_viewer.apply_selection_to_items(changed)
        ws.sequence_viewer.clear_h_guides()
        ws.sequence_viewer.clear_v_guides()
        ws.sequence_viewer.clear_visual_selection()
        try: ws.sequence_viewer._model.clear_selection()
        except: pass
        # Şimdi consensus'u seçili yap
        ws.consensus_spacer.set_selected(True)
        ws.consensus_spacer.setFocus()
        ws.consensus_row.set_selected(True)
        ws.consensus_row.select_all()

    def rebuild_views(self):
        h_scroll = self.workspace.sequence_viewer.horizontalScrollBar().value()
        v_scroll = self.workspace.sequence_viewer.verticalScrollBar().value()
        self.workspace._remove_all_ann_items()
        self.workspace.header_viewer.clear(); self.workspace.sequence_viewer.clear()
        for i, (header, sequence) in enumerate(self.workspace.model.all_rows()):
            item = self.workspace.header_viewer.add_header_item(f"{i + 1}. {header}")
            item.set_row_index(i)
            if self.workspace.header_viewer._selection.is_selected(i): item.set_selected(True)
            self.workspace.sequence_viewer.add_sequence(sequence)
        layout = self.workspace._compute_row_layout()
        self.workspace._apply_layout(layout)
        self.workspace.ruler.update()
        self.workspace._update_header_max_width()
        self.workspace._rebuild_ann_items(layout)
        self.workspace.sequence_viewer.horizontalScrollBar().setValue(h_scroll)
        self.workspace.sequence_viewer.verticalScrollBar().setValue(v_scroll)