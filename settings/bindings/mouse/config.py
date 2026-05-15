from __future__ import annotations

import json
import os
from typing import Any, Optional

from settings.sequence_viewer.paths import DEFAULT_CONFIG_DIR


DEFAULT_THRESHOLDS: dict[str, int] = {
    "sequence_viewer": 4,
    "consensus_row": 4,
    "header_viewer": 6,
    "navigation_ruler": 3,
}

DEFAULT_ZOOM = {
    "base_factor": 1.22,
    "acceleration_factor": 1.06,
    "max_char_width": 90.0,
}

CONFIG_PATH = os.path.normpath(DEFAULT_CONFIG_DIR / "mouse_bindings.json")


class MouseBindingConfig:
    """Reads raw mouse binding configuration from disk."""

    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or CONFIG_PATH

    def load(self) -> dict[str, Any]:
        try:
            if os.path.isfile(self.config_path):
                with open(self.config_path, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
                    return data if isinstance(data, dict) else {}
        except Exception:
            pass
        return {}
