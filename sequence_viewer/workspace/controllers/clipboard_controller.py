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
            sel = getattr(ctx.sequence_viewer, "_selection_range", None)
            if sel is not None:
                rs, re, cs, ce = sel
                start_col = min(cs, ce)
                end_col = max(cs, ce) + 1
                for row in range(rs, re + 1):
                    try:
                        seq = ctx.model.get_sequence(row)
                    except (IndexError, AttributeError):
                        continue
                    fragment = str(seq)[start_col:end_col]
                    if fragment:
                        lines.append(fragment)
        if lines:
            QApplication.clipboard().setText("\n".join(lines))

    def copy_fasta(self) -> None:
        ctx = self._ctx
        blocks: list[str] = []
        sel = getattr(ctx.sequence_viewer, "_selection_range", None)
        has_fragment_selection = sel is not None
        selected = ctx.header_viewer.selected_rows()
        if has_fragment_selection:
            rs, re, cs, ce = sel
            start_col = min(cs, ce)
            end_col = max(cs, ce) + 1
            for row in range(rs, re + 1):
                try:
                    header = ctx.model.get_header(row)
                    seq = ctx.model.get_sequence(row)
                except (IndexError, AttributeError):
                    continue
                fragment = str(seq)[start_col:end_col]
                if fragment:
                    blocks.append(f">{header}\n{fragment}")
        elif selected:
            for i, (header, sequence) in enumerate(ctx.model.all_rows()):
                if i in selected:
                    blocks.append(f">{header}\n{sequence}")
        if blocks:
            QApplication.clipboard().setText("\n".join(blocks))

    def copy_consensus_sequence(self) -> None:
        text = self._ctx.consensus_row.clipboard_sequence_text()
        if text:
            QApplication.clipboard().setText(text)

    def copy_consensus_fasta(self) -> None:
        text = self._ctx.consensus_row.clipboard_fasta_text(self._ctx.consensus_spacer.label)
        if text:
            QApplication.clipboard().setText(text)
