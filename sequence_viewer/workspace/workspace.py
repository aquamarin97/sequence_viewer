# sequence_viewer/workspace/workspace.py
from __future__ import annotations

from typing import Iterable, Optional

from PyQt5.QtCore import QEvent
from PyQt5.QtWidgets import QWidget

from sequence_viewer.model.alignment_data_model import AlignmentDataModel
from sequence_viewer.model.alignment_metadata import AlignmentMetadata
from sequence_viewer.model.sequence_record import SequenceRecord
from sequence_viewer.model.undo_stack import UndoStack
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
    WorkspaceAnnotationSelectionCoordinator,
    WorkspaceLayoutScrollSync,
    WorkspaceRowSelectionCoordinator,
    WorkspaceSelectionState,
)
from sequence_viewer.workspace.signal_mapping import WorkspaceSignalMapper
from sequence_viewer.workspace.styling import WorkspaceStyleApplier
from sequence_viewer.workspace.public_api import (
    SelectedAnnotationRef,
    SelectionSnapshot,
    SequenceRowInput,
)
from sequence_viewer.workspace.ui import WorkspaceLayoutManager

_DEFAULT_CHAR_HEIGHT = 20


class SequenceWorkspaceWidget(QWidget):
    def __init__(
        self, parent=None, char_width=12.0, char_height: Optional[float] = None
    ):
        super().__init__(parent)
        if char_height is None:
            char_height = _DEFAULT_CHAR_HEIGHT
        row_height = int(round(char_height))

        # ── Bağımlılık konteyneri ────────────────────────────────────────
        ctx = WorkspaceContext(root_widget=self)
        ctx.model = AlignmentDataModel(parent=self)
        ctx.undo_stack = UndoStack(self)
        self._ctx = ctx

        # ── UI kurulumu (ctx.sequence_viewer, ctx.header_viewer, … doldurulur) ──
        WorkspaceLayoutManager(self, char_width=char_width, row_height=row_height).setup_ui(ctx)

        # ── Coordinator'lar ──────────────────────────────────────────────
        ctx.selection_state = WorkspaceSelectionState()
        ctx.layout_sync = WorkspaceLayoutScrollSync(ctx)
        ctx.annotation_presentation = WorkspaceAnnotationPresentation(ctx)
        ctx.action_dialogs = WorkspaceActionDialogCoordinator(ctx)
        ctx.annotation_selection = WorkspaceAnnotationSelectionCoordinator(ctx, ctx.selection_state)
        ctx.row_selection = WorkspaceRowSelectionCoordinator(ctx, ctx.selection_state)

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
        ctx.sequence_viewer.copyFastaRequested.connect(ctx.clipboard_controller.copy_fasta)

        ctx.annotation_layer.installEventFilter(self)

        # ── Signal bağlantıları ──────────────────────────────────────────
        WorkspaceSignalMapper(
            ctx,
            on_model_reset=self._on_model_reset,
            on_alignment_state_changed=lambda _: ctx.layout_sync.sync_consensus_visibility(),
            on_display_settings_changed=self._on_display_settings_changed,
        ).connect_all()

        # ── Public API ───────────────────────────────────────────────────
        ctx.layout_sync.sync_consensus_visibility()

    # ── Properties ───────────────────────────────────────────────────────

    @property
    def model(self):
        """Advanced escape hatch; host code should prefer the facade methods below."""
        return self._ctx.model

    def selected_rows(self):
        return self._ctx.header_viewer.selected_rows()

    # ── Dahili callback'ler ───────────────────────────────────────────────

    # ---- Public facade: data loading / row mutations -----------------

    def add_sequence(self, header, sequence) -> None:
        self._row_manager.add_sequence(header, sequence)

    def append_rows(self, rows: Iterable[SequenceRowInput | tuple]) -> None:
        for row in rows:
            header, sequence = self._coerce_row_input(row)
            self.add_sequence(header, sequence)

    def load_rows(
        self,
        rows: Iterable[SequenceRowInput | tuple],
        *,
        alignment_metadata: Optional[AlignmentMetadata] = None,
    ) -> None:
        payload = [self._coerce_row_input(row) for row in rows]
        self._ctx.model.reset_from_list(payload)
        if alignment_metadata is not None and payload:
            self._ctx.model.set_aligned(alignment_metadata)

    def append_records(
        self,
        records: Iterable[SequenceRecord],
        *,
        alignment_metadata: Optional[AlignmentMetadata] = None,
    ) -> None:
        payload = list(records)
        if payload:
            self._ctx.model.append_records_bulk(payload)
        if alignment_metadata is not None and payload:
            self._ctx.model.set_aligned(alignment_metadata)

    def load_records(
        self,
        records: Iterable[SequenceRecord],
        *,
        alignment_metadata: Optional[AlignmentMetadata] = None,
    ) -> None:
        self.clear()
        self.append_records(records, alignment_metadata=alignment_metadata)

    def clear(self) -> None:
        self._row_manager.clear()

    def move_row(self, from_index, to_index) -> None:
        self._row_manager.move_row(from_index, to_index)

    def set_header(self, index, new_header) -> None:
        self._row_manager.set_header(index, new_header)

    def row_count(self) -> int:
        return self._ctx.model.row_count()

    def all_rows(self):
        return self._ctx.model.all_rows()

    def set_aligned(self, metadata: AlignmentMetadata) -> None:
        self._ctx.model.set_aligned(metadata)

    def clear_alignment(self) -> None:
        self._ctx.model.clear_alignment()

    # ---- Public facade: annotations / commands -----------------------

    def add_annotation(self, row_index, annotation) -> None:
        self._annotation_manager.add_annotation(row_index, annotation)

    def remove_annotation(self, row_index, annotation_id) -> None:
        self._annotation_manager.remove_annotation(row_index, annotation_id)

    def clear_annotations(self) -> None:
        self._annotation_manager.clear_annotations()

    def delete_rows_with_undo(self, rows) -> None:
        self._ctx.command_controller.delete_rows_with_undo(rows)

    def delete_annotations_with_undo(self, annotations) -> None:
        self._ctx.command_controller.delete_annotations_with_undo(annotations)

    def delete_consensus_annotations_with_undo(self, annotation_ids) -> None:
        self._ctx.command_controller.delete_consensus_annotations_with_undo(annotation_ids)

    # ---- Public facade: dialogs/actions ------------------------------

    def open_find_motifs_dialog(self) -> None:
        self._ctx.action_dialogs.open_find_motifs_dialog()

    def open_edit_annotation_dialog(self, annotation) -> None:
        self._ctx.action_dialogs.open_edit_annotation_dialog(annotation)

    def open_edit_consensus_annotation_dialog(self, annotation) -> None:
        self._ctx.action_dialogs.on_consensus_annotation_double_clicked(annotation)

    # ---- Public facade: read-only snapshots --------------------------

    def selection_snapshot(self) -> SelectionSnapshot:
        ctx = self._ctx
        sequence_range = self._normalized_sequence_range(
            getattr(ctx.sequence_viewer, "_selection_range", None)
        )
        consensus_range = getattr(ctx.consensus_row, "_selection", None)
        selected_annotations = tuple(
            SelectedAnnotationRef(
                annotation_id=ann.id,
                scope="global" if row_index is None else "row",
                row_index=row_index,
            )
            for ann, row_index in ctx.selection_state.selected_annotations
        )
        return SelectionSnapshot(
            selected_rows=tuple(sorted(ctx.header_viewer.selected_rows())),
            sequence_range=sequence_range,
            selected_annotations=selected_annotations,
            consensus_selected=bool(ctx.consensus_spacer.is_selected),
            consensus_range=consensus_range,
            consensus_annotation_ids=tuple(sorted(ctx.consensus_row.get_selected_annotation_ids())),
        )

    @staticmethod
    def _coerce_row_input(row) -> tuple[str, object]:
        if isinstance(row, SequenceRowInput):
            return row.header, row.sequence
        header, sequence = row
        return header, sequence

    @staticmethod
    def _normalized_sequence_range(selection_range):
        if selection_range is None:
            return None
        row_start, row_end, col_start, col_end = selection_range
        return (
            min(row_start, row_end),
            max(row_start, row_end),
            min(col_start, col_end),
            max(col_start, col_end),
        )

    # ---- Internal callbacks ------------------------------------------

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
