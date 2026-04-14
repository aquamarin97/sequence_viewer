# sequence_viewer/workspace/controllers/__init__.py
"""Controllers that isolate workspace behavior from widget composition."""

from .clipboard_controller import WorkspaceClipboardController
from .command_controller import WorkspaceCommandController

__all__ = ["WorkspaceClipboardController", "WorkspaceCommandController"]

