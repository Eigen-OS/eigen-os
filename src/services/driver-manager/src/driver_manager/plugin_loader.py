"""Driver plugin discovery and construction.

Plugins are exposed through the ``eigen_os.driver_plugins`` entry-point group.
The driver-manager does not know concrete backend implementations.
"""

from __future__ import annotations

import importlib.metadata
import logging
import os
from collections.abc import Callable
from typing import Any

from .base_driver import BaseDriver

_LOG = logging.getLogger("driver_manager.plugins")

DriverFactory = Callable[..., BaseDriver]


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


def load_plugins(types_pb: Any) -> list[BaseDriver]:
    """Load enabled driver plugins from Python package entry points."""

    plugins: list[BaseDriver] = []
    for name, entry_point in sorted(_entry_points().items()):
        if not _enabled(name):
            continue

        try:
            factory = entry_point.load()
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
