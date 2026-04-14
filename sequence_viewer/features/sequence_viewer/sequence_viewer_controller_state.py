from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from PyQt5.QtCore import QPoint


@dataclass
class MouseSelectionState:
    is_selecting: bool = False
    press_pos: Optional[QPoint] = None
    press_scene_col: Optional[int] = None
    press_scene_row: Optional[int] = None
    drag_started: bool = False
    drag_end_row: Optional[int] = None
    last_notified_row_range: Optional[tuple[int, int]] = None


@dataclass
class ZoomState:
    wheel_zoom_streak_dir: Optional[int] = None
    wheel_zoom_streak_len: int = 0


@dataclass
class TooltipState:
    last_sel_range: Optional[tuple[int, int, int, int]] = None
