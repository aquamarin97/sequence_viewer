from __future__ import annotations

from sequence_viewer.settings.mouse_binding_manager import MouseAction, mouse_binding_manager


class HeaderSelectionHandler:
    def __init__(self, selection_model) -> None:
        self._selection_model = selection_model

    def handle_click(self, row: int, modifiers, item_count: int):
        action = mouse_binding_manager.resolve_header_click(modifiers)
        if action == MouseAction.ROW_MULTI_SELECT:
            return self._selection_model.handle_ctrl_click(row, item_count)
        if action == MouseAction.ROW_RANGE_SELECT:
            return self._selection_model.handle_shift_click(row, item_count)
        return self._selection_model.handle_click(row, item_count)

    def clear(self):
        return self._selection_model.clear()

    def select_all(self, item_count: int):
        return self._selection_model.select_all(item_count)
