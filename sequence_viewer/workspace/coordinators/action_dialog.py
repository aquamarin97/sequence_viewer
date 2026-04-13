from __future__ import annotations
from typing import FrozenSet, Optional, TYPE_CHECKING
from sequence_viewer.model.annotation import Annotation, AnnotationType
from sequence_viewer.settings.mouse_binding_manager import mouse_binding_manager, MouseAction
if TYPE_CHECKING:
    from sequence_viewer.workspace.workspace import SequenceWorkspaceWidget

class WorkspaceActionDialogCoordinator:
    def __init__(self, workspace):
        self.workspace = workspace
        self._selected_annotations: list = []  # [(annotation, row_index_or_None), ...]
        self._last_clicked_row: int = 0  # Shift+click anchor

    def _update_selection_visuals(self, ann_id, is_layer, ctrl=False):
        """Per-row ve layer annotation seÃ§im gÃ¶rsellerini senkronize eder."""
        ws = self.workspace
        ws._annotation_presentation.set_selected_annotation(
            ann_id if not is_layer else None, ctrl=ctrl)
        ws.annotation_layer.set_selected_annotation(
            ann_id if is_layer else None, ctrl=ctrl)

    @staticmethod
    def _annotation_focus_range(annotation):
        return (annotation.start, annotation.start + 1) if annotation.type == AnnotationType.MISMATCH_MARKER else (annotation.start, annotation.end + 1)

    @staticmethod
    def _annotation_guide_boundaries(annotation):
        return [annotation.start] if annotation.type == AnnotationType.MISMATCH_MARKER else [annotation.start, annotation.end + 1]

    def _clear_all_annotation_visuals(self):
        """TÃ¼m seÃ§ili annotation gÃ¶rsellerini ve dim overlay'ini temizler."""
        ws = self.workspace
        ws._annotation_presentation.clear_annotation_selection()
        ws.annotation_layer.clear_annotation_selection()
        ws.sequence_viewer.clear_selection_dim_range()

    def _apply_union_selection(self):
        """
        Coordinator'Ä±n seÃ§imlerini uygular. Consensus annotation'lar kendi widget'Ä±nda
        render edilir (regular sequence items'a yazÄ±lmaz). V-guide + dim iÃ§in merge.
        """
        ws = self.workspace
        n = ws.model.row_count()
        ws.sequence_viewer.clear_visual_selection()
        try: ws.sequence_viewer._model.clear_selection()
        except: pass
        ws.sequence_viewer.clear_selection_dim_range()

        # Consensus row'un seÃ§ili annotation'larÄ±nÄ± sadece guide/dim hesabÄ± iÃ§in al
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
        # Her satÄ±r iÃ§in ayrÄ± aralÄ±klarÄ± topla â€” SADECE coordinator annotation'larÄ±
        row_ranges_map: dict = {}  # row_index â†’ [(start, end), ...]
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

        # V-guide + focus: coordinator + consensus annotation sÄ±nÄ±rlarÄ±nÄ± birleÅŸtir
        boundaries: list = []
        focus_ranges: list = []
        for ann, _ in self._selected_annotations:
            for boundary in self._annotation_guide_boundaries(ann):
                if boundary not in boundaries: boundaries.append(boundary)
            focus_ranges.append(self._annotation_focus_range(ann))
        for ann in cr_anns:
            for boundary in self._annotation_guide_boundaries(ann):
                if boundary not in boundaries: boundaries.append(boundary)
            focus_ranges.append(self._annotation_focus_range(ann))
        boundaries.sort()

        # Controller gÃ¼ncellenmesi set_v_guides'dan Ã–NCE olmalÄ±
        seq_ctrl = ws.sequence_viewer._controller
        if seq_ctrl is not None:
            seq_ctrl._v_guide_cols = list(boundaries)
        ws.sequence_viewer.set_v_guides(boundaries)
        if focus_ranges:
            ws.sequence_viewer.set_selection_focus_ranges(focus_ranges)

        # H-guide: sadece per-row annotation satÄ±rlarÄ±
        if per_row_indices:
            ws.sequence_viewer.set_h_guides(frozenset(per_row_indices))
        else:
            ws.sequence_viewer.clear_h_guides()
        # Header: per-row annotation satÄ±rlarÄ±nÄ± vurgula
        changed = ws.header_viewer._selection.clear()
        for ri in per_row_indices:
            changed = changed | ws.header_viewer._selection.handle_ctrl_click(ri, n)
        ws.header_viewer.apply_selection_to_items(changed)

    def on_annotation_layer_clicked(self, annotation):
        from PyQt5.QtWidgets import QApplication
        action = mouse_binding_manager.resolve_annotation_click(QApplication.keyboardModifiers())
        is_multi = action == MouseAction.ANNOTATION_MULTI_SELECT
        if is_multi:
            existing = next((i for i, (a, _) in enumerate(self._selected_annotations)
                             if a.id == annotation.id), -1)
            if existing >= 0:
                self._selected_annotations.pop(existing)
            else:
                self._selected_annotations.append((annotation, None))
            self.workspace.annotation_layer.set_selected_annotation(annotation.id, ctrl=True)
            self._apply_union_selection()
            return
        # Non-ctrl tekil seÃ§im: consensus row'u temizle
        self.workspace.consensus_row.clear_selection()
        self._selected_annotations = [(annotation, None)]
        self._update_selection_visuals(annotation.id, is_layer=True)
        self.workspace.setFocus()
        _boundaries = self._annotation_guide_boundaries(annotation)
        _seq_ctrl = self.workspace.sequence_viewer._controller
        if _seq_ctrl is not None:
            _seq_ctrl._v_guide_cols = list(_boundaries)
        self.workspace.sequence_viewer.set_v_guides(_boundaries)
        focus_start, focus_end = self._annotation_focus_range(annotation)
        self.workspace.sequence_viewer.set_selection_dim_range(focus_start, focus_end)
        n = self.workspace.model.row_count()
        if n > 0:
            self.workspace.sequence_viewer.set_visual_selection(0, n-1, focus_start, focus_end - 1)
            self.workspace.sequence_viewer._model.start_selection(0, focus_start)
            self.workspace.sequence_viewer._model.update_selection(n-1, focus_end - 1)
            self.workspace.sequence_viewer.show_info_panel(0, n - 1, focus_start, focus_end - 1)

    def on_annotation_layer_double_clicked(self, annotation):
        if annotation.type == AnnotationType.MISMATCH_MARKER:
            return
        self.do_edit_dialog(annotation, row_index=None)

    def on_ann_item_clicked(self, annotation, row_index):
        from PyQt5.QtWidgets import QApplication
        action = mouse_binding_manager.resolve_annotation_click(QApplication.keyboardModifiers())
        is_multi = action == MouseAction.ANNOTATION_MULTI_SELECT
        if is_multi:
            self.workspace.sequence_viewer.clear_caret()
            existing = next((i for i, (a, _) in enumerate(self._selected_annotations)
                             if a.id == annotation.id), -1)
            if existing >= 0:
                self._selected_annotations.pop(existing)
            else:
                self._selected_annotations.append((annotation, row_index))
            self.workspace._annotation_presentation.set_selected_annotation(annotation.id, ctrl=True)
            self._apply_union_selection()
            return
        # Non-ctrl tekil seÃ§im: consensus row'u temizle
        self.workspace.consensus_row.clear_selection()
        self.workspace.sequence_viewer.clear_caret()
        self._selected_annotations = [(annotation, row_index)]
        self._update_selection_visuals(annotation.id, is_layer=False)
        self.workspace.setFocus()
        ws = self.workspace
        n = ws.model.row_count()

        # Header seÃ§imini temizle + row_index'i vurgula (on_selection_changed tetiklenmeden)
        clear_changed = ws.header_viewer._selection.clear()
        if 0 <= row_index < n:
            click_changed = ws.header_viewer._selection.handle_click(row_index, n)
            ws.header_viewer.apply_selection_to_items(clear_changed | click_changed)
        else:
            ws.header_viewer.apply_selection_to_items(clear_changed)

        # Consensus row/spacer temizle
        ws.consensus_spacer.set_selected(False)
        ws.consensus_row.clear_selection()

        # H-guide: annotation satÄ±rÄ±nÄ± vurgula (bant + Ã¼st/alt Ã§izgi)
        if 0 <= row_index < n:
            ws.sequence_viewer.set_h_guides(frozenset({row_index}))
        else:
            ws.sequence_viewer.clear_h_guides()

        # V-guide: annotation sÃ¼tun aralÄ±ÄŸÄ±
        _boundaries = self._annotation_guide_boundaries(annotation)
        _seq_ctrl = ws.sequence_viewer._controller
        if _seq_ctrl is not None:
            _seq_ctrl._v_guide_cols = list(_boundaries)
        ws.sequence_viewer.set_v_guides(_boundaries)
        focus_start, focus_end = self._annotation_focus_range(annotation)
        ws.sequence_viewer.set_selection_dim_range(focus_start, focus_end)

        # GÃ¶rsel seÃ§im: sadece annotation sÃ¼tun aralÄ±ÄŸÄ±
        if 0 <= row_index < n:
            ws.sequence_viewer.set_visual_selection(row_index, row_index, focus_start, focus_end - 1)
            ws.sequence_viewer._model.start_selection(row_index, focus_start)
            ws.sequence_viewer._model.update_selection(row_index, focus_end - 1)
            ws.sequence_viewer.show_info_panel(row_index, row_index, focus_start, focus_end - 1)

    def on_ann_item_double_clicked(self, annotation, _row_index):
        if annotation.type == AnnotationType.MISMATCH_MARKER:
            return
        self.workspace.open_edit_annotation_dialog(annotation)

    def on_consensus_annotation_double_clicked(self, annotation):
        from sequence_viewer.dialogs.edit_annotation_dialog import EditAnnotationDialog
        dlg = EditAnnotationDialog(annotation=annotation, parent=self.workspace)
        if dlg.exec_() == EditAnnotationDialog.Accepted:
            updated = dlg.result_annotation()
            if updated is None: return
            try:
                self.workspace.model.update_consensus_annotation(updated)
            except Exception:
                pass

    def open_find_motifs_dialog(self):
        from sequence_viewer.dialogs.find_motifs_dialog import FindMotifsDialog
        FindMotifsDialog(model=self.workspace.model, parent=self.workspace).exec_()

    def open_edit_annotation_dialog(self, annotation):
        result = self.workspace.model.find_annotation(annotation.id)
        if result is None: return
        row_index, _ = result
        self.do_edit_dialog(annotation, row_index=row_index)

    def do_edit_dialog(self, annotation, row_index=None):
        from sequence_viewer.dialogs.edit_annotation_dialog import EditAnnotationDialog
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
        self.workspace.delete_rows_with_undo(rows)

    def on_selection_changed(self, selected_rows):
        from PyQt5.QtWidgets import QApplication
        header_action = mouse_binding_manager.resolve_header_click(QApplication.keyboardModifiers())
        is_multi = header_action == MouseAction.ROW_MULTI_SELECT
        if self._selected_annotations:
            self._clear_all_annotation_visuals()
            self._selected_annotations.clear()
        # Consensus row: ctrl+click'te koru, non-ctrl'da temizle
        if not is_multi:
            self.workspace.consensus_spacer.set_selected(False)
            self.workspace.consensus_row.clear_selection()
        self.workspace.sequence_viewer.clear_v_guides()
        self.workspace.sequence_viewer.clear_selection_dim_range()
        if not selected_rows:
            self.workspace.sequence_viewer.clear_h_guides()
        else:
            self.workspace.sequence_viewer.set_h_guides(frozenset(selected_rows))
            # Header seÃ§ildiÄŸinde ilgili satÄ±rlarÄ±n dizilerini de seÃ§ili yap
            n = self.workspace.model.row_count()
            max_len = self.workspace.model.max_sequence_length
            if n > 0 and max_len > 0:
                rows = sorted(selected_rows)
                # TÃ¼m satÄ±rlarÄ±n tÃ¼m kolonlarÄ±nÄ± seÃ§ili yap
                for i, item in enumerate(self.workspace.sequence_viewer.sequence_items):
                    if i in selected_rows:
                        item.set_selection(0, max_len)
                    else:
                        item.clear_selection()
                self.workspace.sequence_viewer.scene.invalidate()
                self.workspace.sequence_viewer.viewport().update()

    def on_seq_row_clicked(self, row_start, row_end):
        """Sequence view'da satÄ±r(lar)a tÄ±klanÄ±nca: header highlight + h-guide, full selection yok."""
        from PyQt5.QtWidgets import QApplication
        ws = self.workspace
        n = ws.model.row_count()
        if n == 0: return
        click_action = mouse_binding_manager.resolve_header_click(QApplication.keyboardModifiers())
        is_multi = click_action == MouseAction.ROW_MULTI_SELECT
        is_range = click_action == MouseAction.ROW_RANGE_SELECT

        # Drag (row_start != row_end) â†’ her zaman temizle ve yeni aralÄ±ÄŸÄ± seÃ§
        is_drag = (row_start != row_end)

        if is_drag or click_action in (MouseAction.ROW_SELECT, MouseAction.NONE):
            # Normal tÄ±klama veya drag: annotation + consensus temizle, yeni seÃ§im
            if self._selected_annotations:
                self._clear_all_annotation_visuals()
                self._selected_annotations.clear()
            ws.consensus_spacer.set_selected(False)
            ws.consensus_row.clear_selection()
            rows = frozenset(range(row_start, row_end + 1)) if 0 <= row_start < n else frozenset()
            clear_changed = ws.header_viewer._selection.clear()
            click_changed: frozenset = frozenset()
            if rows:
                for r in rows:
                    click_changed = click_changed | ws.header_viewer._selection.handle_ctrl_click(r, n)
            ws.header_viewer.apply_selection_to_items(clear_changed | click_changed)
            self._last_clicked_row = row_start
            if rows:
                ws.sequence_viewer.set_h_guides(rows)
            else:
                ws.sequence_viewer.clear_h_guides()

        elif is_multi:
            # Ctrl+click: toggle bu satÄ±rÄ±, mevcut seÃ§imi koru
            row = row_start
            if not (0 <= row < n): return
            changed = ws.header_viewer._selection.handle_ctrl_click(row, n)
            ws.header_viewer.apply_selection_to_items(changed)
            selected = ws.header_viewer._selection.selected_rows()
            self._last_clicked_row = row
            if selected:
                ws.sequence_viewer.set_h_guides(frozenset(selected))
            else:
                ws.sequence_viewer.clear_h_guides()

        elif is_range:
            # Shift+click: _last_clicked_row ile row_start arasÄ±ndaki tÃ¼m satÄ±rlar
            anchor = getattr(self, '_last_clicked_row', row_start)
            lo, hi = min(anchor, row_start), max(anchor, row_start)
            rows = frozenset(range(lo, hi + 1)) if 0 <= lo < n else frozenset()
            # Mevcut seÃ§imi koru, range'i ekle
            click_changed = frozenset()
            for r in rows:
                if not ws.header_viewer._selection.is_selected(r):
                    click_changed = click_changed | ws.header_viewer._selection.handle_ctrl_click(r, n)
            ws.header_viewer.apply_selection_to_items(click_changed)
            selected = ws.header_viewer._selection.selected_rows()
            if selected:
                ws.sequence_viewer.set_h_guides(frozenset(selected))
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
        """SeÃ§ili annotation'larÄ± sil (Delete tuÅŸu)."""
        if not self._selected_annotations:
            return
        self.workspace.delete_annotations_with_undo(self._selected_annotations)

    def on_consensus_spacer_clicked(self, ctrl=False):
        """Consensus spacer'a tÄ±klama.
        ctrl=False: exclusive â€” header + annotation seÃ§imlerini sÄ±fÄ±rla, sadece consensus seÃ§.
        ctrl=True:  additive  â€” header seÃ§imlerini koru, consensus'u toggle et.
        """
        if self._selected_annotations:
            self._clear_all_annotation_visuals()
            self._selected_annotations.clear()
        ws = self.workspace
        # Annotation seÃ§imini temizle (her iki modda da)
        ws.consensus_row._selected_ann_ids.clear()
        ws.sequence_viewer.clear_v_guides()
        ws.sequence_viewer.clear_selection_dim_range()
        if ctrl:
            # Additive: header seÃ§imini koru, consensus'u toggle et
            if ws.consensus_spacer._selected:
                # SeÃ§imi kaldÄ±r
                ws.consensus_spacer.set_selected(False)
                ws.consensus_row.clear_selection()
            else:
                # Ekle
                ws.consensus_spacer.set_selected(True)
                ws.consensus_spacer.setFocus()
                ws.consensus_row.set_selected(True)
                ws.consensus_row.select_all()
        else:
            # Exclusive: header seÃ§imini temizle
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
        # clear() sÄ±rasÄ±nda sÄ±fÄ±rlanan h_guide'larÄ± mevcut seÃ§ime gÃ¶re yeniden uygula
        selected_rows = self.workspace.header_viewer._selection.selected_rows()
        if selected_rows:
            self.workspace.sequence_viewer.set_h_guides(frozenset(selected_rows))
        else:
            self.workspace.sequence_viewer.clear_h_guides()


