from __future__ import annotations

import json
import os
from enum import Enum
from typing import Optional

from PyQt5.QtCore import QObject, Qt, pyqtSignal


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


_MODIFIER_STR_TO_QT: dict[str, int] = {
    "None": Qt.NoModifier,
    "Ctrl": Qt.ControlModifier,
    "Shift": Qt.ShiftModifier,
    "Alt": Qt.AltModifier,
    "Ctrl+Shift": Qt.ControlModifier | Qt.ShiftModifier,
}

_SUPPORTED_MODIFIERS_MASK = (
    Qt.ControlModifier | Qt.ShiftModifier | Qt.AltModifier
)

_BUILT_IN_BINDINGS: dict[tuple[str, str], dict[str, str]] = {
    ("sequence_view", "drag_select"): {"button": "Left", "modifier": "None"},
    ("sequence_view", "drag_select_additive"): {"button": "Left", "modifier": "Ctrl"},
    ("sequence_view", "guide_set"): {"button": "Left", "modifier": "None"},
    ("sequence_view", "guide_toggle"): {"button": "Left", "modifier": "Ctrl"},
    ("sequence_view", "zoom"): {"button": "Wheel", "modifier": "Ctrl"},
    ("sequence_view", "h_scroll"): {"button": "Wheel", "modifier": "Shift"},
    ("header_view", "row_select"): {"button": "Left", "modifier": "None"},
    ("header_view", "row_multi_select"): {"button": "Left", "modifier": "Ctrl"},
    ("header_view", "row_range_select"): {"button": "Left", "modifier": "Shift"},
    ("header_view", "row_reorder"): {"button": "Left", "modifier": "None"},
    ("navigation_ruler", "zoom_to_range"): {"button": "Left", "modifier": "None"},
    ("navigation_ruler", "scroll_to"): {"button": "Left", "modifier": "None"},
    ("annotation_view", "select"): {"button": "Left", "modifier": "None"},
    ("annotation_view", "multi_select"): {"button": "Left", "modifier": "Ctrl"},
    ("annotation_view", "edit"): {"button": "Left", "modifier": "None"},
    ("consensus_spacer", "select_all"): {"button": "Left", "modifier": "None"},
    ("consensus_spacer", "select_all_additive"): {"button": "Left", "modifier": "Ctrl"},
    ("consensus_spacer", "edit_label"): {"button": "Left", "modifier": "None"},
}

_DEFAULT_THRESHOLDS: dict[str, int] = {
    "sequence_viewer": 4,
    "consensus_row": 4,
    "header_viewer": 6,
    "navigation_ruler": 3,
}

_DEFAULT_ZOOM = {
    "base_factor": 1.22,
    "acceleration_factor": 1.06,
    "max_char_width": 90.0,
}

_CONFIG_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "data", "mouse_bindings.json")
)


