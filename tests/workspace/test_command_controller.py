from __future__ import annotations

from unittest.mock import MagicMock

from sequence_viewer.model.undo_stack import ModelSnapshotCommand
from sequence_viewer.workspace.controllers.command_controller import WorkspaceCommandController


def test_delete_rows_with_undo_empty_does_not_push(ctx) -> None:
    controller = WorkspaceCommandController(ctx)

    controller.delete_rows_with_undo([])

    ctx.undo_stack.push.assert_not_called()


def test_delete_annotations_with_undo_empty_does_not_push(ctx) -> None:
    controller = WorkspaceCommandController(ctx)

    controller.delete_annotations_with_undo([])

    ctx.undo_stack.push.assert_not_called()


def test_push_delete_command_pushes_model_snapshot_command(ctx) -> None:
    controller = WorkspaceCommandController(ctx)
    mutate = MagicMock()

    controller.push_delete_command("Delete rows", mutate)

    ctx.undo_stack.push.assert_called_once()
    command = ctx.undo_stack.push.call_args.args[0]
    assert isinstance(command, ModelSnapshotCommand)
    assert command.text == "Delete rows"
    assert command._model is ctx.model
    assert command._mutate is mutate
