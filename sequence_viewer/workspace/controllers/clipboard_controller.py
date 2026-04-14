# sequence_viewer/workspace/controllers/clipboard_controller.py
from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt5.QtWidgets import QApplication

if TYPE_CHECKING:
    from sequence_viewer.workspace.context import WorkspaceContext


class WorkspaceClipboardController:
    """Pano (clipboard) işlemlerini yönetir."""

    def __init__(self, ctx: "WorkspaceContext") -> None:
        self._ctx = ctx

    def copy_sequences(self) -> None:
        ctx = self._ctx
        lines: list[str] = []
        selected = ctx.header_viewer.selected_rows()
        if ctx.consensus_spacer.is_selected:
            from sequence_viewer.model.consensus_calculator import ConsensusCalculator

            seqs = [seq for _, seq in ctx.model.all_rows()]
            if seqs:
                lines.append(ConsensusCalculator.compute(seqs))
        elif selected:
            for i, (_, sequence) in enumerate(ctx.model.all_rows()):
                if i in selected:
                    lines.append(sequence)
        else:
            for item in ctx.sequence_viewer.sequence_items:
                if item.selection_range is not None:
                    start, end = item.selection_range
                    fragment = item.sequence[start:end]
                    if fragment:
                        lines.append(fragment)
        if lines:
            QApplication.clipboard().setText("\n".join(lines))

    def copy_fasta(self) -> None:
        ctx = self._ctx
        blocks: list[str] = []
        has_fragment_selection = any(
            item.selection_range is not None for item in ctx.sequence_viewer.sequence_items
        )
        selected = ctx.header_viewer.selected_rows()
        if has_fragment_selection:
            for i, item in enumerate(ctx.sequence_viewer.sequence_items):
                if item.selection_range is not None:
                    start, end = item.selection_range
                    fragment = item.sequence[start:end]
                    if fragment:
                        header = ctx.model.get_header(i)
                        blocks.append(f">{header}\n{fragment}")
        elif selected:
            for i, (header, sequence) in enumerate(ctx.model.all_rows()):
                if i in selected:
                    blocks.append(f">{header}\n{sequence}")
        if blocks:
            QApplication.clipboard().setText("\n".join(blocks))

