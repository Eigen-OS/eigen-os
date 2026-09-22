"""Driver plugin discovery and construction.

Plugins are exposed through the ``eigen_os.driver_plugins`` entry-point group.
The driver-manager does not know concrete backend implementations.
"""

from __future__ import annotations

import importlib
import importlib.metadata
import logging
import os
from collections.abc import Callable
from typing import Any

from .base_driver import BaseDriver

_LOG = logging.getLogger("driver_manager.plugins")

DriverFactory = Callable[..., BaseDriver]

# The simulator is shipped by this package. Keep a source-tree fallback so
# running pytest from a checkout does not depend on editable-install metadata.
_BUILTIN_FACTORIES: dict[str, str] = {
    "aqo-simulator": "driver_manager.simulator_driver:create_plugin",
}


def _enabled(name: str) -> bool:
    value = os.getenv(
        f"DRIVER_MANAGER_PLUGIN_{name.upper().replace('-', '_')}_ENABLED",
        "true" if name == "aqo-simulator" else "false",
    )
    return value.lower() in {"1", "true", "yes", "on"}


def _plugin_config(name: str) -> dict[str, str]:
    prefix = f"DRIVER_MANAGER_PLUGIN_{name.upper().replace('-', '_')}_"
    return {
        key[len(prefix):].lower(): value
        for key, value in os.environ.items()
        if key.startswith(prefix) and key != f"{prefix}ENABLED"
    }


def _entry_points() -> dict[str, importlib.metadata.EntryPoint]:
    discovered = importlib.metadata.entry_points()
    selected = discovered.select(group="eigen_os.driver_plugins")
    return {entry.name: entry for entry in selected}


def _builtin_factory(name: str) -> DriverFactory | None:
    target = _BUILTIN_FACTORIES.get(name)
    if target is None:
        return None

    module_name, factory_name = target.split(":", 1)
    module = importlib.import_module(module_name)
    return getattr(module, factory_name)


def load_plugins(types_pb: Any) -> list[BaseDriver]:
    """Load enabled driver plugins from entry points and built-ins."""

    plugins: list[BaseDriver] = []
    entry_points = _entry_points()
    names = sorted(
        set(entry_points)
        | {name for name in _BUILTIN_FACTORIES if _enabled(name)}
    )

    for name in names:
        if not _enabled(name):
            continue

        try:
            entry_point = entry_points.get(name)
            factory = (
                entry_point.load()
                if entry_point is not None
                else _builtin_factory(name)
            )
            if factory is None:
                _LOG.warning(
                    "enabled driver plugin %s has no registered entry point",
                    name,
                )
                continue
            driver = factory(types_pb=types_pb)
            driver.initialize(config=_plugin_config(name))
        except Exception:
            _LOG.exception("failed to initialize driver plugin %s", name)
            raise

        plugins.append(driver)
        _LOG.info("loaded driver plugin %s as %s", name, getattr(driver, "name", name))

    if not plugins:
        raise RuntimeError("no driver plugins are enabled")

    return plugins
