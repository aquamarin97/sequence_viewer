# sequence_viewer/workspace/signal_mapping.py
from __future__ import annotations

from typing import TYPE_CHECKING, Callable

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
        ctx.model.annotationUpdated.connect(ctx.annotation_presentation.on_annotation_changed)
        ctx.model.annotationsReset.connect(ctx.annotation_presentation.on_annotation_changed)
        ctx.annotation_layer.annotationClicked.connect(ctx.action_dialogs.on_annotation_layer_clicked)
        ctx.annotation_layer.annotationDoubleClicked.connect(
            ctx.action_dialogs.on_annotation_layer_double_clicked
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

    def _connect_header_signals(self) -> None:
        ctx = self._ctx
        ctx.header_viewer.headerEdited.connect(ctx.action_dialogs.on_header_edited)
        ctx.header_viewer.rowMoveRequested.connect(ctx.action_dialogs.on_row_move_requested)
        ctx.header_viewer.rowsDeleteRequested.connect(ctx.action_dialogs.on_rows_delete_requested)
        ctx.header_viewer.selectionChanged.connect(ctx.action_dialogs.on_selection_changed)

    def _connect_consensus_signals(self) -> None:
        ctx = self._ctx
        ctx.consensus_spacer.clicked.connect(ctx.action_dialogs.on_consensus_spacer_clicked)
        ctx.sequence_viewer.rowClicked.connect(ctx.action_dialogs.on_seq_row_clicked)
        ctx.sequence_viewer.selectionChanged.connect(ctx.consensus_row.clear_selection)
        ctx.sequence_viewer.selectionChanged.connect(
            lambda: ctx.consensus_spacer.set_selected(False)
        )
        ctx.sequence_viewer.add_v_guide_observer(ctx.consensus_row.update)
        ctx.sequence_viewer.add_v_guide_observer(ctx.pos_ruler.update)

    def _connect_theme_and_settings_signals(self) -> None:
        from sequence_viewer.settings.annotation_styles import annotation_style_manager
        from sequence_viewer.settings.display_settings_manager import display_settings_manager
        from sequence_viewer.settings.theme import theme_manager

        ctx = self._ctx
        theme_manager.themeChanged.connect(ctx.style_applier.on_theme_changed)
        ctx.style_applier.on_theme_changed(theme_manager.current)
        display_settings_manager.displaySettingsChanged.connect(self._on_display_settings_changed)
        annotation_style_manager.stylesChanged.connect(
            ctx.annotation_presentation.on_annotation_changed
        )

    def _connect_zoom_and_selection_signals(self) -> None:
        ctx = self._ctx
        anim = getattr(ctx.sequence_viewer, "_zoom_animation", None)
        if anim is not None:
            anim.valueChanged.connect(ctx.annotation_presentation.on_zoom_changed)
        ctx.sequence_viewer.horizontalScrollBar().rangeChanged.connect(
            ctx.annotation_presentation.on_zoom_changed
        )
