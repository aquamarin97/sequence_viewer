from __future__ import annotations

from PyQt5.QtCore import Qt

from settings.bindings.mouse.bindings import BUILT_IN_BINDINGS, BUTTON, MODIFIER
from settings.bindings.mouse.types import (
    MouseBinding,
    MouseButton,
    SUPPORTED_MODIFIERS_MASK,
    parse_modifier,
    parse_mouse_button,
)


class MouseBindingResolver:
    """Resolves configured mouse bindings against Qt events."""

    def __init__(self, defaults: dict[tuple[str, str], dict[str, str]] | None = None):
        self._defaults = defaults or BUILT_IN_BINDINGS

    def raw_binding(self, data: dict, section: str, action_key: str) -> dict:
        raw = self._section(data, section).get(action_key, {})
        return dict(raw) if isinstance(raw, dict) else {}

    def binding(self, data: dict, section: str, action_key: str) -> MouseBinding:
        raw = self._binding_dict(data, section, action_key)
        button = parse_mouse_button(raw.get(BUTTON))
        modifier = parse_modifier(raw.get(MODIFIER))
        defaults = self._defaults.get((section, action_key), {})

        if button is None:
            button = parse_mouse_button(defaults.get(BUTTON)) or MouseButton.LEFT
        if modifier is None:
            modifier = parse_modifier(defaults.get(MODIFIER)) or int(Qt.NoModifier)

        return MouseBinding(
            button=button,
            modifier=modifier,
            gesture=str(raw.get("gesture", "")),
            description=str(raw.get("description", "")),
        )

    def matches(self, data: dict, section: str, action_key: str, qt_button, qt_modifiers) -> bool:
        if not self._has_binding(data, section, action_key):
            return False

        binding = self.binding(data, section, action_key)
        actual_modifiers = self._normalize_modifiers(qt_modifiers)
        if not self._button_matches(binding.button, qt_button):
            return False
        return actual_modifiers == binding.modifier

    def _binding_dict(self, data: dict, section: str, action_key: str) -> dict:
        raw = self.raw_binding(data, section, action_key)
        defaults = self._defaults.get((section, action_key), {})
        merged = dict(defaults)
        merged.update(raw)
        return merged

    def _section(self, data: dict, section: str) -> dict:
        section_data = data.get(section, {})
        return section_data if isinstance(section_data, dict) else {}

    def _has_binding(self, data: dict, section: str, action_key: str) -> bool:
        return (section, action_key) in self._defaults or bool(
            self.raw_binding(data, section, action_key)
        )

    def _normalize_modifiers(self, qt_modifiers) -> int:
        return int(qt_modifiers) & SUPPORTED_MODIFIERS_MASK

    def _button_matches(self, required_button: MouseButton, qt_button) -> bool:
        if required_button == MouseButton.WHEEL:
            return qt_button in (None, Qt.NoButton)
        if required_button == MouseButton.LEFT:
            return qt_button == Qt.LeftButton
        if required_button == MouseButton.RIGHT:
            return qt_button == Qt.RightButton
        if required_button == MouseButton.MIDDLE:
            return qt_button == Qt.MiddleButton
        if required_button == MouseButton.NONE:
            return qt_button in (None, Qt.NoButton)
        return False
