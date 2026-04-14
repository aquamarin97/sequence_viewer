# sequence_viewer/features/sequence_viewer/sequence_viewer_controller.py
from __future__ import annotations

from typing import List

from PyQt5.QtWidgets import QApplication

from .sequence_viewer_mouse_controller import SequenceViewerMouseController
from .sequence_viewer_tooltip_controller import (
    SequenceViewerHoverController,
    SequenceViewerTooltipController,
)
from .sequence_viewer_zoom_controller import SequenceViewerZoomController


class SequenceViewerController:
    """Facade that coordinates dedicated interaction sub-controllers."""

    def __init__(self, model, view, *, on_selection_changed=None, on_row_clicked=None):
        self._model = model
        self._view = view
        self._tooltip = SequenceViewerTooltipController(model, view)
        self._hover = SequenceViewerHoverController(model, view, self._tooltip)
        self._mouse = SequenceViewerMouseController(
            model,
            view,
            self._tooltip,
            self._hover,
            on_selection_changed=on_selection_changed,
            on_row_clicked=on_row_clicked,
        )
        self._zoom = SequenceViewerZoomController(model, view, self._tooltip)

    @property
    def _is_selecting(self) -> bool:
        return self._mouse.is_selecting

    @property
    def _drag_tooltip(self):
        return self._tooltip.drag_tooltip

    @property
    def _last_sel_range(self):
        return self._tooltip.last_sel_range

    @property
    def _v_guide_cols(self) -> List[int]:
        return self._mouse.v_guide_cols

    @_v_guide_cols.setter
    def _v_guide_cols(self, cols: List[int]) -> None:
        self._mouse.set_v_guides(cols)

    def add_sequence(self, sequence_string) -> None:
        self._model.add_sequence(sequence_string)
        self._view.add_sequence_item(sequence_string)

    def clear(self) -> None:
        self._tooltip.clear()
        self._model.clear_sequences()
        self._view.clear_items()
        self._mouse.clear()
        self._view.clear_caret()
        self._view.clear_hover_caret()
        self._view.clear_selection_dim_range()
        self._zoom.clear()
        self._mouse.notify_selection_changed()

    def copy_selection_to_clipboard(self) -> None:
        lines = []
        for item in self._view.sequence_items:
            if item.selection_range is not None:
                start, end = item.selection_range
                fragment = item.sequence[start:end]
                if fragment:
                    lines.append(fragment)
        if lines:
            QApplication.clipboard().setText("\n".join(lines))

    @property
    def v_guide_cols(self) -> List[int]:
        return self._mouse.v_guide_cols

    def set_v_guides(self, cols: List[int]) -> None:
        self._mouse.set_v_guides(cols)

    def clear_v_guides(self) -> None:
        self._mouse.clear_v_guides()

    def handle_mouse_press(self, event):
        return self._mouse.handle_mouse_press(event)

    def handle_mouse_move(self, event):
        return self._mouse.handle_mouse_move(event)

    def handle_mouse_release(self, event):
        return self._mouse.handle_mouse_release(event)

    def handle_wheel_event(self, event):
        return self._zoom.handle_wheel_event(event)

    def show_info_panel(self, row_start: int, row_end: int, col_start: int, col_end: int) -> None:
        self._tooltip.show_info_panel(row_start, row_end, col_start, col_end)
