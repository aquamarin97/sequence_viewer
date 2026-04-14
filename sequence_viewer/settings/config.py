# sequence_viewer/settings/config.py
# settings/config.py
from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Dict
from pydantic import BaseModel, BaseSettings, Field, validator

DEFAULT_SETTINGS_PATH = Path(__file__).resolve().parent.parent / "data" / "default_settings.json"
DEFAULT_USER_CONFIG_PATH = Path.home() / ".sequence_viewer" / "config.json"

class ModeSettings(BaseModel):
    name: str
    visible_components: Dict[str, bool] = Field(default_factory=dict)
    line_thickness: int = 1
    additional_params: Dict[str, Any] = Field(default_factory=dict)

class ShowingModesSettings(BaseModel):
    alignment: ModeSettings
    coverage: ModeSettings
    variant: ModeSettings

class ColorPaletteSettings(BaseModel):
    background: str = "#FFFFFF"
    foreground: str = "#000000"
    highlights: Dict[str, str] = Field(default_factory=dict)

class DataSourceSettings(BaseModel):
    type: str = Field("file")
    config: Dict[str, Any] = Field(default_factory=dict)
    @validator("type")
    def validate_type(cls, value):
        if value not in {"file","api","database"}: raise ValueError(f"Unsupported: {value}")
        return value

class AppConfig(BaseSettings):
    color_palette: ColorPaletteSettings
    showing_modes: ShowingModesSettings
    data_source: DataSourceSettings
    user_config_path: Path = Field(default=DEFAULT_USER_CONFIG_PATH, exclude=True)

def _load_json_settings(path):
    with path.open("r", encoding="utf-8") as f: return json.load(f)

def _write_json_settings(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f: json.dump(data, f, indent=2)


