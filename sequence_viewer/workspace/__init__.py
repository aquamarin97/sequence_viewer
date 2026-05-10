# sequence_viewer/workspace/__init__.py
from .workspace import SequenceWorkspaceWidget
from .public_api import SelectedAnnotationRef, SelectionSnapshot, SequenceRowInput

__all__ = [
    "SelectedAnnotationRef",
    "SelectionSnapshot",
    "SequenceRowInput",
    "SequenceWorkspaceWidget",
]

