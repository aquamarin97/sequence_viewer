# sequence_viewer/workspace/coordinators/action_dialog.py
from __future__ import annotations

from typing import TYPE_CHECKING

from sequence_viewer.model.annotation import Annotation, AnnotationType
from sequence_viewer.settings.mouse_binding_manager import MouseAction, mouse_binding_manager

if TYPE_CHECKING:
    from sequence_viewer.workspace.context import WorkspaceContext


class WorkspaceActionDialogCoordinator:
    def __init__(self, ctx: "WorkspaceContext") -> None:
        self._ctx = ctx
        self._selected_annotations: list = []  # [(annotation, row_index_or_None), ...]
        self._last_clicked_row: int = 0  # Shift+click anchor

    # ── Seçim görsel senkronizasyonu ─────────────────────────────────────

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

    def _clear_all_annotation_visuals(self) -> None:
        self._ctx.annotation_presentation.clear_annotation_selection()
        self._ctx.annotation_layer.clear_annotation_selection()
        self._ctx.sequence_viewer.clear_selection_dim_range()

    def _apply_union_selection(self) -> None:
        ctx = self._ctx
        n = ctx.model.row_count()
        ctx.sequence_viewer.clear_visual_selection()
        try:
            ctx.sequence_viewer._model.clear_selection()
        except Exception:
            pass
        ctx.sequence_viewer.clear_selection_dim_range()

        cr = ctx.consensus_row
        cr_ann_ids = set(getattr(cr, "_selected_ann_ids", set()))
        cr_anns: list = []
        if cr_ann_ids and getattr(ctx.model, "is_aligned", False):
            ann_map = {a.id: a for a in ctx.model.consensus_annotations}
            cr_anns = [ann_map[aid] for aid in cr_ann_ids if aid in ann_map]

        has_any = bool(self._selected_annotations or cr_anns)
        if not has_any or n == 0:
            ctx.sequence_viewer.clear_h_guides()
            clear_changed = ctx.header_viewer._selection.clear()
            ctx.header_viewer.apply_selection_to_items(clear_changed)
            return

        items = ctx.sequence_viewer.sequence_items
        row_ranges_map: dict = {}
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
        ctx.sequence_viewer.scene.invalidate()
        ctx.sequence_viewer.viewport().update()

        boundaries: list = []
        focus_ranges: list = []
        for ann, _ in self._selected_annotations:
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

        seq_ctrl = ctx.sequence_viewer._controller
        if seq_ctrl is not None:
            seq_ctrl._v_guide_cols = list(boundaries)
        ctx.sequence_viewer.set_v_guides(boundaries)
        if focus_ranges:
            ctx.sequence_viewer.set_selection_focus_ranges(focus_ranges)

        if per_row_indices:
            ctx.sequence_viewer.set_h_guides(frozenset(per_row_indices))
        else:
            ctx.sequence_viewer.clear_h_guides()
        changed = ctx.header_viewer._selection.clear()
        for ri in per_row_indices:
            changed = changed | ctx.header_viewer._selection.handle_ctrl_click(ri, n)
        ctx.header_viewer.apply_selection_to_items(changed)

    # ── Annotation layer click handler'ları ──────────────────────────────

    def on_annotation_layer_clicked(self, annotation) -> None:
        from PyQt5.QtWidgets import QApplication

        action = mouse_binding_manager.resolve_annotation_click(QApplication.keyboardModifiers())
        is_multi = action == MouseAction.ANNOTATION_MULTI_SELECT
        if is_multi:
            existing = next(
                (i for i, (a, _) in enumerate(self._selected_annotations) if a.id == annotation.id),
                -1,
            )
            if existing >= 0:
                self._selected_annotations.pop(existing)
            else:
                self._selected_annotations.append((annotation, None))
            self._ctx.annotation_layer.set_selected_annotation(annotation.id, ctrl=True)
            self._apply_union_selection()
            return
        self._ctx.consensus_row.clear_selection()
        self._selected_annotations = [(annotation, None)]
        self._update_selection_visuals(annotation.id, is_layer=True)
        self._ctx.root_widget.setFocus()
        _boundaries = self._annotation_guide_boundaries(annotation)
        _seq_ctrl = self._ctx.sequence_viewer._controller
        if _seq_ctrl is not None:
            _seq_ctrl._v_guide_cols = list(_boundaries)
        self._ctx.sequence_viewer.set_v_guides(_boundaries)
        focus_start, focus_end = self._annotation_focus_range(annotation)
        self._ctx.sequence_viewer.set_selection_dim_range(focus_start, focus_end)
        n = self._ctx.model.row_count()
        if n > 0:
            self._ctx.sequence_viewer.set_visual_selection(0, n - 1, focus_start, focus_end - 1)
            self._ctx.sequence_viewer._model.start_selection(0, focus_start)
            self._ctx.sequence_viewer._model.update_selection(n - 1, focus_end - 1)
            self._ctx.sequence_viewer.show_info_panel(0, n - 1, focus_start, focus_end - 1)

    def on_annotation_layer_double_clicked(self, annotation) -> None:
        if annotation.type == AnnotationType.MISMATCH_MARKER:
            return
        self.do_edit_dialog(annotation, row_index=None)

    # ── Per-row annotation item click handler'ları ───────────────────────

    def on_ann_item_clicked(self, annotation, row_index) -> None:
        from PyQt5.QtWidgets import QApplication

        ctx = self._ctx
        action = mouse_binding_manager.resolve_annotation_click(QApplication.keyboardModifiers())
        is_multi = action == MouseAction.ANNOTATION_MULTI_SELECT
        if is_multi:
            ctx.sequence_viewer.clear_caret()
            existing = next(
                (i for i, (a, _) in enumerate(self._selected_annotations) if a.id == annotation.id),
                -1,
            )
            if existing >= 0:
                self._selected_annotations.pop(existing)
            else:
                self._selected_annotations.append((annotation, row_index))
            ctx.annotation_presentation.set_selected_annotation(annotation.id, ctrl=True)
            self._apply_union_selection()
            return
        ctx.consensus_row.clear_selection()
        ctx.sequence_viewer.clear_caret()
        self._selected_annotations = [(annotation, row_index)]
        self._update_selection_visuals(annotation.id, is_layer=False)
        ctx.root_widget.setFocus()
        n = ctx.model.row_count()

        clear_changed = ctx.header_viewer._selection.clear()
        if 0 <= row_index < n:
            click_changed = ctx.header_viewer._selection.handle_click(row_index, n)
            ctx.header_viewer.apply_selection_to_items(clear_changed | click_changed)
        else:
            ctx.header_viewer.apply_selection_to_items(clear_changed)

        ctx.consensus_spacer.set_selected(False)
        ctx.consensus_row.clear_selection()

        if 0 <= row_index < n:
            ctx.sequence_viewer.set_h_guides(frozenset({row_index}))
        else:
            ctx.sequence_viewer.clear_h_guides()

        _boundaries = self._annotation_guide_boundaries(annotation)
        _seq_ctrl = ctx.sequence_viewer._controller
        if _seq_ctrl is not None:
            _seq_ctrl._v_guide_cols = list(_boundaries)
        ctx.sequence_viewer.set_v_guides(_boundaries)
        focus_start, focus_end = self._annotation_focus_range(annotation)
        ctx.sequence_viewer.set_selection_dim_range(focus_start, focus_end)

        if 0 <= row_index < n:
            ctx.sequence_viewer.set_visual_selection(row_index, row_index, focus_start, focus_end - 1)
            ctx.sequence_viewer._model.start_selection(row_index, focus_start)
            ctx.sequence_viewer._model.update_selection(row_index, focus_end - 1)
            ctx.sequence_viewer.show_info_panel(row_index, row_index, focus_start, focus_end - 1)

    def on_ann_item_double_clicked(self, annotation, _row_index) -> None:
        if annotation.type == AnnotationType.MISMATCH_MARKER:
            return
        self.open_edit_annotation_dialog(annotation)

    # ── Consensus annotation ──────────────────────────────────────────────

    def on_consensus_annotation_double_clicked(self, annotation) -> None:
        from sequence_viewer.dialogs.edit_annotation_dialog import EditAnnotationDialog

        dlg = EditAnnotationDialog(annotation=annotation, parent=self._ctx.root_widget)
        if dlg.exec_() == EditAnnotationDialog.Accepted:
            updated = dlg.result_annotation()
            if updated is None:
                return
            try:
                self._ctx.model.update_consensus_annotation(updated)
            except Exception:
                pass

    # ── Dialog açma ───────────────────────────────────────────────────────

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
            except Exception:
                pass

    # ── Header & model event handler'ları ────────────────────────────────

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

    def on_selection_changed(self, selected_rows) -> None:
        from PyQt5.QtWidgets import QApplication

        ctx = self._ctx
        header_action = mouse_binding_manager.resolve_header_click(QApplication.keyboardModifiers())
        is_multi = header_action == MouseAction.ROW_MULTI_SELECT
        if self._selected_annotations:
            self._clear_all_annotation_visuals()
            self._selected_annotations.clear()
        if not is_multi:
            ctx.consensus_spacer.set_selected(False)
            ctx.consensus_row.clear_selection()
        ctx.sequence_viewer.clear_v_guides()
        ctx.sequence_viewer.clear_selection_dim_range()
        if not selected_rows:
            ctx.sequence_viewer.clear_h_guides()
        else:
            ctx.sequence_viewer.set_h_guides(frozenset(selected_rows))
            n = ctx.model.row_count()
            max_len = ctx.model.max_sequence_length
            if n > 0 and max_len > 0:
                for i, item in enumerate(ctx.sequence_viewer.sequence_items):
                    if i in selected_rows:
                        item.set_selection(0, max_len)
                    else:
                        item.clear_selection()
                ctx.sequence_viewer.scene.invalidate()
                ctx.sequence_viewer.viewport().update()

    def on_seq_row_clicked(self, row_start: int, row_end: int) -> None:
        from PyQt5.QtWidgets import QApplication

        ctx = self._ctx
        n = ctx.model.row_count()
        if n == 0:
            return
        click_action = mouse_binding_manager.resolve_header_click(QApplication.keyboardModifiers())
        is_multi = click_action == MouseAction.ROW_MULTI_SELECT
        is_range = click_action == MouseAction.ROW_RANGE_SELECT
        is_drag = row_start != row_end

        if is_drag or click_action in (MouseAction.ROW_SELECT, MouseAction.NONE):
            if self._selected_annotations:
                self._clear_all_annotation_visuals()
                self._selected_annotations.clear()
            ctx.consensus_spacer.set_selected(False)
            ctx.consensus_row.clear_selection()
            rows = frozenset(range(row_start, row_end + 1)) if 0 <= row_start < n else frozenset()
            clear_changed = ctx.header_viewer._selection.clear()
            click_changed: frozenset = frozenset()
            if rows:
                for r in rows:
                    click_changed = click_changed | ctx.header_viewer._selection.handle_ctrl_click(r, n)
            ctx.header_viewer.apply_selection_to_items(clear_changed | click_changed)
            self._last_clicked_row = row_start
            if rows:
                ctx.sequence_viewer.set_h_guides(rows)
            else:
                ctx.sequence_viewer.clear_h_guides()

        elif is_multi:
            row = row_start
            if not (0 <= row < n):
                return
            changed = ctx.header_viewer._selection.handle_ctrl_click(row, n)
            ctx.header_viewer.apply_selection_to_items(changed)
            selected = ctx.header_viewer._selection.selected_rows()
            self._last_clicked_row = row
            if selected:
                ctx.sequence_viewer.set_h_guides(frozenset(selected))
            else:
                ctx.sequence_viewer.clear_h_guides()

        elif is_range:
            anchor = getattr(self, "_last_clicked_row", row_start)
            lo, hi = min(anchor, row_start), max(anchor, row_start)
            rows = frozenset(range(lo, hi + 1)) if 0 <= lo < n else frozenset()
            click_changed = frozenset()
            for r in rows:
                if not ctx.header_viewer._selection.is_selected(r):
                    click_changed = click_changed | ctx.header_viewer._selection.handle_ctrl_click(r, n)
            ctx.header_viewer.apply_selection_to_items(click_changed)
            selected = ctx.header_viewer._selection.selected_rows()
            if selected:
                ctx.sequence_viewer.set_h_guides(frozenset(selected))
            else:
                ctx.sequence_viewer.clear_h_guides()

    def on_row_appended(self, index: int, header: str, sequence: str) -> None:
        ctx = self._ctx
        ctx.header_viewer.add_header_item(f"{index + 1}. {header}")
        ctx.sequence_viewer.add_sequence(sequence)
        ctx.ruler.update()
        ctx.layout_sync.update_header_max_width()
        layout = ctx.layout_sync.compute_row_layout()
        ctx.layout_sync.apply_layout(layout)
        ctx.annotation_presentation.rebuild_ann_items(layout)

    def on_row_removed(self, _index) -> None:
        self.rebuild_views()

    def on_row_moved(self, from_index: int, to_index: int) -> None:
        self._ctx.header_viewer._selection.move_row(from_index, to_index)
        self.rebuild_views()

    def on_header_changed(self, index: int, new_header: str) -> None:
        ctx = self._ctx
        if index < 0 or index >= len(ctx.header_viewer.header_items):
            return
        ctx.header_viewer.header_items[index]._model.full_text = f"{index + 1}. {new_header}"
        ctx.header_viewer.header_items[index].update()
        ctx.layout_sync.update_header_max_width()

    def on_model_reset(self) -> None:
        self.rebuild_views()

    # ── Seçim durumu sorgu / değişim ─────────────────────────────────────

    def has_selected_annotations(self) -> bool:
        return bool(self._selected_annotations)

    def get_selected_annotations(self) -> list:
        return list(self._selected_annotations)

    def clear_selected_annotations(self) -> None:
        self._selected_annotations.clear()

    # ── Annotation silme ──────────────────────────────────────────────────

    def delete_selected_annotation(self) -> None:
        if not self._selected_annotations:
            return
        self._ctx.command_controller.delete_annotations_with_undo(self._selected_annotations)

    # ── Consensus spacer ──────────────────────────────────────────────────

    def on_consensus_spacer_clicked(self, ctrl: bool = False) -> None:
        if self._selected_annotations:
            self._clear_all_annotation_visuals()
            self._selected_annotations.clear()
        ctx = self._ctx
        ctx.consensus_row._selected_ann_ids.clear()
        ctx.sequence_viewer.clear_v_guides()
        ctx.sequence_viewer.clear_selection_dim_range()
        if ctrl:
            if ctx.consensus_spacer._selected:
                ctx.consensus_spacer.set_selected(False)
                ctx.consensus_row.clear_selection()
            else:
                ctx.consensus_spacer.set_selected(True)
                ctx.consensus_spacer.setFocus()
                ctx.consensus_row.set_selected(True)
                ctx.consensus_row.select_all()
        else:
            changed = ctx.header_viewer._selection.clear()
            ctx.header_viewer.apply_selection_to_items(changed)
            ctx.sequence_viewer.clear_h_guides()
            ctx.sequence_viewer.clear_visual_selection()
            try:
                ctx.sequence_viewer._model.clear_selection()
            except Exception:
                pass
            ctx.consensus_spacer.set_selected(True)
            ctx.consensus_spacer.setFocus()
            ctx.consensus_row.set_selected(True)
            ctx.consensus_row.select_all()

    # ── View yeniden inşası ───────────────────────────────────────────────

    def rebuild_views(self) -> None:
        ctx = self._ctx
        h_scroll = ctx.sequence_viewer.horizontalScrollBar().value()
        v_scroll = ctx.sequence_viewer.verticalScrollBar().value()
        ctx.annotation_presentation.remove_all_ann_items()
        ctx.header_viewer.clear()
        ctx.sequence_viewer.clear()
        for i, (header, sequence) in enumerate(ctx.model.all_rows()):
            item = ctx.header_viewer.add_header_item(f"{i + 1}. {header}")
            item.set_row_index(i)
            if ctx.header_viewer._selection.is_selected(i):
                item.set_selected(True)
            ctx.sequence_viewer.add_sequence(sequence)
        layout = ctx.layout_sync.compute_row_layout()
        ctx.layout_sync.apply_layout(layout)
        ctx.ruler.update()
        ctx.layout_sync.update_header_max_width()
        ctx.annotation_presentation.rebuild_ann_items(layout)
        ctx.sequence_viewer.horizontalScrollBar().setValue(h_scroll)
        ctx.sequence_viewer.verticalScrollBar().setValue(v_scroll)
        selected_rows = ctx.header_viewer._selection.selected_rows()
        if selected_rows:
            ctx.sequence_viewer.set_h_guides(frozenset(selected_rows))
        else:
            ctx.sequence_viewer.clear_h_guides()
