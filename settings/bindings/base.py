from __future__ import annotations

from typing import Any, Mapping, Optional

from PyQt5.QtCore import QObject, pyqtSignal


class BindingManager(QObject):
    """Base class for config-backed binding managers."""

    bindingsChanged = pyqtSignal()

    def __init__(self, config_path: Optional[str] = None):
        super().__init__()
        self._config_path = config_path
        self._data: dict[str, Any] = {}
        self._load()

    def reload(self):
        self._load()
        self.bindingsChanged.emit()

    def _load(self):
        """Load binding data into self._data."""
        raise NotImplementedError


class BindingRegistry:
    """Small registry for shared binding manager instances."""

    def __init__(self):
        self._managers: dict[str, BindingManager] = {}

    def register(self, name: str, manager: BindingManager):
        self._managers[name] = manager

    def get(self, name: str) -> BindingManager:
        return self._managers[name]

    def all(self) -> Mapping[str, BindingManager]:
        return dict(self._managers)
