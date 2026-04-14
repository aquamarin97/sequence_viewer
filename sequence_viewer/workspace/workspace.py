# sequence_viewer/workspace/workspace.py
from __future__ import annotations

from PyQt5.QtCore import QEvent
from PyQt5.QtWidgets import QWidget

from sequence_viewer.model.alignment_data_model import AlignmentDataModel
from sequence_viewer.model.undo_stack import UndoStack
from sequence_viewer.settings.display_settings_manager import display_settings_manager
from sequence_viewer.workspace.context import WorkspaceContext
from sequence_viewer.workspace.controllers import (
    WorkspaceAnnotationManager,
    WorkspaceClipboardController,
    WorkspaceCommandController,
    WorkspaceKeyboardController,
    WorkspaceRowManager,
)
from sequence_viewer.workspace.coordinators import (
    WorkspaceActionDialogCoordinator,
    WorkspaceAnnotationPresentation,
    WorkspaceLayoutScrollSync,
)
from sequence_viewer.workspace.signal_mapping import WorkspaceSignalMapper
from sequence_viewer.workspace.styling import WorkspaceStyleApplier
from sequence_viewer.workspace.ui import WorkspaceLayoutManager


class SequenceWorkspaceWidget(QWidget):
    def __init__(self, parent=None, char_width=12.0, char_height=None):
        super().__init__(parent)
        if char_height is None:
            char_height = display_settings_manager.sequence_char_height
        row_height = int(round(char_height))

        # ── Bağımlılık konteyneri ────────────────────────────────────────
        ctx = WorkspaceContext(root_widget=self)
        ctx.model = AlignmentDataModel(parent=self)
        ctx.undo_stack = UndoStack(self)
        self._ctx = ctx

        # ── UI kurulumu (ctx.sequence_viewer, ctx.header_viewer, … doldurulur) ──
        WorkspaceLayoutManager(self, char_width=char_width, row_height=row_height).setup_ui(ctx)

        # ── Coordinator'lar ──────────────────────────────────────────────
        ctx.layout_sync = WorkspaceLayoutScrollSync(ctx)
        ctx.annotation_presentation = WorkspaceAnnotationPresentation(ctx)
        ctx.action_dialogs = WorkspaceActionDialogCoordinator(ctx)

        # ── Controller'lar ───────────────────────────────────────────────
        self._annotation_manager = WorkspaceAnnotationManager(ctx.model)
        self._row_manager = WorkspaceRowManager(ctx.model)
        ctx.clipboard_controller = WorkspaceClipboardController(ctx)
        ctx.command_controller = WorkspaceCommandController(ctx)
        ctx.keyboard_controller = WorkspaceKeyboardController(ctx)
        ctx.style_applier = WorkspaceStyleApplier(
            root_widget=self,
            left_panel=ctx.left_panel,
            splitter=ctx.splitter,
            sequence_viewer=ctx.sequence_viewer,
        )

        ctx.annotation_layer.installEventFilter(self)

        # ── Signal bağlantıları ──────────────────────────────────────────
        WorkspaceSignalMapper(
            ctx,
            on_model_reset=self._on_model_reset,
            on_alignment_state_changed=lambda _: ctx.layout_sync.sync_consensus_visibility(),
            on_display_settings_changed=self._on_display_settings_changed,
        ).connect_all()

        # ── Public API ───────────────────────────────────────────────────
        self.add_annotation = self._annotation_manager.add_annotation
        self.remove_annotation = self._annotation_manager.remove_annotation
        self.clear_annotations = self._annotation_manager.clear_annotations
        self.add_sequence = self._row_manager.add_sequence
        self.clear = self._row_manager.clear
        self.move_row = self._row_manager.move_row
        self.set_header = self._row_manager.set_header
        self.delete_rows_with_undo = ctx.command_controller.delete_rows_with_undo
        self.delete_annotations_with_undo = ctx.command_controller.delete_annotations_with_undo
        self.delete_consensus_annotations_with_undo = (
            ctx.command_controller.delete_consensus_annotations_with_undo
        )
        self.open_find_motifs_dialog = ctx.action_dialogs.open_find_motifs_dialog
        self.open_edit_annotation_dialog = ctx.action_dialogs.open_edit_annotation_dialog
        self.open_edit_consensus_annotation_dialog = (
            ctx.action_dialogs.on_consensus_annotation_double_clicked
        )

        ctx.layout_sync.sync_consensus_visibility()

    # ── Properties ───────────────────────────────────────────────────────

    @property
    def model(self):
        return self._ctx.model

    def selected_rows(self):
        return self._ctx.header_viewer.selected_rows()

    # ── Dahili callback'ler ───────────────────────────────────────────────

    def _on_model_reset(self) -> None:
        self._ctx.action_dialogs.on_model_reset()
        self._ctx.layout_sync.sync_consensus_visibility()

    def _on_display_settings_changed(self) -> None:
        layout = self._ctx.layout_sync.compute_row_layout()
        self._ctx.layout_sync.apply_layout(layout)

    # ── Qt olayları ───────────────────────────────────────────────────────

    def eventFilter(self, obj, event):
        if obj is self._ctx.annotation_layer and event.type() == QEvent.Resize:
            self._ctx.annotation_spacer.sync_height(self._ctx.annotation_layer.height())
        return super().eventFilter(obj, event)

    def keyPressEvent(self, event):
        if self._ctx.keyboard_controller.handle_keypress(event):
            return
        super().keyPressEvent(event)
