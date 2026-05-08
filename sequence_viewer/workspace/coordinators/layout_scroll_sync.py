from __future__ import annotations

# sequence_viewer/workspace/coordinators/layout_scroll_sync.py

from typing import TYPE_CHECKING

from PyQt5.QtWidgets import QScrollBar, QWIDGETSIZE_MAX

from sequence_viewer.features.annotation_layer.annotation_layout_engine import (
    partition_annotations_by_side,
    side_strip_height,
)
from sequence_viewer.workspace.row_layout import RowLayout

if TYPE_CHECKING:
    from sequence_viewer.workspace.context import WorkspaceContext


class _ScrollSyncGuard:
    def __init__(self) -> None:
        self._locked = False

    def sync(self, target: QScrollBar, value: int) -> None:
        if self._locked:
            return
        self._locked = True
        try:
            target.setValue(value)
        finally:
            self._locked = False


class WorkspaceLayoutScrollSync:
    def __init__(self, ctx: "WorkspaceContext") -> None:
        self._ctx = ctx
        self._v_scroll_guard = _ScrollSyncGuard()

    def compute_row_layout(self) -> RowLayout:
        ch = self._ctx.sequence_viewer.char_height
        above_heights, below_heights = [], []
        for record in self._ctx.model.all_records():
            above_anns, below_anns = partition_annotations_by_side(record.annotations)
            above_heights.append(side_strip_height(above_anns))
            below_heights.append(side_strip_height(below_anns))
        return RowLayout.build(ch, above_heights, below_heights)

    def apply_layout(self, layout: RowLayout) -> None:
        self._ctx.sequence_viewer.apply_row_layout(layout)
        self._ctx.header_viewer.apply_row_layout(layout)

    def connect_scroll_sync(self) -> None:
        h_vsb = self._ctx.header_viewer.verticalScrollBar()
        s_vsb = self._ctx.sequence_viewer.verticalScrollBar()
        s_vsb.valueChanged.connect(lambda v: self._v_scroll_guard.sync(h_vsb, v))
        h_vsb.valueChanged.connect(lambda v: self._v_scroll_guard.sync(s_vsb, v))

    def on_splitter_moved(self, _pos: int, _index: int) -> None:
        sizes = self._ctx.splitter.sizes()
        if len(sizes) < 2 or self._ctx.header_viewer.get_row_count() == 0:
            return
        left, right = sizes
        required = self._ctx.header_viewer.compute_required_width()
        if left > required:
            total = left + right
            self._ctx.splitter.blockSignals(True)
            self._ctx.splitter.setSizes([required, max(0, total - required)])
            self._ctx.splitter.blockSignals(False)

    def sync_consensus_visibility(self) -> None:
        """Consensus row'un aktifliğine göre consensus_spacer yüksekliğini ve
        görünürlüğünü senkronize eder."""
        cr = self._ctx.consensus_row
        cs = self._ctx.consensus_spacer
        cr_active = not cr.isHidden() and cr.height() > 0
        if not cr_active and self._ctx.model.is_aligned:
            cr.update_visibility()
            cr_active = not cr.isHidden() and cr.height() > 0
        if cr_active:
            cs.setFixedHeight(cr.height())
            cs.setVisible(True)
            above_h, ch, _below_h = cr.compute_heights()
            cs.sync_seq_region(float(above_h), float(ch))
        else:
            cs.setFixedHeight(0)
            cs.setVisible(False)
        cs.updateGeometry()
        if self._ctx.left_panel.layout() is not None:
            self._ctx.left_panel.layout().invalidate()
            self._ctx.left_panel.layout().activate()
        self._ctx.left_panel.updateGeometry()
        self._ctx.left_panel.update()

    def on_consensus_annotation_changed(self, *_) -> None:
        self.sync_consensus_visibility()

    def sync_consensus_spacer(
        self, height: int, visible: bool, above_h: float, char_h: float
    ) -> None:
        cs = self._ctx.consensus_spacer
        cs.setFixedHeight(height if visible else 0)
        cs.setVisible(visible)
        if visible:
            cs.sync_seq_region(above_h, char_h)
        cs.updateGeometry()
        if self._ctx.left_panel.layout() is not None:
            self._ctx.left_panel.layout().invalidate()
            self._ctx.left_panel.layout().activate()
        self._ctx.left_panel.updateGeometry()
        self._ctx.left_panel.update()

    def update_header_max_width(self) -> None:
        if self._ctx.header_viewer.get_row_count() > 0:
            req = self._ctx.header_viewer.compute_required_width()
            self._ctx.header_viewer.setMaximumWidth(req)
            self._ctx.left_panel.setMaximumWidth(req)
        else:
            self._ctx.header_viewer.setMaximumWidth(QWIDGETSIZE_MAX)
            self._ctx.left_panel.setMaximumWidth(QWIDGETSIZE_MAX)
            total = sum(self._ctx.splitter.sizes())
            if total > 0:
                half = total // 2
                self._ctx.splitter.blockSignals(True)
                self._ctx.splitter.setSizes([half, total - half])
                self._ctx.splitter.blockSignals(False)
