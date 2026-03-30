from __future__ import annotations
from typing import TYPE_CHECKING, List
from PyQt5.QtWidgets import QScrollBar
from features.annotation_layer.annotation_layout_engine import assign_lanes, lane_count
from widgets.row_layout import RowLayout, strip_height

if TYPE_CHECKING:
    from widgets.workspace import SequenceWorkspaceWidget

class _ScrollSyncGuard:
    def __init__(self): self._locked = False
    def sync(self, target, value):
        if self._locked: return
        self._locked = True
        try: target.setValue(value)
        finally: self._locked = False

class WorkspaceLayoutScrollSync:
    def __init__(self, workspace): self.workspace = workspace; self._v_scroll_guard = _ScrollSyncGuard()

    def compute_row_layout(self):
        ch = self.workspace.sequence_viewer.char_height
        above_heights, below_heights = [], []
        for record in self.workspace.model.all_records():
            above_anns = [a for a in record.annotations if a.type.is_above_sequence()]
            below_anns = [a for a in record.annotations if not a.type.is_above_sequence()]
            above_heights.append(strip_height(lane_count(assign_lanes(above_anns))))
            below_heights.append(strip_height(lane_count(assign_lanes(below_anns))))
        return RowLayout.build(ch, above_heights, below_heights)

    def apply_layout(self, layout):
        self.workspace.sequence_viewer.apply_row_layout(layout)
        self.workspace.header_viewer.apply_row_layout(layout)

    def connect_scroll_sync(self):
        h_vsb = self.workspace.header_viewer.verticalScrollBar()
        s_vsb = self.workspace.sequence_viewer.verticalScrollBar()
        s_vsb.valueChanged.connect(lambda v: self._v_scroll_guard.sync(h_vsb, v))
        h_vsb.valueChanged.connect(lambda v: self._v_scroll_guard.sync(s_vsb, v))

    def on_splitter_moved(self, _pos, _index):
        sizes = self.workspace.splitter.sizes()
        if len(sizes) < 2 or not self.workspace.header_viewer.header_items: return
        left, right = sizes
        required = self.workspace.header_viewer.compute_required_width()
        if left > required:
            total = left + right
            self.workspace.splitter.blockSignals(True)
            self.workspace.splitter.setSizes([required, max(0, total - required)])
            self.workspace.splitter.blockSignals(False)

    def update_header_max_width(self):
        big = 16_777_215
        if self.workspace.header_viewer.header_items:
            req = self.workspace.header_viewer.compute_required_width()
            self.workspace.header_viewer.setMaximumWidth(req)
            self.workspace.left_panel.setMaximumWidth(req)
        else:
            self.workspace.header_viewer.setMaximumWidth(big)
            self.workspace.left_panel.setMaximumWidth(big)
            total = sum(self.workspace.splitter.sizes())
            if total > 0:
                half = total // 2
                self.workspace.splitter.blockSignals(True)
                self.workspace.splitter.setSizes([half, total - half])
                self.workspace.splitter.blockSignals(False)
