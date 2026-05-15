from __future__ import annotations

from typing import Optional

from PyQt5.QtCore import Qt

from settings.bindings.base import BindingManager
from settings.bindings.mouse.config import DEFAULT_THRESHOLDS, DEFAULT_ZOOM, MouseBindingConfig
from settings.bindings.mouse.resolver import MouseBindingResolver
from settings.bindings.mouse.types import (
    AnnotationActions,
    ConsensusSpacerActions,
    HeaderActions,
    MouseAction,
    MouseContext,
    NavigationRulerActions,
    SequenceActions,
)
from settings.bindings.registry import register_binding_manager



class MouseBindingManager(BindingManager):
    """Config-backed mouse binding manager."""

    def __init__(self, config_path: Optional[str] = None):
        self._config = MouseBindingConfig(config_path)
        self._resolver = MouseBindingResolver()
        super().__init__(self._config.config_path)

    def resolve_sequence_drag(self, qt_modifiers, qt_button=Qt.LeftButton) -> MouseAction:
        if self._matches_binding(
            MouseContext.SEQUENCE_VIEW,
            SequenceActions.DRAG_SELECT_ADDITIVE,
            qt_button,
            qt_modifiers,
        ):
            return MouseAction.DRAG_SELECT_ADDITIVE
        if self._matches_binding(
            MouseContext.SEQUENCE_VIEW,
            SequenceActions.DRAG_SELECT,
            qt_button,
            qt_modifiers,
        ):
            return MouseAction.DRAG_SELECT
        return MouseAction.NONE

    def resolve_sequence_click(self, qt_modifiers, qt_button=Qt.LeftButton) -> MouseAction:
        if self._matches_binding(
            MouseContext.SEQUENCE_VIEW,
            SequenceActions.GUIDE_TOGGLE,
            qt_button,
            qt_modifiers,
        ):
            return MouseAction.GUIDE_TOGGLE
        if self._matches_binding(
            MouseContext.SEQUENCE_VIEW,
            SequenceActions.GUIDE_SET,
            qt_button,
            qt_modifiers,
        ):
            return MouseAction.GUIDE_SET
        return MouseAction.NONE

    def is_zoom_event(self, qt_modifiers, qt_button=Qt.NoButton) -> bool:
        return self._matches_binding(
            MouseContext.SEQUENCE_VIEW,
            SequenceActions.ZOOM,
            qt_button,
            qt_modifiers,
        )

    def is_h_scroll_event(self, qt_modifiers, qt_button=Qt.NoButton) -> bool:
        return self._matches_binding(
            MouseContext.SEQUENCE_VIEW,
            SequenceActions.H_SCROLL,
            qt_button,
            qt_modifiers,
        )

    def resolve_header_click(self, qt_modifiers, qt_button=Qt.LeftButton) -> MouseAction:
        if self._matches_binding(
            MouseContext.HEADER_VIEW,
            HeaderActions.ROW_MULTI_SELECT,
            qt_button,
            qt_modifiers,
        ):
            return MouseAction.ROW_MULTI_SELECT
        if self._matches_binding(
            MouseContext.HEADER_VIEW,
            HeaderActions.ROW_RANGE_SELECT,
            qt_button,
            qt_modifiers,
        ):
            return MouseAction.ROW_RANGE_SELECT
        if self._matches_binding(
            MouseContext.HEADER_VIEW,
            HeaderActions.ROW_SELECT,
            qt_button,
            qt_modifiers,
        ):
            return MouseAction.ROW_SELECT
        return MouseAction.NONE

    def is_header_reorder_event(self, qt_modifiers, qt_button=Qt.LeftButton) -> bool:
        return self._matches_binding(
            MouseContext.HEADER_VIEW,
            HeaderActions.ROW_REORDER,
            qt_button,
            qt_modifiers,
        )

    def is_navigation_zoom_to_range_event(self, qt_modifiers, qt_button=Qt.LeftButton) -> bool:
        return self._matches_binding(
            MouseContext.NAVIGATION_RULER,
            NavigationRulerActions.ZOOM_TO_RANGE,
            qt_button,
            qt_modifiers,
        )

    def is_navigation_scroll_to_event(self, qt_modifiers, qt_button=Qt.LeftButton) -> bool:
        return self._matches_binding(
            MouseContext.NAVIGATION_RULER,
            NavigationRulerActions.SCROLL_TO,
            qt_button,
            qt_modifiers,
        )

    def resolve_annotation_click(self, qt_modifiers, qt_button=Qt.LeftButton) -> MouseAction:
        if self._matches_binding(
            MouseContext.ANNOTATION_VIEW,
            AnnotationActions.MULTI_SELECT,
            qt_button,
            qt_modifiers,
        ):
            return MouseAction.ANNOTATION_MULTI_SELECT
        if self._matches_binding(
            MouseContext.ANNOTATION_VIEW,
            AnnotationActions.SELECT,
            qt_button,
            qt_modifiers,
        ):
            return MouseAction.ANNOTATION_SELECT
        return MouseAction.NONE

    def is_annotation_edit_event(self, qt_modifiers, qt_button=Qt.LeftButton) -> bool:
        return self._matches_binding(
            MouseContext.ANNOTATION_VIEW,
            AnnotationActions.EDIT,
            qt_button,
            qt_modifiers,
        )

    def resolve_consensus_spacer_click(self, qt_modifiers, qt_button=Qt.LeftButton) -> MouseAction:
        if self._matches_binding(
            MouseContext.CONSENSUS_SPACER,
            ConsensusSpacerActions.SELECT_ALL_ADDITIVE,
            qt_button,
            qt_modifiers,
        ):
            return MouseAction.CONSENSUS_SELECT_ADDITIVE
        if self._matches_binding(
            MouseContext.CONSENSUS_SPACER,
            ConsensusSpacerActions.SELECT_ALL,
            qt_button,
            qt_modifiers,
        ):
            return MouseAction.CONSENSUS_SELECT_ALL
        return MouseAction.NONE

    def is_consensus_spacer_edit_event(self, qt_modifiers, qt_button=Qt.LeftButton) -> bool:
        return self._matches_binding(
            MouseContext.CONSENSUS_SPACER,
            ConsensusSpacerActions.EDIT_LABEL,
            qt_button,
            qt_modifiers,
        )

    def drag_threshold(self, context: str) -> int:
        return int(
            self._data
            .get("drag_thresholds_px", {})
            .get(context, DEFAULT_THRESHOLDS.get(context, 4))
        )

    @property
    def zoom_base_factor(self) -> float:
        return float(self._data.get("zoom", {}).get("base_factor", DEFAULT_ZOOM["base_factor"]))

    @property
    def zoom_accel_factor(self) -> float:
        return float(
            self._data.get("zoom", {}).get("acceleration_factor", DEFAULT_ZOOM["acceleration_factor"])
        )

    @property
    def zoom_max_char_width(self) -> float:
        return float(
            self._data.get("zoom", {}).get("max_char_width", DEFAULT_ZOOM["max_char_width"])
        )

    def raw_binding(self, section: str, action_key: str) -> dict:
        return self._resolver.raw_binding(self._data, self._context_value(section), action_key)

    def _load(self):
        self._data = self._config.load()

    def _matches_binding(
        self,
        section: MouseContext | str,
        action_key: str,
        qt_button,
        qt_modifiers,
    ) -> bool:
        return self._resolver.matches(
            self._data,
            self._context_value(section),
            action_key,
            qt_button,
            qt_modifiers,
        )

    def _context_value(self, section: MouseContext | str) -> str:
        return section.value if isinstance(section, MouseContext) else str(section)


mouse_binding_manager = MouseBindingManager()
register_binding_manager("mouse", mouse_binding_manager)
