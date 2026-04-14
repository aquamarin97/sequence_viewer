# sequence_viewer/workspace/signal_mapping.py
from __future__ import annotations


class WorkspaceSignalMapper:
    """Centralizes signal-to-slot wiring for SequenceWorkspaceWidget."""

    def __init__(self, workspace):
        self.workspace = workspace

    def connect_all(self) -> None:
        self._connect_layout_signals()
        self._connect_annotation_signals()
        self._connect_model_signals()
        self._connect_header_signals()
        self._connect_consensus_signals()
        self._connect_theme_and_settings_signals()
        self._connect_zoom_and_selection_signals()

    def _connect_layout_signals(self) -> None:
        self.workspace.splitter.splitterMoved.connect(self.workspace._layout_sync.on_splitter_moved)
        self.workspace._layout_sync.connect_scroll_sync()

    def _connect_annotation_signals(self) -> None:
        ws = self.workspace
        ws._model.annotationAdded.connect(ws._annotation_presentation.on_annotation_changed)
        ws._model.annotationRemoved.connect(ws._annotation_presentation.on_annotation_changed)
        ws._model.annotationUpdated.connect(ws._annotation_presentation.on_annotation_changed)
        ws._model.annotationsReset.connect(ws._annotation_presentation.on_annotation_changed)
        ws.annotation_layer.annotationClicked.connect(ws._action_dialogs.on_annotation_layer_clicked)
        ws.annotation_layer.annotationDoubleClicked.connect(ws._action_dialogs.on_annotation_layer_double_clicked)
        ws.annotation_layer.installEventFilter(ws)
        ws.annotation_spacer.sync_height(ws.annotation_layer.height())

    def _connect_model_signals(self) -> None:
        ws = self.workspace
        ws._model.rowAppended.connect(ws._action_dialogs.on_row_appended)
        ws._model.rowRemoved.connect(ws._action_dialogs.on_row_removed)
        ws._model.rowMoved.connect(ws._action_dialogs.on_row_moved)
        ws._model.headerChanged.connect(ws._action_dialogs.on_header_changed)
        ws._model.modelReset.connect(ws._on_model_reset)
        ws._model.alignmentStateChanged.connect(ws._on_alignment_state_changed)

    def _connect_header_signals(self) -> None:
        ws = self.workspace
        ws.header_viewer.headerEdited.connect(ws._action_dialogs.on_header_edited)
        ws.header_viewer.rowMoveRequested.connect(ws._action_dialogs.on_row_move_requested)
        ws.header_viewer.rowsDeleteRequested.connect(ws._action_dialogs.on_rows_delete_requested)
        ws.header_viewer.selectionChanged.connect(ws._action_dialogs.on_selection_changed)

    def _connect_consensus_signals(self) -> None:
        ws = self.workspace
        ws.consensus_spacer.clicked.connect(ws._action_dialogs.on_consensus_spacer_clicked)
        ws.sequence_viewer.rowClicked.connect(ws._action_dialogs.on_seq_row_clicked)
        ws.sequence_viewer.selectionChanged.connect(ws.consensus_row.clear_selection)
        ws.sequence_viewer.selectionChanged.connect(
            lambda: ws.consensus_spacer.set_selected(False)
        )
        ws.sequence_viewer.add_v_guide_observer(ws.consensus_row.update)
        ws.sequence_viewer.add_v_guide_observer(ws.pos_ruler.update)

    def _connect_theme_and_settings_signals(self) -> None:
        ws = self.workspace
        from sequence_viewer.settings.annotation_styles import annotation_style_manager
        from sequence_viewer.settings.theme import theme_manager
        from sequence_viewer.settings.display_settings_manager import display_settings_manager

        theme_manager.themeChanged.connect(ws._style_applier.on_theme_changed)
        ws._style_applier.on_theme_changed(theme_manager.current)
        display_settings_manager.displaySettingsChanged.connect(ws._on_display_settings_changed)
        annotation_style_manager.stylesChanged.connect(ws._annotation_presentation.on_annotation_changed)

    def _connect_zoom_and_selection_signals(self) -> None:
        ws = self.workspace
        anim = getattr(ws.sequence_viewer, "_zoom_animation", None)
        if anim is not None:
            anim.valueChanged.connect(ws._annotation_presentation.on_zoom_changed)
        ws.sequence_viewer.horizontalScrollBar().rangeChanged.connect(
            ws._annotation_presentation.on_zoom_changed
        )

