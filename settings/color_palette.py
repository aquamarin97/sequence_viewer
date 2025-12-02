"""
Color palette management for sequence_viewer.

The :class:`ColorPalette` class reads user-provided colors from
:class:`settings.config.AppConfig` while preserving defaults from the bundled
configuration. User updates can be persisted back to the user configuration
file, keeping the rest of the application decoupled from storage concerns.
"""
from __future__ import annotations

from types import MappingProxyType
from typing import Dict, Optional

from .config import AppConfig, _write_json_settings


class ColorPalette:
    """Access and mutate user-customizable colors."""

    def __init__(self, config: AppConfig):
        self._config = config
        # Cache to avoid repeated lookups and guarantee read-only access.
        self._colors = MappingProxyType(
            {
                "background": self._config.color_palette.background,
                "foreground": self._config.color_palette.foreground,
                **self._config.color_palette.highlights,
            }
        )

    def get_background_color(self) -> str:
        """Return the configured background color."""

        return self._colors.get("background", "#FFFFFF")

    def get_feature_color(self, feature_name: str) -> Optional[str]:
        """Return the color associated with a feature or None if missing."""

        return self._colors.get(feature_name)

    def set_custom_color(self, key: str, value: str) -> None:
        """Persist a custom color to the user configuration file.

        The change is written to disk immediately and reflected in the
        underlying :class:`AppConfig` instance.
        """

        updated_palette = dict(self._config.color_palette.highlights)
        if key in {"background", "foreground"}:
            setattr(self._config.color_palette, key, value)
        else:
            updated_palette[key] = value
            self._config.color_palette.highlights = updated_palette

        payload = self._config.dict(exclude={"user_config_path"})
        _write_json_settings(self._config.user_config_path, payload)
        self._colors = MappingProxyType(
            {
                "background": self._config.color_palette.background,
                "foreground": self._config.color_palette.foreground,
                **self._config.color_palette.highlights,
            }
        )