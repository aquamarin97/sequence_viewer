# widgets/workspace_action_dialog_coordinator.py
from __future__ import annotations
from typing import FrozenSet, Optional, TYPE_CHECKING
from model.annotation import Annotation
if TYPE_CHECKING:
    from widgets.workspace import SequenceWorkspaceWidget

class WorkspaceActionDialogCoordinator:
    def __init__(self, workspace):
        self.workspace = workspace
        self._selected_annotations: list = []  # [(annotation, row_index_or_None), ...]

    def _update_selection_visuals(self, ann_id, is_layer, ctrl=False):
        """Per-row ve layer annotation seçim görsellerini senkronize eder."""
        ws = self.workspace
        ws._annotation_presentation.set_selected_annotation(
            ann_id if not is_layer else None, ctrl=ctrl)
        ws.annotation_layer.set_selected_annotation(
            ann_id if is_layer else None, ctrl=ctrl)

    def _clear_all_annotation_visuals(self):
        """Tüm seçili annotation görsellerini ve dim overlay'ini temizler."""
        ws = self.workspace
        ws._annotation_presentation.clear_annotation_selection()
        ws.annotation_layer.clear_annotation_selection()
        ws.sequence_viewer.clear_selection_dim_range()

    def _apply_union_selection(self):
        """
        Coordinator'ın seçimlerini uygular. Consensus annotation'lar kendi widget'ında
        render edilir (regular sequence items'a yazılmaz). V-guide + dim için merge.
        """
        ws = self.workspace
        n = ws.model.row_count()
        ws.sequence_viewer.clear_visual_selection()
        try: ws.sequence_viewer._model.clear_selection()
        except: pass
        ws.sequence_viewer.clear_selection_dim_range()

        # Consensus row'un seçili annotation'larını sadece guide/dim hesabı için al
        cr = ws.consensus_row
        cr_ann_ids = set(getattr(cr, '_selected_ann_ids', set()))
        cr_anns: list = []
        if cr_ann_ids and getattr(ws.model, 'is_aligned', False):
            ann_map = {a.id: a for a in ws.model.consensus_annotations}
            cr_anns = [ann_map[aid] for aid in cr_ann_ids if aid in ann_map]

        has_any = bool(self._selected_annotations or cr_anns)
        if not has_any or n == 0:
            ws.sequence_viewer.clear_h_guides()
            clear_changed = ws.header_viewer._selection.clear()
            ws.header_viewer.apply_selection_to_items(clear_changed)
            return

        items = ws.sequence_viewer.sequence_items
        # Her satır için ayrı aralıkları topla — SADECE coordinator annotation'ları
        row_ranges_map: dict = {}  # row_index → [(start, end), ...]
        per_row_indices: set = set()
        for ann, row_index in self._selected_annotations:
            if row_index is None:
                for i in range(len(items)):
                    row_ranges_map.setdefault(i, []).append((ann.start, ann.end))
            elif 0 <= row_index < len(items):
                per_row_indices.add(row_index)
                row_ranges_map.setdefault(row_index, []).append((ann.start, ann.end))

        for row_index, ranges in row_ranges_map.items():
            if len(ranges) == 1:
                items[row_index].set_selection(ranges[0][0], ranges[0][1])
            else:
                items[row_index].set_multi_selection(ranges)
        ws.sequence_viewer.scene.invalidate()
        ws.sequence_viewer.viewport().update()

        # V-guide + focus: coordinator + consensus annotation sınırlarını birleştir
        boundaries: list = []
        focus_ranges: list = []
        for ann, _ in self._selected_annotations:
            if ann.start not in boundaries: boundaries.append(ann.start)
            if ann.end + 1 not in boundaries: boundaries.append(ann.end + 1)
            focus_ranges.append((ann.start, ann.end + 1))
        for ann in cr_anns:
            if ann.start not in boundaries: boundaries.append(ann.start)
            if ann.end + 1 not in boundaries: boundaries.append(ann.end + 1)
            focus_ranges.append((ann.start, ann.end + 1))
        boundaries.sort()

        # Controller güncellenmesi set_v_guides'dan ÖNCE olmalı
        seq_ctrl = ws.sequence_viewer._controller
        if seq_ctrl is not None:
            seq_ctrl._v_guide_cols = list(boundaries)
        ws.sequence_viewer.set_v_guides(boundaries)
        if focus_ranges:
            ws.sequence_viewer.set_selection_focus_ranges(focus_ranges)

        # H-guide: sadece per-row annotation satırları
        if per_row_indices:
            ws.sequence_viewer.set_h_guides(frozenset(per_row_indices))
        else:
            ws.sequence_viewer.clear_h_guides()
        # Header: per-row annotation satırlarını vurgula
        changed = ws.header_viewer._selection.clear()
        for ri in per_row_indices:
            changed = changed | ws.header_viewer._selection.handle_ctrl_click(ri, n)
        ws.header_viewer.apply_selection_to_items(changed)

    def on_annotation_layer_clicked(self, annotation):
        from PyQt5.QtWidgets import QApplication
        from PyQt5.QtCore import Qt as _Qt
        ctrl = bool(QApplication.keyboardModifiers() & _Qt.ControlModifier)
        if ctrl:
            existing = next((i for i, (a, _) in enumerate(self._selected_annotations)
                             if a.id == annotation.id), -1)
            if existing >= 0:
                self._selected_annotations.pop(existing)
            else:
                self._selected_annotations.append((annotation, None))
            self.workspace.annotation_layer.set_selected_annotation(annotation.id, ctrl=True)
            self._apply_union_selection()
            return
        # Non-ctrl tekil seçim: consensus row'u temizle
        self.workspace.consensus_row._selected_ann_ids.clear()
        self.workspace.consensus_row.update()
        self._selected_annotations = [(annotation, None)]
        self._update_selection_visuals(annotation.id, is_layer=True)
        self.workspace.setFocus()
        _boundaries = [annotation.start, annotation.end + 1]
        _seq_ctrl = self.workspace.sequence_viewer._controller
        if _seq_ctrl is not None:
            _seq_ctrl._v_guide_cols = list(_boundaries)
        self.workspace.sequence_viewer.set_v_guides(_boundaries)
        self.workspace.sequence_viewer.set_selection_dim_range(annotation.start, annotation.end + 1)
        n = self.workspace.model.row_count()
        if n > 0:
            self.workspace.sequence_viewer.set_visual_selection(0, n-1, annotation.start, annotation.end)
            self.workspace.sequence_viewer._model.start_selection(0, annotation.start)
            self.workspace.sequence_viewer._model.update_selection(n-1, annotation.end)

    def on_annotation_layer_double_clicked(self, annotation):
        self.do_edit_dialog(annotation, row_index=None)

    def on_ann_item_clicked(self, annotation, row_index):
        from PyQt5.QtWidgets import QApplication
        from PyQt5.QtCore import Qt as _Qt
        ctrl = bool(QApplication.keyboardModifiers() & _Qt.ControlModifier)
        if ctrl:
            existing = next((i for i, (a, _) in enumerate(self._selected_annotations)
                             if a.id == annotation.id), -1)
            if existing >= 0:
                self._selected_annotations.pop(existing)
            else:
                self._selected_annotations.append((annotation, row_index))
            self.workspace._annotation_presentation.set_selected_annotation(annotation.id, ctrl=True)
            self._apply_union_selection()
            return
        # Non-ctrl tekil seçim: consensus row'u temizle
        self.workspace.consensus_row._selected_ann_ids.clear()
        self.workspace.consensus_row.update()
        self._selected_annotations = [(annotation, row_index)]
        self._update_selection_visuals(annotation.id, is_layer=False)
        self.workspace.setFocus()
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
        _boundaries = [annotation.start, annotation.end + 1]
        _seq_ctrl = ws.sequence_viewer._controller
        if _seq_ctrl is not None:
            _seq_ctrl._v_guide_cols = list(_boundaries)
        ws.sequence_viewer.set_v_guides(_boundaries)
        ws.sequence_viewer.set_selection_dim_range(annotation.start, annotation.end + 1)

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
        from PyQt5.QtWidgets import QApplication
        from PyQt5.QtCore import Qt as _Qt
        ctrl = bool(QApplication.keyboardModifiers() & _Qt.ControlModifier)
        if self._selected_annotations:
            self._clear_all_annotation_visuals()
            self._selected_annotations.clear()
        # Consensus row: ctrl+click'te koru, non-ctrl'da temizle
        if not ctrl:
            self.workspace.consensus_spacer.set_selected(False)
            self.workspace.consensus_row.clear_selection()
        self.workspace.sequence_viewer.clear_v_guides()
        self.workspace.sequence_viewer.clear_selection_dim_range()
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
        if self._selected_annotations:
            self._clear_all_annotation_visuals()
            self._selected_annotations.clear()
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

    def delete_selected_annotation(self):
        """Seçili annotation'ları sil (Delete tuşu)."""
        if not self._selected_annotations:
            return
        to_delete = list(self._selected_annotations)
        self._selected_annotations.clear()
        self._clear_all_annotation_visuals()
        for ann, row_index in to_delete:
            try:
                if row_index is None:
                    self.workspace.model.remove_global_annotation(ann.id)
                else:
                    self.workspace.model.remove_annotation(row_index, ann.id)
            except (KeyError, IndexError):
                pass

    def on_consensus_spacer_clicked(self, ctrl=False):
        """Consensus spacer'a tıklama.
        ctrl=False: exclusive — header + annotation seçimlerini sıfırla, sadece consensus seç.
        ctrl=True:  additive  — header seçimlerini koru, consensus'u toggle et.
        """
        if self._selected_annotations:
            self._clear_all_annotation_visuals()
            self._selected_annotations.clear()
        ws = self.workspace
        # Annotation seçimini temizle (her iki modda da)
        ws.consensus_row._selected_ann_ids.clear()
        ws.sequence_viewer.clear_v_guides()
        ws.sequence_viewer.clear_selection_dim_range()
        if ctrl:
            # Additive: header seçimini koru, consensus'u toggle et
            if ws.consensus_spacer._selected:
                # Seçimi kaldır
                ws.consensus_spacer.set_selected(False)
                ws.consensus_row.clear_selection()
            else:
                # Ekle
                ws.consensus_spacer.set_selected(True)
                ws.consensus_spacer.setFocus()
                ws.consensus_row.set_selected(True)
                ws.consensus_row.select_all()
        else:
            # Exclusive: header seçimini temizle
            changed = ws.header_viewer._selection.clear()
            ws.header_viewer.apply_selection_to_items(changed)
            ws.sequence_viewer.clear_h_guides()
            ws.sequence_viewer.clear_visual_selection()
            try: ws.sequence_viewer._model.clear_selection()
            except: pass
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
        # clear() sırasında sıfırlanan h_guide'ları mevcut seçime göre yeniden uygula
        selected_rows = self.workspace.header_viewer._selection.selected_rows()
        if selected_rows:
            self.workspace.sequence_viewer.set_h_guides(frozenset(selected_rows))
        else:
            self.workspace.sequence_viewer.clear_h_guides()