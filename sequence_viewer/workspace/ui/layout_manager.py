# sequence_viewer/workspace/ui/layout_manager.py
from __future__ import annotations

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QHBoxLayout, QSplitter, QVBoxLayout, QWidget

from sequence_viewer.features.annotation_layer.annotation_layer_widget import AnnotationLayerWidget
from sequence_viewer.features.consensus_row.consensus_row_widget import ConsensusRowWidget
from sequence_viewer.features.header_viewer.header_spacer_widgets import (
    AnnotationSpacerWidget,
    ConsensusSpacerWidget,
    HeaderPositionSpacerWidget,
    HeaderTopWidget,
)
from sequence_viewer.features.header_viewer.header_viewer_widget import HeaderViewerWidget
from sequence_viewer.features.navigation_ruler.navigation_ruler_widget import RulerWidget
from sequence_viewer.features.position_ruler.position_ruler_widget import SequencePositionRulerWidget
from sequence_viewer.features.sequence_viewer.sequence_viewer_widget import SequenceViewerWidget


class WorkspaceLayoutManager:
    """Builds and wires the workspace UI structure."""

    def __init__(self, workspace, *, char_width: float, row_height: int):
        self.workspace = workspace
        self.char_width = char_width
        self.row_height = row_height

    def setup_ui(self) -> None:
        self._build_left_panel()
        right_panel = self._build_right_panel()
        self._build_splitter(right_panel)
        self._build_root_layout()
        self._apply_viewport_margins()

    def _build_left_panel(self) -> None:
        ws = self.workspace
        ws.header_top = HeaderTopWidget(height=28, parent=ws)
        ws.header_pos_spacer = HeaderPositionSpacerWidget(height=24, parent=ws)
        ws.annotation_spacer = AnnotationSpacerWidget(parent=ws)
        ws.consensus_spacer = ConsensusSpacerWidget(parent=ws)
        ws.header_viewer = HeaderViewerWidget(parent=ws, row_height=self.row_height, initial_width=160.0)

        ws.left_panel = QWidget(ws)
        layout = QVBoxLayout(ws.left_panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        for widget in (
            ws.header_top,
            ws.header_pos_spacer,
            ws.annotation_spacer,
            ws.consensus_spacer,
            ws.header_viewer,
        ):
            layout.addWidget(widget)

    def _build_right_panel(self) -> QWidget:
        ws = self.workspace
        ws.sequence_viewer = SequenceViewerWidget(
            parent=ws,
            char_width=self.char_width,
            char_height=self.row_height,
        )
        ws.sequence_viewer.set_alignment_model(ws._model)
        ws.ruler = RulerWidget(ws.sequence_viewer, parent=ws)
        ws.pos_ruler = SequencePositionRulerWidget(ws.sequence_viewer, parent=ws)
        ws.annotation_layer = AnnotationLayerWidget(
            model=ws._model,
            sequence_viewer=ws.sequence_viewer,
            parent=ws,
        )
        ws.consensus_row = ConsensusRowWidget(
            alignment_model=ws._model,
            sequence_viewer=ws.sequence_viewer,
            parent=ws,
        )

        right_panel = QWidget(ws)
        layout = QVBoxLayout(right_panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        for widget in (
            ws.ruler,
            ws.pos_ruler,
            ws.annotation_layer,
            ws.consensus_row,
            ws.sequence_viewer,
        ):
            layout.addWidget(widget)
        return right_panel

    def _build_splitter(self, right_panel: QWidget) -> None:
        ws = self.workspace
        ws.splitter = QSplitter(Qt.Horizontal, ws)
        ws.splitter.addWidget(ws.left_panel)
        ws.splitter.addWidget(right_panel)
        ws.splitter.setSizes([130, 500])

    def _build_root_layout(self) -> None:
        ws = self.workspace
        layout = QHBoxLayout(ws)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(ws.splitter)
        ws.setLayout(layout)
        ws.setFocusPolicy(Qt.StrongFocus)

    def _apply_viewport_margins(self) -> None:
        ws = self.workspace
        hsb_h = ws.sequence_viewer.horizontalScrollBar().sizeHint().height()
        ws.header_viewer.setViewportMargins(0, 0, 0, hsb_h)

