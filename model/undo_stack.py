from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

from PyQt5.QtCore import QObject, pyqtSignal


class UndoCommand:
    def __init__(self, text: str = ""):
        self.text = text

    def execute(self):
        raise NotImplementedError

    def undo(self):
        raise NotImplementedError

    def redo(self):
        self.execute()


class UndoStack(QObject):
    changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._undo: list[UndoCommand] = []
        self._redo: list[UndoCommand] = []

    def push(self, command: UndoCommand):
        command.execute()
        self._undo.append(command)
        self._redo.clear()
        self.changed.emit()

    def can_undo(self) -> bool:
        return bool(self._undo)

    def can_redo(self) -> bool:
        return bool(self._redo)

    def undo(self):
        if not self._undo:
            return False
        command = self._undo.pop()
        command.undo()
        self._redo.append(command)
        self.changed.emit()
        return True

    def redo(self):
        if not self._redo:
            return False
        command = self._redo.pop()
        command.redo()
        self._undo.append(command)
        self.changed.emit()
        return True

    def clear(self):
        if not self._undo and not self._redo:
            return
        self._undo.clear()
        self._redo.clear()
        self.changed.emit()


class ModelSnapshotCommand(UndoCommand):
    def __init__(
        self,
        *,
        text: str,
        model,
        mutate: Callable[[], None],
        after_restore: Optional[Callable[[], None]] = None,
    ):
        super().__init__(text=text)
        self._model = model
        self._mutate = mutate
        self._after_restore = after_restore
        self._before = model.create_snapshot()
        self._after = None

    def execute(self):
        self._mutate()
        self._after = self._model.create_snapshot()
        if self._after_restore is not None:
            self._after_restore()

    def undo(self):
        self._model.restore_snapshot(self._before)
        if self._after_restore is not None:
            self._after_restore()

    def redo(self):
        if self._after is None:
            self.execute()
            return
        self._model.restore_snapshot(self._after)
        if self._after_restore is not None:
            self._after_restore()
