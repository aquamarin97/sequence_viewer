# sequence_viewer/workspace/ui/layout_manager.py
from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QHBoxLayout, QSplitter, QVBoxLayout, QWidget

from sequence_viewer.features.annotation_layer.annotation_layer_widget import AnnotationLayerWidget
from sequence_viewer.features.consensus_row.consensus_row_widget import ConsensusRowWidget
from sequence_viewer.features.consensus_row.consensus_spacer_widget import ConsensusSpacerWidget
from sequence_viewer.features.header_viewer.header_spacer_widgets import (
    AnnotationSpacerWidget,
    HeaderPositionSpacerWidget,
    HeaderTopWidget,
)
from sequence_viewer.features.header_viewer.header_viewer_widget import HeaderViewerWidget
from sequence_viewer.features.navigation_ruler.navigation_ruler_widget import RulerWidget
from sequence_viewer.features.position_ruler.position_ruler_widget import SequencePositionRulerWidget
from sequence_viewer.features.sequence_viewer.sequence_viewer_widget import SequenceViewerWidget

if TYPE_CHECKING:
    from sequence_viewer.workspace.context import WorkspaceContext


class WorkspaceLayoutManager:
    """Workspace UI yapısını kurar ve WorkspaceContext'i doldurur."""

    def __init__(self, workspace: QWidget, *, char_width: float, row_height: int) -> None:
        self._workspace = workspace  # Yalnızca Qt parent olarak kullanılır
        self.char_width = char_width
        self.row_height = row_height

    def setup_ui(self, ctx: "WorkspaceContext") -> None:
        self._build_left_panel(ctx)
        right_panel = self._build_right_panel(ctx)
        self._build_splitter(ctx, right_panel)
        self._build_root_layout(ctx)
        self._apply_viewport_margins(ctx)

    # ── Sol panel ────────────────────────────────────────────────────────

    def _build_left_panel(self, ctx: "WorkspaceContext") -> None:
        ws = self._workspace
        header_top = HeaderTopWidget(height=28, parent=ws)
        header_pos_spacer = HeaderPositionSpacerWidget(height=24, parent=ws)
        ctx.annotation_spacer = AnnotationSpacerWidget(parent=ws)
        ctx.consensus_spacer = ConsensusSpacerWidget(parent=ws)
        ctx.header_viewer = HeaderViewerWidget(parent=ws, row_height=self.row_height, initial_width=160.0)

        ctx.left_panel = QWidget(ws)
        layout = QVBoxLayout(ctx.left_panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        for widget in (
            header_top,
            header_pos_spacer,
            ctx.annotation_spacer,
            ctx.consensus_spacer,
            ctx.header_viewer,
        ):
            layout.addWidget(widget)

    # ── Sağ panel ────────────────────────────────────────────────────────

    def _build_right_panel(self, ctx: "WorkspaceContext") -> QWidget:
        ws = self._workspace
        ctx.sequence_viewer = SequenceViewerWidget(
            parent=ws,
            char_width=self.char_width,
            char_height=self.row_height,
        )
        ctx.sequence_viewer.set_alignment_model(ctx.model)
        ctx.ruler = RulerWidget(ctx.sequence_viewer, parent=ws)
        ctx.pos_ruler = SequencePositionRulerWidget(ctx.sequence_viewer, parent=ws)
        ctx.annotation_layer = AnnotationLayerWidget(
            model=ctx.model,
            sequence_viewer=ctx.sequence_viewer,
            parent=ws,
        )
        ctx.consensus_row = ConsensusRowWidget(
            alignment_model=ctx.model,
            sequence_viewer=ctx.sequence_viewer,
            parent=ws,
        )

        right_panel = QWidget(ws)
        layout = QVBoxLayout(right_panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        for widget in (
            ctx.ruler,
            ctx.pos_ruler,
            ctx.annotation_layer,
            ctx.consensus_row,
            ctx.sequence_viewer,
        ):
            layout.addWidget(widget)
        return right_panel

    # ── Splitter & kök layout ─────────────────────────────────────────────

    def _build_splitter(self, ctx: "WorkspaceContext", right_panel: QWidget) -> None:
        ws = self._workspace
        ctx.splitter = QSplitter(Qt.Horizontal, ws)
        ctx.splitter.addWidget(ctx.left_panel)
        ctx.splitter.addWidget(right_panel)
        ctx.splitter.setSizes([130, 500])

    def _build_root_layout(self, ctx: "WorkspaceContext") -> None:
        ws = self._workspace
        layout = QHBoxLayout(ws)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(ctx.splitter)
        ws.setLayout(layout)
        ws.setFocusPolicy(Qt.StrongFocus)

    def _apply_viewport_margins(self, ctx: "WorkspaceContext") -> None:
        hsb_h = ctx.sequence_viewer.horizontalScrollBar().sizeHint().height()
        ctx.header_viewer.setViewportMargins(0, 0, 0, hsb_h)
