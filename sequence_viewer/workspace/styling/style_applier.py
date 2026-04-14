# sequence_viewer/workspace/styling/style_applier.py
from __future__ import annotations

from PyQt5.QtGui import QBrush, QPalette

from sequence_viewer.settings.scrollbar_style import apply_scrollbar_style


class WorkspaceStyleApplier:
    """Applies workspace-level style/theme changes."""

    def __init__(self, workspace):
        self.workspace = workspace

    def on_theme_changed(self, theme) -> None:
        from sequence_viewer.settings.annotation_styles import annotation_style_manager
        from sequence_viewer.settings.color_styles import color_style_manager

        target_bg = theme.seq_bg
        for widget in (self.workspace, self.workspace.left_panel, self.workspace.splitter):
            palette = widget.palette()
            palette.setBrush(QPalette.Window, QBrush(target_bg))
            widget.setAutoFillBackground(True)
            widget.setPalette(palette)

        color_style_manager.apply_theme(theme.name)
        annotation_style_manager.apply_theme(theme.name)
        apply_scrollbar_style(self.workspace.sequence_viewer)
        self.workspace.update()

