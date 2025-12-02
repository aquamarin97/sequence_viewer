"""
Application configuration management for the sequence_viewer package.

This module exposes the ``AppConfig`` class which centralizes reading and
validating settings from multiple sources in the following precedence:

1. Environment variables (highest priority).
2. User configuration file (``~/.sequence_viewer/config.json`` by default).
3. Immutable default settings bundled with the package
   (``data/default_settings.json``).

The configuration is decomposed into focused sub-models to keep the codebase
extensible and easy to reason about when new settings are introduced.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from pydantic import BaseModel, BaseSettings, Field, validator


DEFAULT_SETTINGS_PATH = Path(__file__).resolve().parent.parent / "data" / "default_settings.json"
DEFAULT_USER_CONFIG_PATH = Path.home() / ".sequence_viewer" / "config.json"


class ModeSettings(BaseModel):
    """Visual configuration for a single showing mode."""

    name: str
    visible_components: Dict[str, bool] = Field(default_factory=dict)
    line_thickness: int = 1
    additional_params: Dict[str, Any] = Field(default_factory=dict)


class ShowingModesSettings(BaseModel):
    """Container for all showing modes."""

    alignment: ModeSettings
    coverage: ModeSettings
    variant: ModeSettings


class ColorPaletteSettings(BaseModel):
    """User-customizable colors with sensible defaults."""

    background: str = "#FFFFFF"
    foreground: str = "#000000"
    highlights: Dict[str, str] = Field(default_factory=dict)


class DataSourceSettings(BaseModel):
    """Configuration for data retrieval."""

    type: str = Field("file", description="Data source type: file, api, or database")
    config: Dict[str, Any] = Field(default_factory=dict)

    @validator("type")
    def validate_type(cls, value: str) -> str:
        allowed = {"file", "api", "database"}
        if value not in allowed:
            raise ValueError(f"Unsupported data source type '{value}'. Allowed: {allowed}")
        return value


class AppConfig(BaseSettings):
    """Central application configuration.

    The class leverages ``BaseSettings`` to merge environment variables,
    user overrides, and bundled defaults into a single typed interface.
    """

    color_palette: ColorPaletteSettings
    showing_modes: ShowingModesSettings
    data_source: DataSourceSettings

    # Tracks the resolved user configuration path so helper classes can persist
    # user edits (e.g., custom colors) back to disk.
    user_config_path: Path = Field(default=DEFAULT_USER_CONFIG_PATH, exclude=True)

    class Config:
        env_prefix = "SEQUENCE_VIEWER_"
        case_sensitive = False

        @classmethod
        def customise_sources(cls, init_settings, env_settings, file_secret_settings):
            return (
                env_settings,
                cls._user_settings_source,
                cls._default_settings_source,
                init_settings,
                file_secret_settings,
            )

        @staticmethod
        def _user_settings_source(settings: BaseSettings) -> Dict[str, Any]:
            path = getattr(settings, "user_config_path", DEFAULT_USER_CONFIG_PATH)
            if path.exists():
                return _load_json_settings(path)
            return {}

        @staticmethod
        def _default_settings_source(settings: BaseSettings) -> Dict[str, Any]:
            if DEFAULT_SETTINGS_PATH.exists():
                return _load_json_settings(DEFAULT_SETTINGS_PATH)
            return {}

    def save_user_settings(self) -> None:
        """Persist the current configuration to the user config path.

        Only stores serializable settings to keep the file lean.
        """

        payload = json.loads(self.json(exclude={"user_config_path"}))
        _write_json_settings(self.user_config_path, payload)


def _load_json_settings(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON in settings file '{path}'") from exc


def _write_json_settings(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)