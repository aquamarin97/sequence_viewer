"""
Immutable accessors for showing mode configurations.

The :class:`ShowingModes` helper exposes read-only access to the visual presets
loaded by :class:`settings.config.AppConfig`. Each mode is returned as a mapping
proxy to prevent accidental mutation at call sites.
"""
from __future__ import annotations

from types import MappingProxyType
from typing import Mapping

from .config import AppConfig, ModeSettings


class ShowingModes:
    """Provide immutable showing mode presets from ``AppConfig``."""

    def __init__(self, config: AppConfig):
        self._config = config

    @staticmethod
    def _to_mapping(settings: ModeSettings) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "name": settings.name,
                "visible_components": dict(settings.visible_components),
                "line_thickness": settings.line_thickness,
                "additional_params": dict(settings.additional_params),
            }
        )

    def alignment_mode(self) -> Mapping[str, object]:
        return self._to_mapping(self._config.showing_modes.alignment)

    def coverage_mode(self) -> Mapping[str, object]:
        return self._to_mapping(self._config.showing_modes.coverage)

    def variant_mode(self) -> Mapping[str, object]:
        return self._to_mapping(self._config.showing_modes.variant)