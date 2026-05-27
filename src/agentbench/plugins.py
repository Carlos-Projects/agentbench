"""Plugin system for dynamically loading external benchmark suites.

The plugin system allows loading benchmark suites from:
- Built-in packages (agentbench.suites)
- Installed Python packages
- Local file system directories

Usage::

    from agentbench.plugins import PluginLoader

    loader = PluginLoader()
    plugins = loader.discover_builtin()
    # or
    plugins = loader.discover_directory("./my-suites")
    suite = plugins["my_suite"].create()
"""

from __future__ import annotations

import importlib
import importlib.util
import inspect
import pkgutil
from pathlib import Path
from typing import Any

from agentbench.logger import logger
from agentbench.suites.base import BaseSuite


class SuitePlugin:
    """Represents a dynamically loaded suite plugin.

    Attributes:
        name: Human-readable suite name.
        cls: The suite class (subclass of BaseSuite).
        source: Origin string (e.g., "builtin", "package:foo", "file:/path").
    """

    def __init__(self, name: str, cls: type[BaseSuite], source: str = "builtin"):
        self.name = name
        self.cls = cls
        self.source = source

    def create(self) -> BaseSuite:
        """Create an instance of the suite.

        Returns:
            An instantiated suite object.
        """
        return self.cls()


class PluginLoader:
    """Discovers and loads benchmark suite plugins from multiple sources.

    Supports loading from built-in suites, installed Python packages,
    and local directories containing Python files.
    """

    def __init__(self) -> None:
        self._plugins: dict[str, SuitePlugin] = {}

    def discover_builtin(self) -> dict[str, SuitePlugin]:
        """Discover built-in suites from :mod:`agentbench.suites`.

        Returns:
            Dict of suite name to :class:`SuitePlugin`.
        """
        from agentbench.suites import SUITE_REGISTRY

        for name, cls in SUITE_REGISTRY.items():
            self._plugins[name] = SuitePlugin(name, cls, source="builtin")
        return dict(self._plugins)

    def discover_package(self, package_name: str) -> dict[str, SuitePlugin]:
        """Discover suites from an installed Python package.

        Args:
            package_name: Python package name to search for suite modules.

        Returns:
            Dict of discovered :class:`SuitePlugin` objects.
        """
        try:
            package = importlib.import_module(package_name)
            path = getattr(package, "__path__", None)
            if not path:
                return {}

            for _importer, modname, ispkg in pkgutil.iter_modules(path):
                if ispkg:
                    continue
                module = importlib.import_module(f"{package_name}.{modname}")
                self._scan_module(module, source=f"package:{package_name}")

        except ImportError:
            pass

        return dict(self._plugins)

    def discover_directory(self, directory: str | Path) -> dict[str, SuitePlugin]:
        """Discover suites from Python files in a directory.

        Only loads plugins from directories that are subdirectories of
        the current working directory or an explicitly allowed path.
        This prevents arbitrary code execution from untrusted paths.

        Args:
            directory: Path to directory containing suite modules (``.py`` files).

        Returns:
            Dict of discovered :class:`SuitePlugin` objects.
        """
        try:
            from agentbench.utils.security import safe_resolve_path

            path = safe_resolve_path(directory)
        except PermissionError:
            logger.warning("Plugin directory blocked: %s is outside allowed paths", directory)
            return {}

        if not path.exists() or not path.is_dir():
            return {}

        for pyfile in sorted(path.glob("*.py")):
            if pyfile.name.startswith("_"):
                continue
            spec = importlib.util.spec_from_file_location(pyfile.stem, str(pyfile))
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                self._scan_module(module, source=f"file:{pyfile}")

        return dict(self._plugins)

    def _scan_module(self, module: Any, source: str = "unknown") -> None:
        for name, obj in inspect.getmembers(module, inspect.isclass):
            if issubclass(obj, BaseSuite) and obj is not BaseSuite:
                suite_name = getattr(obj, "name", name.lower())
                self._plugins[suite_name] = SuitePlugin(suite_name, obj, source=source)

    def get_plugin(self, name: str) -> SuitePlugin | None:
        """Get a plugin by name.

        Args:
            name: Suite name to look up.

        Returns:
            :class:`SuitePlugin` or ``None`` if not found.
        """
        return self._plugins.get(name)

    def list_plugins(self) -> list[SuitePlugin]:
        """List all discovered plugins.

        Returns:
            List of all :class:`SuitePlugin` objects.
        """
        return list(self._plugins.values())
