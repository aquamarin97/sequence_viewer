from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sequence_viewer.workspace.context import WorkspaceContext
from sequence_viewer.workspace.coordinators.selection.selection_state import (
    WorkspaceSelectionState,
)


@pytest.fixture
def ctx():
    ctx = MagicMock(spec=WorkspaceContext(MagicMock()))
    ctx.root_widget = MagicMock()
    ctx.model = MagicMock()
    ctx.model.row_count.return_value = 3
    ctx.model.max_sequence_length = 100
    ctx.model.is_aligned = False
    ctx.model.consensus_annotations = []
    ctx.undo_stack = MagicMock()

    ctx.header_viewer = MagicMock()
    ctx.header_viewer.selected_rows.return_value = set()
    ctx.header_viewer.clear_selection.return_value = frozenset()
    ctx.header_viewer.toggle_row.side_effect = lambda row, _n: frozenset({row})
    ctx.header_viewer.select_row.side_effect = lambda row, _n: frozenset({row})
    ctx.header_viewer.range_select.side_effect = (
        lambda lo, hi, _n: frozenset(range(lo, hi + 1))
    )

    ctx.sequence_viewer = MagicMock()
    ctx.sequence_viewer.sequence_items = []
    ctx.sequence_viewer.scene = MagicMock()
    ctx.sequence_viewer.viewport.return_value = MagicMock()

    ctx.annotation_layer = MagicMock()
    ctx.annotation_presentation = MagicMock()
    ctx.annotation_selection = MagicMock()
    ctx.command_controller = MagicMock()

    ctx.consensus_row = MagicMock()
    ctx.consensus_row.get_selected_annotation_ids.return_value = []
    ctx.consensus_spacer = MagicMock()
    ctx.consensus_spacer.is_selected = False
    return ctx


@pytest.fixture
def state():
    return WorkspaceSelectionState()
