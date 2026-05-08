from __future__ import annotations

from unittest.mock import MagicMock

from PyQt5.QtCore import QRect
from PyQt5.QtGui import QFont

from sequence_viewer.features.annotation_layer.annotation_layout_engine import build_side_geometry
from sequence_viewer.features.consensus_row.consensus_renderer import ConsensusRenderer


class _Scrollbar:
    def value(self) -> int:
        return 0


class _SequenceViewer:
    char_height = 20
    selection_dim_ranges = []

    def horizontalScrollBar(self):
        return _Scrollbar()


def test_consensus_render_uses_visible_slice_without_all_rows() -> None:
    alignment_model = MagicMock()
    alignment_model.row_count.return_value = 1
    alignment_model.max_sequence_length = 100
    alignment_model.is_aligned = True
    alignment_model.consensus_annotations = []

    widget = MagicMock()
    widget.rect.return_value = QRect(0, 0, 800, 20)
    widget.width.return_value = 800
    widget.height.return_value = 20
    widget._is_selected = False
    widget._selected_ann_ids = set()
    widget._selection_ranges = []
    widget._alignment_model = alignment_model
    widget._sequence_viewer = _SequenceViewer()
    widget._ann_geometry = (build_side_geometry([]), build_side_geometry([]))
    widget._font = QFont()
    widget._color_map = {}
    widget._model.cached_consensus.return_value = None
    widget._get_char_width.return_value = 10.0
    widget._get_view_left.return_value = 0.0
    widget._effective_mode.return_value = "text"
    widget._consensus_length.return_value = 100
    widget._consensus_slice.return_value = ""

    ConsensusRenderer().render(widget, MagicMock())

    alignment_model.all_rows.assert_not_called()
    widget._consensus_slice.assert_called_once_with(0, 80)
