# sequence_viewer/workspace/coordinators/__init__.py
from .action_dialog import WorkspaceActionDialogCoordinator
from .annotation_presentation import WorkspaceAnnotationPresentation
from .layout_scroll_sync import WorkspaceLayoutScrollSync

__all__ = [
    "WorkspaceActionDialogCoordinator",
    "WorkspaceAnnotationPresentation",
    "WorkspaceLayoutScrollSync",
]


