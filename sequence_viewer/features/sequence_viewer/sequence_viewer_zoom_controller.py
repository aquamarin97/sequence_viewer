from __future__ import annotations

from math import pow

from sequence_viewer.settings.mouse_binding_manager import mouse_binding_manager

from .sequence_viewer_controller_state import ZoomState


class SequenceViewerZoomController:
    def __init__(self, model, view, tooltip_controller) -> None:
        self._model = model
        self._view = view
        self._tooltip_controller = tooltip_controller
        self._state = ZoomState()

    @property
    def wheel_zoom_streak_dir(self):
        return self._state.wheel_zoom_streak_dir

    @property
    def wheel_zoom_streak_len(self) -> int:
        return self._state.wheel_zoom_streak_len

    def clear(self) -> None:
        self._state.wheel_zoom_streak_dir = None
        self._state.wheel_zoom_streak_len = 0

    def handle_wheel_event(self, event) -> bool:
        if mouse_binding_manager.is_h_scroll_event(event.modifiers()):
            return self._handle_horizontal_scroll(event)
        if not mouse_binding_manager.is_zoom_event(event.modifiers()):
            return False
        return self._handle_zoom(event)

    def _handle_horizontal_scroll(self, event) -> bool:
        delta = event.angleDelta().y()
        if delta == 0:
            delta = event.angleDelta().x()
        if delta != 0:
            self._tooltip_controller.clear_panel()
            scrollbar = self._view.horizontalScrollBar()
            step = max(1, int(self._view._effective_char_width() * 3))
            scrollbar.setValue(scrollbar.value() - int(delta / 120.0 * step))
        return True

    def _handle_zoom(self, event) -> bool:
        delta = event.angleDelta().y()
        if delta == 0 or not self._view.sequence_items:
            return True

        self._tooltip_controller.clear_panel()
        steps = delta / 120.0
        direction = 1 if steps > 0 else -1
        self._update_zoom_streak(direction)

        view_width_px = float(self._view.viewport().width())
        if view_width_px <= 0:
            return True

        current_cw = self._view.current_char_width()
        if current_cw <= 0:
            current_cw = max(self._view.char_width, 0.001)

        center_nt = self._model.get_selection_center_nt()
        if center_nt is None:
            old_left_px = float(self._view.horizontalScrollBar().value())
            cursor_x = float(event.pos().x())
            center_nt = (old_left_px + cursor_x) / current_cw

        target_cw = self._compute_target_char_width(current_cw, steps, direction)
        if abs(target_cw - current_cw) < 0.0001:
            return True

        self._view.start_zoom_animation(
            target_char_width=target_cw,
            center_nt=center_nt,
            view_width_px=view_width_px,
        )
        return True

    def _update_zoom_streak(self, direction: int) -> None:
        if self._state.wheel_zoom_streak_dir == direction:
            self._state.wheel_zoom_streak_len += 1
        else:
            self._state.wheel_zoom_streak_dir = direction
            self._state.wheel_zoom_streak_len = 1

    def _compute_target_char_width(self, current_cw: float, steps: float, direction: int) -> float:
        streak_boost = pow(
            mouse_binding_manager.zoom_accel_factor,
            max(0, self._state.wheel_zoom_streak_len - 1),
        )
        per_step_factor = mouse_binding_manager.zoom_base_factor * streak_boost
        magnitude_factor = pow(per_step_factor, abs(steps))
        factor = magnitude_factor if direction > 0 else 1.0 / magnitude_factor
        return max(
            self._view.compute_min_char_width(),
            min(current_cw * factor, mouse_binding_manager.zoom_max_char_width),
        )
