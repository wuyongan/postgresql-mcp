"""Dynamic tool loader - discovers and registers tool functions from .py files."""

import importlib
import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


class ToolLoader:
    """Discovers and manages dynamic MCP tool registration."""

    def __init__(self, mcp_server):
        """
        Args:
            mcp_server: The FastMCP server instance.
        """
        self._mcp = mcp_server
        self._tool_modules: dict[str, str] = {}
        # map of module name -> loaded module object
        self._modules: dict[str, object] = {}

    def discover_tools(self) -> int:
        """Discover all tool modules in tools/ directory.

        Scans each .py file (except helpers like loader, watcher)
        and registers any async functions that have a __tool_name__ attribute.

        Returns:
            Number of tools registered.
        """
        tools_path = Path(__file__).parent
        count = 0

        for item in sorted(tools_path.iterdir()):
            if item.suffix != ".py" or item.name.startswith("_"):
                continue

            # Skip loader and watcher themselves
            if item.name in ("loader.py", "watcher.py"):
                continue

            module_name = item.stem
            if self._module_has_tool(module_name):
                self.register_module(module_name)
                count += 1

        return count

    def _module_has_tool(self, module_name: str) -> bool:
        """Check if a module file contains MCP tool functions."""
        try:
            # Import without caching to get fresh file content
            module = self._import_module(module_name)
            return hasattr(module, "__tools__")
        except Exception:
            return False

    def _import_module(self, module_name: str):
        """Import or reload a tool module without caching."""
        full_name = f"postgresql_mcp.tools.{module_name}"

        if full_name in sys.modules:
            # Force reload for hot-plug
            del sys.modules[full_name]

        module = importlib.import_module(full_name)
        return module

    def register_module(self, module_name: str) -> int:
        """Register a single tool module with the MCP server.

        Expects the module to define:
            __tools__: list of (function, tool_name, description) tuples

        Args:
            module_name: Name of the Python file (without .py).

        Returns:
            Number of tools registered from this module.
        """
        module = self._import_module(module_name)
        self._modules[module_name] = module

        if not hasattr(module, "__tools__"):
            logger.warning("Module %s has no __tools__, skipping", module_name)
            return 0

        tools: list[tuple] = module.__tools__  # type: ignore
        count = 0
        for func, name, desc in tools:
            self._mcp.add_tool(func, name=name, description=desc)
            self._tool_modules[name] = module_name
            count += 1
            logger.info("Registered tool '%s' from %s", name, module_name)

        return count

    def unregister_module(self, module_name: str) -> int:
        """Unregister all tools from a module.

        Args:
            module_name: Name of the Python file (without .py).

        Returns:
            Number of tools unregistered.
        """
        if module_name not in self._modules:
            return 0

        module = self._modules[module_name]
        tools = getattr(module, "__tools__", [])  # type: ignore
        count = 0

        for func, name, desc in tools:
            try:
                self._mcp.remove_tool(name)
                self._tool_modules.pop(name, None)
                count += 1
                logger.info("Unregistered tool '%s' from %s", name, module_name)
            except Exception:
                logger.warning("Failed to unregister tool '%s'", name)

        # Clean up cache
        full_name = f"postgresql_mcp.tools.{module_name}"
        sys.modules.pop(full_name, None)
        self._modules.pop(module_name, None)

        return count

    def reload_module(self, module_name: str) -> int:
        """Reload a module and update its registrations.

        Unregisters old tools, imports the new version, registers new tools.

        Args:
            module_name: Name of the Python file (without .py).

        Returns:
            Number of tools re-registered.
        """
        logger.info("Reloading module %s", module_name)
        # Save old tools
        old_tools = list(self._tool_modules.items())

        self.unregister_module(module_name)
        return self.register_module(module_name)

    def get_loaded_modules(self) -> dict[str, str]:
        """Return {tool_name: module_name} for all currently loaded tools."""
        return dict(self._tool_modules)

    def is_hot_plug_mode(self) -> bool:
        """Return whether file watching is enabled."""
        return getattr(self._mcp, "_hotplug_enabled", False)


def create_tool_loader(mcp_server):
    """Create a ToolLoader instance for an MCP server."""
    loader = ToolLoader(mcp_server)
    return loader
