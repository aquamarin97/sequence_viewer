# sequence_viewer/workspace/controllers/keyboard_controller.py
from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt5.QtCore import Qt

if TYPE_CHECKING:
    from sequence_viewer.workspace.context import WorkspaceContext


class WorkspaceKeyboardController:
    """Workspace düzeyindeki klavye kısayollarını yönetir.

    Kısayolların *ne yapacağını* bilir; işi uygun controller'a devreder.
    Clipboard, undo ve silme kısayolları burada tanımlanır.
    """

    def __init__(self, ctx: "WorkspaceContext") -> None:
        self._ctx = ctx

    def handle_keypress(self, event) -> bool:
        ctrl = bool(event.modifiers() & Qt.ControlModifier)
        shift = bool(event.modifiers() & Qt.ShiftModifier)

        if ctrl and not shift and event.key() == Qt.Key_Z:
            if self._ctx.undo_stack.undo():
                event.accept()
                return True

        if ctrl and shift and event.key() == Qt.Key_C:
            self._ctx.clipboard_controller.copy_fasta()
            event.accept()
            return True

        if ctrl and not shift and event.key() == Qt.Key_C:
            self._ctx.clipboard_controller.copy_sequences()
            event.accept()
            return True

        if event.key() == Qt.Key_Delete:
            return self._handle_delete(event)

        return False

    def _handle_delete(self, event) -> bool:
        ctx = self._ctx
        has_coord = ctx.action_dialogs.has_selected_annotations()
        has_cons = ctx.consensus_row.has_selected_annotations()

        if not (has_coord or has_cons):
            return False

        if has_coord:
            selected = ctx.action_dialogs.get_selected_annotations()
            ctx.command_controller.delete_annotations_with_undo(selected)

        if has_cons:
            ann_ids = ctx.consensus_row.get_selected_annotation_ids()
            ctx.command_controller.delete_consensus_annotations_with_undo(ann_ids)

        event.accept()
        return True
