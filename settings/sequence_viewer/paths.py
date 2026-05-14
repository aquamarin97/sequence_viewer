"""Filesystem locations for Sequence Viewer defaults and assets."""

from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_DIR = PROJECT_ROOT / "config" / "defaults" / "sequence_viewer"
ASSETS_DIR = PROJECT_ROOT / "assets"
