from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from PyQt5.QtCore import Qt


class MouseContext(str, Enum):
    SEQUENCE_VIEW = "sequence_view"
    HEADER_VIEW = "header_view"
    NAVIGATION_RULER = "navigation_ruler"
    ANNOTATION_VIEW = "annotation_view"
    CONSENSUS_SPACER = "consensus_spacer"


class MouseButton(str, Enum):
    NONE = "None"
    LEFT = "Left"
    RIGHT = "Right"
    MIDDLE = "Middle"
    WHEEL = "Wheel"


class MouseAction(Enum):
    """Central catalog of mouse actions used across the app."""

    # Sequence / Consensus
    DRAG_SELECT = "drag_select"
    DRAG_SELECT_ADDITIVE = "drag_select_additive"
    GUIDE_SET = "guide_set"
    GUIDE_TOGGLE = "guide_toggle"
    ZOOM = "zoom"

    # Header
    ROW_SELECT = "row_select"
    ROW_MULTI_SELECT = "row_multi_select"
    ROW_RANGE_SELECT = "row_range_select"
    ROW_REORDER = "row_reorder"

    # Navigation ruler
    NAV_ZOOM_TO_RANGE = "nav_zoom_to_range"
    NAV_SCROLL_TO = "nav_scroll_to"

    # Annotation
    ANNOTATION_SELECT = "annotation_select"
    ANNOTATION_MULTI_SELECT = "annotation_multi_select"
    ANNOTATION_EDIT = "annotation_edit"

    # Consensus spacer
    CONSENSUS_SELECT_ALL = "consensus_select_all"
    CONSENSUS_SELECT_ADDITIVE = "consensus_select_additive"
    CONSENSUS_EDIT_LABEL = "consensus_edit_label"

    NONE = "none"


class SequenceActions:
    DRAG_SELECT = "drag_select"
    DRAG_SELECT_ADDITIVE = "drag_select_additive"
    GUIDE_SET = "guide_set"
    GUIDE_TOGGLE = "guide_toggle"
    ZOOM = "zoom"
    H_SCROLL = "h_scroll"


class HeaderActions:
    ROW_SELECT = "row_select"
    ROW_MULTI_SELECT = "row_multi_select"
    ROW_RANGE_SELECT = "row_range_select"
    ROW_REORDER = "row_reorder"


class NavigationRulerActions:
    ZOOM_TO_RANGE = "zoom_to_range"
    SCROLL_TO = "scroll_to"


class AnnotationActions:
    SELECT = "select"
    MULTI_SELECT = "multi_select"
    EDIT = "edit"


class ConsensusSpacerActions:
    SELECT_ALL = "select_all"
    SELECT_ALL_ADDITIVE = "select_all_additive"
    EDIT_LABEL = "edit_label"


@dataclass(frozen=True)
class MouseBinding:
    button: MouseButton = MouseButton.LEFT
    modifier: int = int(Qt.NoModifier)
    gesture: str = ""
    description: str = ""


MODIFIER_NAME_TO_QT: dict[str, int] = {
    "CTRL": int(Qt.ControlModifier),
    "CONTROL": int(Qt.ControlModifier),
    "SHIFT": int(Qt.ShiftModifier),
    "ALT": int(Qt.AltModifier),
}

SUPPORTED_MODIFIERS_MASK = int(Qt.ControlModifier | Qt.ShiftModifier | Qt.AltModifier)


def parse_modifier(value) -> Optional[int]:
    """Parse modifier strings independent of order, e.g. Ctrl+Shift or Shift+Ctrl."""
    if value is None:
        return int(Qt.NoModifier)
    if isinstance(value, int):
        return value & SUPPORTED_MODIFIERS_MASK

    text = str(value).strip()
    if not text or text.lower() == "none":
        return int(Qt.NoModifier)

    modifier = int(Qt.NoModifier)
    for part in text.replace(" ", "").split("+"):
        qt_modifier = MODIFIER_NAME_TO_QT.get(part.upper())
        if qt_modifier is None:
            return None
        modifier |= qt_modifier
    return modifier & SUPPORTED_MODIFIERS_MASK


def parse_mouse_button(value) -> Optional[MouseButton]:
    if isinstance(value, MouseButton):
        return value

    normalized = str(value or MouseButton.LEFT.value).strip().lower()
    for button in MouseButton:
        if button.value.lower() == normalized:
            return button
    return None
