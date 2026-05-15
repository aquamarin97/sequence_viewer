from __future__ import annotations

from settings.bindings.base import BindingManager, BindingRegistry


binding_registry = BindingRegistry()


def register_binding_manager(name: str, manager: BindingManager):
    binding_registry.register(name, manager)


def get_binding_manager(name: str) -> BindingManager:
    return binding_registry.get(name)
