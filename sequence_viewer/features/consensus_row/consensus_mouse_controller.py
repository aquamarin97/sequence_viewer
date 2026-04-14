# sequence_viewer/features/consensus_row/consensus_mouse_controller.py
from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QToolTip

from sequence_viewer.model.annotation import AnnotationType
from sequence_viewer.settings.mouse_binding_manager import MouseAction, mouse_binding_manager

if TYPE_CHECKING:
    from sequence_viewer.features.consensus_row.consensus_annotation_handler import (
        ConsensusAnnotationHandler,
        AnnotationSelectResult,
    )
    from sequence_viewer.features.consensus_row.consensus_drag_controller import ConsensusDragController


class ConsensusMouseController:
    """Consensus satırındaki tüm fare olaylarını koordine eder.

    Hover state ve press-on-annotation bayrağını yönetir;
    annotation seçimini ConsensusAnnotationHandler'a,
    drag mantığını ConsensusDragController'a devreder.

    Olay metodları True döndürürse widget super()'ı çağırmamalıdır.
    """

    def __init__(
        self,
        widget,
        sequence_viewer,
        ann_handler: "ConsensusAnnotationHandler",
        drag_ctrl: "ConsensusDragController",
    ) -> None:
        self._w = widget
        self._sv = sequence_viewer
        self._ann = ann_handler
        self._drag = drag_ctrl
        self._hovered_ann_id = None
        self._press_on_annotation: bool = False

    # ── Olay işleyicileri ──────────────────────────────────────────────────

    def handle_press(self, event) -> bool:
        if event.button() != Qt.LeftButton:
            return False

        ann = self._w._annotation_at(event.pos())
        if ann:
            self._press_on_annotation = True
            self._sv.clear_caret()
            action = mouse_binding_manager.resolve_annotation_click(
                event.modifiers(), event.button()
            )
            if action == MouseAction.NONE:
                return False  # widget super'ı çağırır
            result = self._ann.compute_select(
                ann,
                ctrl=(action == MouseAction.ANNOTATION_MULTI_SELECT),
                current_ids=frozenset(self._w._selected_ann_ids),
            )
            self._apply_annotation_result(result)
            event.accept()
            return True

        # Annotation dışı press — drag izlemeye başla
        self._press_on_annotation = False
        self._w._selected_ann_ids.clear()
        self._w.workspaceAnnotationClearRequested.emit()
        self._sv.clear_selection_dim_range()
        self._w._clear_guide_cols()
        self._w.update()
        self._w.setFocus()
        self._sv.clear_visual_selection()
        try:
            self._sv._model.clear_selection()
        except Exception:
            pass

        scene_col = self._w._scene_col_at_x(float(event.pos().x()))
        self._drag.begin_press(event.pos(), scene_col)
        self._w._is_selected = True
        self._w.headerClearRequested.emit()
        self._w.positionRulerRefreshRequested.emit()
        event.accept()
        return True

    def handle_move(self, event) -> bool:
        if not self._drag.has_press():
            # Hover modu
            ann = self._w._annotation_at(event.pos())
            new_id = ann.id if ann else None
            if new_id != self._hovered_ann_id:
                self._hovered_ann_id = new_id
                self._w.setCursor(Qt.PointingHandCursor if ann else Qt.IBeamCursor)
                self._w.update()
            if ann:
                QToolTip.showText(event.globalPos(), ann.tooltip_text(), self._w)
            else:
                QToolTip.hideText()
            return False  # scroll, vb. için super'a bırak

        # Drag threshold kontrolü
        if not self._drag.is_dragging() and self._drag.should_start_drag(event.pos()):
            drag_action = mouse_binding_manager.resolve_sequence_drag(
                event.modifiers(), Qt.LeftButton
            )
            if drag_action == MouseAction.NONE:
                return False
            self._drag.start_drag()
            if drag_action == MouseAction.DRAG_SELECT:
                self._w._clear_guide_cols()
            self._sv.clear_caret()
            self._w.setCursor(Qt.SizeHorCursor)

        if self._drag.is_dragging():
            scene_col = self._w._scene_col_at_x(float(event.pos().x()))
            update = self._drag.compute_drag_update(scene_col, self._w._guide_cols())
            self._w._selection = update.selection
            self._w._set_guide_cols(update.guide_cols)
            self._w._update_drag_tooltip(event)
            self._w.update()
            event.accept()
            return True

        return False

    def handle_release(self, event) -> bool:
        if event.button() != Qt.LeftButton:
            return False

        self._w.unsetCursor()
        self._w.setCursor(Qt.IBeamCursor)

        if self._drag.is_dragging():
            drag_action = mouse_binding_manager.resolve_sequence_drag(
                event.modifiers(), Qt.LeftButton
            )
            update = self._drag.finalize_drag(
                drag_action, self._w._selection, self._w._guide_cols()
            )
            self._w._set_guide_cols(update.guide_cols)
        else:
            if self._press_on_annotation:
                self._press_on_annotation = False
                self._w.update()
                event.accept()
                return True
            self._w._selection = None
            boundary_col = self._w._boundary_col_at_x(float(event.pos().x()))
            click_action = mouse_binding_manager.resolve_sequence_click(
                event.modifiers(), Qt.LeftButton
            )
            update = self._drag.finalize_click(
                boundary_col, click_action, self._w._guide_cols()
            )
            if click_action != MouseAction.NONE:
                self._w._set_guide_cols(update.guide_cols)
                if update.set_caret is not None:
                    self._sv.set_caret(update.set_caret, -1)

        self._w.update()
        event.accept()
        return True

    def handle_double_click(self, event) -> bool:
        if mouse_binding_manager.is_annotation_edit_event(event.modifiers(), event.button()):
            ann = self._w._annotation_at(event.pos())
            if ann:
                if ann.type != AnnotationType.MISMATCH_MARKER:
                    self._w.annotationEditRequested.emit(ann)
                event.accept()
                return True
        return False

    def handle_leave(self, event) -> None:
        if self._hovered_ann_id is not None:
            self._hovered_ann_id = None
            self._w.setCursor(Qt.IBeamCursor)
            self._w.update()

    # ── Yardımcı ──────────────────────────────────────────────────────────

    def _apply_annotation_result(self, result: "AnnotationSelectResult") -> None:
        if result.clear_workspace:
            self._w.workspaceAnnotationClearRequested.emit()
        self._w._selected_ann_ids = set(result.selected_ids)
        self._w._is_selected = bool(result.selected_ids)
        self._w._selection_ranges = result.selection_ranges
        self._w.spacerSelectionChanged.emit(self._w._is_selected)
        if result.guide_cols:
            self._w._set_guide_cols(result.guide_cols)
            self._sv.set_selection_dim_range(result.dim_start, result.dim_end)
        self._w.update()
        if result.refresh_coordinator:
            self._w.coordinatorRefreshRequested.emit()
