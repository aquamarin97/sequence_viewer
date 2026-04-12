# settings/color_palette.py
from __future__ import annotations
from types import MappingProxyType
from typing import Optional
from .config import AppConfig, _write_json_settings

class ColorPalette:
    def __init__(self, config):
        self._config = config
        self._colors = MappingProxyType({"background":self._config.color_palette.background,"foreground":self._config.color_palette.foreground,**self._config.color_palette.highlights})
    def get_background_color(self): return self._colors.get("background","#FFFFFF")
    def get_feature_color(self, feature_name): return self._colors.get(feature_name)