class MouseBindingManager(QObject):
    """Config-backed mouse binding resolver."""

    bindingsChanged = pyqtSignal()

    def __init__(self, config_path: Optional[str] = None):
        super().__init__()
        self._config_path: str = config_path or _CONFIG_PATH
        self._data: dict = {}
        self._load()

    # ------------------------------------------------------------------
    # Sequence / consensus interactions
    # ------------------------------------------------------------------

    def resolve_sequence_drag(self, qt_modifiers, qt_button=Qt.LeftButton) -> MouseAction:
        if self._matches_binding("sequence_view", "drag_select_additive", qt_button, qt_modifiers):
            return MouseAction.DRAG_SELECT_ADDITIVE
        if self._matches_binding("sequence_view", "drag_select", qt_button, qt_modifiers):
            return MouseAction.DRAG_SELECT
        return MouseAction.NONE

    def resolve_sequence_click(self, qt_modifiers, qt_button=Qt.LeftButton) -> MouseAction:
        if self._matches_binding("sequence_view", "guide_toggle", qt_button, qt_modifiers):
            return MouseAction.GUIDE_TOGGLE
        if self._matches_binding("sequence_view", "guide_set", qt_button, qt_modifiers):
            return MouseAction.GUIDE_SET
        return MouseAction.NONE

    def is_zoom_event(self, qt_modifiers, qt_button=Qt.NoButton) -> bool:
        return self._matches_binding("sequence_view", "zoom", qt_button, qt_modifiers)

    def is_h_scroll_event(self, qt_modifiers, qt_button=Qt.NoButton) -> bool:
        return self._matches_binding("sequence_view", "h_scroll", qt_button, qt_modifiers)

    # ------------------------------------------------------------------
    # Header interactions
    # ------------------------------------------------------------------

    def resolve_header_click(self, qt_modifiers, qt_button=Qt.LeftButton) -> MouseAction:
        if self._matches_binding("header_view", "row_multi_select", qt_button, qt_modifiers):
            return MouseAction.ROW_MULTI_SELECT
        if self._matches_binding("header_view", "row_range_select", qt_button, qt_modifiers):
            return MouseAction.ROW_RANGE_SELECT
        if self._matches_binding("header_view", "row_select", qt_button, qt_modifiers):
            return MouseAction.ROW_SELECT
        return MouseAction.NONE

    def is_header_reorder_event(self, qt_modifiers, qt_button=Qt.LeftButton) -> bool:
        return self._matches_binding("header_view", "row_reorder", qt_button, qt_modifiers)

    # ------------------------------------------------------------------
    # Navigation ruler interactions
    # ------------------------------------------------------------------

    def is_navigation_zoom_to_range_event(self, qt_modifiers, qt_button=Qt.LeftButton) -> bool:
        return self._matches_binding("navigation_ruler", "zoom_to_range", qt_button, qt_modifiers)

    def is_navigation_scroll_to_event(self, qt_modifiers, qt_button=Qt.LeftButton) -> bool:
        return self._matches_binding("navigation_ruler", "scroll_to", qt_button, qt_modifiers)

    # ------------------------------------------------------------------
    # Annotation interactions
    # ------------------------------------------------------------------

    def resolve_annotation_click(self, qt_modifiers, qt_button=Qt.LeftButton) -> MouseAction:
        if self._matches_binding("annotation_view", "multi_select", qt_button, qt_modifiers):
            return MouseAction.ANNOTATION_MULTI_SELECT
        if self._matches_binding("annotation_view", "select", qt_button, qt_modifiers):
            return MouseAction.ANNOTATION_SELECT
        return MouseAction.NONE

    def is_annotation_edit_event(self, qt_modifiers, qt_button=Qt.LeftButton) -> bool:
        return self._matches_binding("annotation_view", "edit", qt_button, qt_modifiers)

    # ------------------------------------------------------------------
    # Consensus spacer interactions
    # ------------------------------------------------------------------

    def resolve_consensus_spacer_click(self, qt_modifiers, qt_button=Qt.LeftButton) -> MouseAction:
        if self._matches_binding("consensus_spacer", "select_all_additive", qt_button, qt_modifiers):
            return MouseAction.CONSENSUS_SELECT_ADDITIVE
        if self._matches_binding("consensus_spacer", "select_all", qt_button, qt_modifiers):
            return MouseAction.CONSENSUS_SELECT_ALL
        return MouseAction.NONE

    def is_consensus_spacer_edit_event(self, qt_modifiers, qt_button=Qt.LeftButton) -> bool:
        return self._matches_binding("consensus_spacer", "edit_label", qt_button, qt_modifiers)

    # ------------------------------------------------------------------
    # Thresholds / zoom settings
    # ------------------------------------------------------------------

    def drag_threshold(self, context: str) -> int:
        return int(
            self._data
            .get("drag_thresholds_px", {})
            .get(context, _DEFAULT_THRESHOLDS.get(context, 4))
        )

    @property
    def zoom_base_factor(self) -> float:
        return float(self._data.get("zoom", {}).get("base_factor", _DEFAULT_ZOOM["base_factor"]))

    @property
    def zoom_accel_factor(self) -> float:
        return float(
            self._data.get("zoom", {}).get("acceleration_factor", _DEFAULT_ZOOM["acceleration_factor"])
        )

    @property
    def zoom_max_char_width(self) -> float:
        return float(
            self._data.get("zoom", {}).get("max_char_width", _DEFAULT_ZOOM["max_char_width"])
        )

    def raw_binding(self, section: str, action_key: str) -> dict:
        return dict(self._data.get(section, {}).get(action_key, {}))

    def reload(self):
        self._load()
        self.bindingsChanged.emit()

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _load(self):
        try:
            if os.path.isfile(self._config_path):
                with open(self._config_path, "r", encoding="utf-8") as fh:
                    self._data = json.load(fh)
            else:
                self._data = {}
        except Exception:
            self._data = {}

    def _binding_dict(self, section: str, action_key: str) -> dict:
        raw = self._data.get(section, {}).get(action_key, {})
        defaults = _BUILT_IN_BINDINGS.get((section, action_key), {})
        merged = dict(defaults)
        if isinstance(raw, dict):
            merged.update(raw)
        return merged

    def _qt_modifier(self, section: str, action_key: str) -> int:
        raw_modifier = self._binding_dict(section, action_key).get("modifier", "None")
        return _MODIFIER_STR_TO_QT.get(raw_modifier, Qt.NoModifier)

    def _binding_button(self, section: str, action_key: str) -> str:
        return str(self._binding_dict(section, action_key).get("button", "Left"))

    def _normalize_modifiers(self, qt_modifiers) -> int:
        return int(qt_modifiers) & int(_SUPPORTED_MODIFIERS_MASK)

    def _matches_binding(self, section: str, action_key: str, qt_button, qt_modifiers) -> bool:
        required_button = self._binding_button(section, action_key)
        required_modifiers = self._qt_modifier(section, action_key)
        actual_modifiers = self._normalize_modifiers(qt_modifiers)
        if not self._button_matches(required_button, qt_button):
            return False
        if required_modifiers == Qt.NoModifier:
            return actual_modifiers == Qt.NoModifier
        return bool(actual_modifiers & required_modifiers)

    def _button_matches(self, required_button: str, qt_button) -> bool:
        if required_button == "Wheel":
            return qt_button in (None, Qt.NoButton)
        if required_button == "Left":
            return qt_button == Qt.LeftButton
        if required_button == "Right":
            return qt_button == Qt.RightButton
        if required_button == "Middle":
            return qt_button == Qt.MiddleButton
        if required_button == "None":
            return qt_button in (None, Qt.NoButton)
        return False


mouse_binding_manager = MouseBindingManager()


