from __future__ import annotations
from PyQt5.QtCore import QTimer


class ScrollInertiaMixin:
    _FRICTION = 0.85
    _MIN_VEL = 0.5

    def _init_scroll_inertia(self) -> None:
        self._inertia_vel_x = 0.0
        self._inertia_vel_y = 0.0
        self._inertia_rem_x = 0.0
        self._inertia_rem_y = 0.0
        self._inertia_timer = QTimer(self)
        self._inertia_timer.setInterval(16)
        self._inertia_timer.timeout.connect(self._tick_scroll_inertia)

    def _add_scroll_impulse(self, dx: float, dy: float) -> None:
        self._inertia_vel_x += dx
        self._inertia_vel_y += dy
        if not self._inertia_timer.isActive():
            self._inertia_timer.start()

    def stop_scroll_inertia(self) -> None:
        self._inertia_timer.stop()
        self._inertia_vel_x = 0.0
        self._inertia_vel_y = 0.0
        self._inertia_rem_x = 0.0
        self._inertia_rem_y = 0.0

    def _tick_scroll_inertia(self) -> None:
        if self._inertia_vel_x != 0.0:
            total = self._inertia_vel_x + self._inertia_rem_x
            step = int(total)
            self._inertia_rem_x = total - step
            if step:
                hbar = self.horizontalScrollBar()
                hbar.setValue(hbar.value() + step)
            self._inertia_vel_x *= self._FRICTION
            if abs(self._inertia_vel_x) < self._MIN_VEL:
                self._inertia_vel_x = 0.0
                self._inertia_rem_x = 0.0

        if self._inertia_vel_y != 0.0:
            total = self._inertia_vel_y + self._inertia_rem_y
            step = int(total)
            self._inertia_rem_y = total - step
            if step:
                vbar = self.verticalScrollBar()
                vbar.setValue(vbar.value() + step)
            self._inertia_vel_y *= self._FRICTION
            if abs(self._inertia_vel_y) < self._MIN_VEL:
                self._inertia_vel_y = 0.0
                self._inertia_rem_y = 0.0

        if self._inertia_vel_x == 0.0 and self._inertia_vel_y == 0.0:
            self._inertia_timer.stop()
