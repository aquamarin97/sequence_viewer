# sequence_viewer/workspace/controllers/clipboard_controller.py
from __future__ import annotations

from PyQt5.QtWidgets import QApplication


class WorkspaceClipboardController:
    """Owns clipboard-related behaviors for the workspace."""

    def __init__(self, workspace):
        self.workspace = workspace

    def copy_sequences(self) -> None:
        lines: list[str] = []
        selected = self.workspace.header_viewer._selection.selected_rows()
        if self.workspace.consensus_spacer._selected:
            from sequence_viewer.model.consensus_calculator import ConsensusCalculator

            seqs = [seq for _, seq in self.workspace.model.all_rows()]
            if seqs:
                lines.append(ConsensusCalculator.compute(seqs))
        elif selected:
            for i, (_, sequence) in enumerate(self.workspace.model.all_rows()):
                if i in selected:
                    lines.append(sequence)
        else:
            for item in self.workspace.sequence_viewer.sequence_items:
                if item.selection_range is not None:
                    start, end = item.selection_range
                    fragment = item.sequence[start:end]
                    if fragment:
                        lines.append(fragment)
        if lines:
            QApplication.clipboard().setText("\n".join(lines))

    def copy_fasta(self) -> None:
        blocks: list[str] = []
        has_fragment_selection = any(
            item.selection_range is not None for item in self.workspace.sequence_viewer.sequence_items
        )
        selected = self.workspace.header_viewer._selection.selected_rows()
        if has_fragment_selection:
            for i, item in enumerate(self.workspace.sequence_viewer.sequence_items):
                if item.selection_range is not None:
                    start, end = item.selection_range
                    fragment = item.sequence[start:end]
                    if fragment:
                        header = self.workspace.model.get_header(i)
                        blocks.append(f">{header}\n{fragment}")
        elif selected:
            for i, (header, sequence) in enumerate(self.workspace.model.all_rows()):
                if i in selected:
                    blocks.append(f">{header}\n{sequence}")
        if blocks:
            QApplication.clipboard().setText("\n".join(blocks))

