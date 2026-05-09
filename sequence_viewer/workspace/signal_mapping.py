from __future__ import annotations

# sequence_viewer/workspace/signal_mapping.py

from typing import TYPE_CHECKING, Callable

from PyQt5.QtCore import QVariantAnimation

if TYPE_CHECKING:
    from sequence_viewer.workspace.context import WorkspaceContext


class WorkspaceSignalMapper:
    """Tüm signal-slot bağlantılarını tek bir yerde kurar.

    Daha önce 17 ayrı parametre alırken, artık WorkspaceContext üzerinden
    tüm bileşenlere erişir. Yalnızca workspace.py düzeyindeki üç callback
    (model reset, hizalama durumu, display settings) parametre olarak geçilir.
    """

    def __init__(
        self,
        ctx: "WorkspaceContext",
        *,
        on_model_reset: Callable[[], None],
        on_alignment_state_changed: Callable[[object], None],
        on_display_settings_changed: Callable[[], None],
    ) -> None:
        self._ctx = ctx
        self._on_model_reset = on_model_reset
        self._on_alignment_state_changed = on_alignment_state_changed
        self._on_display_settings_changed = on_display_settings_changed

    def connect_all(self) -> None:
        self._connect_layout_signals()
        self._connect_annotation_signals()
        self._connect_model_signals()
        self._connect_header_signals()
        self._connect_consensus_signals()
        self._connect_theme_and_settings_signals()
        self._connect_zoom_and_selection_signals()

    def _connect_layout_signals(self) -> None:
        ctx = self._ctx
        ctx.splitter.splitterMoved.connect(ctx.layout_sync.on_splitter_moved)
        ctx.layout_sync.connect_scroll_sync()

    def _connect_annotation_signals(self) -> None:
        ctx = self._ctx
        ctx.model.annotationAdded.connect(ctx.annotation_presentation.on_annotation_changed)
        ctx.model.annotationRemoved.connect(ctx.annotation_presentation.on_annotation_changed)
        ctx.model.annotationUpdated.connect(ctx.annotation_presentation.on_annotation_updated)
        ctx.model.annotationsReset.connect(ctx.annotation_presentation.on_annotation_changed)
        ctx.annotation_layer.annotationClicked.connect(ctx.annotation_selection.on_annotation_layer_clicked)
        ctx.annotation_layer.annotationDoubleClicked.connect(
            ctx.annotation_selection.on_annotation_layer_double_clicked
        )
        ctx.annotation_spacer.sync_height(ctx.annotation_layer.height())

    def _connect_model_signals(self) -> None:
        ctx = self._ctx
        ctx.model.rowAppended.connect(ctx.action_dialogs.on_row_appended)
        ctx.model.rowRemoved.connect(ctx.action_dialogs.on_row_removed)
        ctx.model.rowMoved.connect(ctx.action_dialogs.on_row_moved)
        ctx.model.headerChanged.connect(ctx.action_dialogs.on_header_changed)
        ctx.model.modelReset.connect(self._on_model_reset)
        ctx.model.alignmentStateChanged.connect(self._on_alignment_state_changed)
        ctx.model.consensusAnnotationAdded.connect(ctx.layout_sync.on_consensus_annotation_changed)
        ctx.model.consensusAnnotationRemoved.connect(ctx.layout_sync.on_consensus_annotation_changed)
        ctx.model.consensusAnnotationUpdated.connect(ctx.layout_sync.on_consensus_annotation_changed)

    def _connect_header_signals(self) -> None:
        ctx = self._ctx
        ctx.header_viewer.headerEdited.connect(ctx.action_dialogs.on_header_edited)
        ctx.header_viewer.rowMoveRequested.connect(ctx.action_dialogs.on_row_move_requested)
        ctx.header_viewer.rowsDeleteRequested.connect(ctx.action_dialogs.on_rows_delete_requested)
        ctx.header_viewer.selectionChanged.connect(ctx.row_selection.on_selection_changed)

    def _connect_consensus_signals(self) -> None:
        ctx = self._ctx
        ctx.consensus_spacer.clicked.connect(ctx.row_selection.on_consensus_spacer_clicked)
        ctx.consensus_spacer.copySequenceRequested.connect(ctx.clipboard_controller.copy_consensus_sequence)
        ctx.consensus_spacer.copyFastaRequested.connect(ctx.clipboard_controller.copy_consensus_fasta)
        ctx.sequence_viewer.rowClicked.connect(ctx.row_selection.on_seq_row_clicked)
        ctx.sequence_viewer.selectionChanged.connect(ctx.consensus_row.clear_selection)
        ctx.sequence_viewer.selectionChanged.connect(ctx.consensus_spacer.deselect)
        ctx.sequence_viewer.add_v_guide_observer(ctx.consensus_row.update)
        ctx.sequence_viewer.add_v_guide_observer(ctx.pos_ruler.update)
        ctx.consensus_row.annotationEditRequested.connect(
            ctx.action_dialogs.on_consensus_annotation_double_clicked
        )
        ctx.consensus_row.workspaceAnnotationClearRequested.connect(
            self._clear_workspace_annotation_selection
        )
        ctx.consensus_row.spacerSelectionChanged.connect(ctx.consensus_spacer.set_selected)
        ctx.consensus_row.coordinatorRefreshRequested.connect(ctx.annotation_selection.apply_union_selection)
        ctx.consensus_row.copySequenceRequested.connect(ctx.clipboard_controller.copy_consensus_sequence)
        ctx.consensus_row.copyFastaRequested.connect(ctx.clipboard_controller.copy_consensus_fasta)
        ctx.consensus_row.deleteAnnotationsRequested.connect(
            ctx.command_controller.delete_consensus_annotations_with_undo
        )
        ctx.consensus_row.headerClearRequested.connect(self._clear_header_selection_for_consensus)
        ctx.consensus_row.spacerSyncRequested.connect(ctx.layout_sync.sync_consensus_spacer)
        ctx.consensus_row.positionRulerRefreshRequested.connect(ctx.pos_ruler.update)

    def _connect_theme_and_settings_signals(self) -> None:
        from sequence_viewer.settings.annotation_styles import annotation_style_manager
        from sequence_viewer.settings.display_settings_manager import display_settings_manager
        from sequence_viewer.settings.theme import theme_manager

        ctx = self._ctx
        theme_manager.themeChanged.connect(ctx.style_applier.on_theme_changed)
        ctx.style_applier.on_theme_changed(theme_manager.current)
        display_settings_manager.displaySettingsChanged.connect(self._on_display_settings_changed)
        display_settings_manager.displaySettingsChanged.connect(ctx.layout_sync.sync_consensus_visibility)
        annotation_style_manager.stylesChanged.connect(
            ctx.annotation_presentation.on_annotation_changed
        )
        annotation_style_manager.stylesChanged.connect(ctx.layout_sync.sync_consensus_visibility)

    def _connect_zoom_and_selection_signals(self) -> None:
        ctx = self._ctx
        anim = getattr(ctx.sequence_viewer, "_zoom_animation", None)
        if anim is not None:
            anim.valueChanged.connect(ctx.annotation_presentation.on_zoom_changed)

        # hbar.rangeChanged fires as a side-effect of _update_scene_rect during animation.
        # anim.valueChanged already covers that frame — skip to avoid double work.
        def _on_hbar_range_zoom(*_):
            a = getattr(ctx.sequence_viewer, "_zoom_animation", None)
            if a is not None and a.state() == QVariantAnimation.Running:
                return
            ctx.annotation_presentation.on_zoom_changed()

        ctx.sequence_viewer.horizontalScrollBar().rangeChanged.connect(_on_hbar_range_zoom)

    def _clear_workspace_annotation_selection(self) -> None:
        ctx = self._ctx
        if ctx.annotation_selection.has_selected_annotations():
            ctx.annotation_selection.clear_selected_annotations()
            ctx.annotation_selection.clear_all_annotation_visuals()
        changed = ctx.header_viewer.clear_selection()
        ctx.header_viewer.apply_selection_to_items(changed)
        ctx.sequence_viewer.clear_h_guides()

    def _clear_header_selection_for_consensus(self) -> None:
        ctx = self._ctx
        ctx.consensus_spacer.set_selected(True)
        ctx.consensus_row.set_selected(True)
        changed = ctx.header_viewer.clear_selection()
        ctx.header_viewer.apply_selection_to_items(changed)
        ctx.sequence_viewer.clear_h_guides()
        ctx.sequence_viewer.clear_visual_selection()
        ctx.sequence_viewer.clear_selection_model()
        ctx.sequence_viewer.clear_selection_dim_range()
