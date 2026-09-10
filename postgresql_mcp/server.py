"""MCP Server setup and tool registration with dynamic tool loading."""

import asyncio
import logging
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from . import tools
from .config import config
from .db import db_pool
from .tools.loader import ToolLoader
from .tools.watcher import ToolFileWatcher

logger = logging.getLogger(__name__)


# Track background tasks for graceful shutdown
_background_tasks = []


def create_mcp_server() -> FastMCP:
    """Create and configure the MCP server with all tools and hot-plug support.

    The server supports dynamic tool loading from the tools/ directory.
    New .py files are automatically discovered and registered at runtime.
    To disable, set HOTPLUG_ENABLED=false in .env.
    """
    mcp = FastMCP(
        name=config.server.mcp_name,
        instructions="HTTP interface for PostgreSQL MCP Server",
    )

    # Register all 8 base tools with MCP descriptions
    mcp.add_tool(tools.execute_query, description="Execute SQL queries (SELECT/INSERT/UPDATE/DELETE)")
    mcp.add_tool(tools.list_schemas, description="List all database schemas (excludes system schemas)")
    mcp.add_tool(tools.list_all_tables, description="List all tables across all schemas with approximate counts")
    mcp.add_tool(tools.list_tables, description="List tables in a specific schema")
    mcp.add_tool(tools.describe_table, description="Get table structure including columns, types, defaults, PKs")
    mcp.add_tool(tools.get_table_count, description="Get approximate row count for a table")
    mcp.add_tool(tools.get_table_indexes, description="Get index information for a table")
    mcp.add_tool(tools.get_version, description="Get PostgreSQL database version")

    # Inject db_pool reference into tools module
    tools.db_pool = db_pool

    # Set up dynamic tool loading
    _setup_hotplug(mcp)

    return mcp


def _setup_hotplug(mcp: FastMCP):
    """Set up dynamic tool loading from the tools/ directory."""
    enable_hotplug = config.server.enable_hotplug if hasattr(config.server, "enable_hotplug") else True

    if not enable_hotplug:
        logger.info("Hot-plug disabled")
        return

    # Create and start the tool loader
    loader = ToolLoader(mcp)

    # Discover and register any existing tool files
    count = loader.discover_tools()
    if count > 0:
        logger.info("Discovered %d dynamic tool module(s)", count)

    # Set up file watcher (runs in background)
    tools_path = Path(__file__).parent / "tools"
    if tools_path.is_dir():
        watcher = ToolFileWatcher(tools_path, loader)

        # Store references on tools module for access
        tools._tool_loader = loader
        tools._file_watcher = watcher

        # Mark MCP server as hot-plug enabled
        mcp._hotplug_enabled = True

        # Start watcher in background (don't block startup)
        task = asyncio.create_task(watcher.start())
        _background_tasks.append(task)

        logger.info("File watcher started for %s", tools_path)
        logger.info("Tools can be hot-plugged: add/remove .py files in tools/ directory")
    else:
        logger.warning("Tools directory not found: %s", tools_path)


async def shutdown_hotplug():
    """Gracefully stop the file watcher and clean up."""
    if tools._file_watcher:
        await tools._file_watcher.stop()
        logger.info("File watcher stopped")


def register_dynamic_tool(name: str, func, description: str = ""):
    """Register a single dynamic tool at runtime (callable from scripts).

    Args:
        name: Unique tool name.
        func: Async function to register.
        description: Tool description.
    """
    loader = getattr(tools, "_tool_loader", None)
    if not loader or not hasattr(loader, "_mcp"):
        logger.warning("Dynamic tool loader not available")
        return False

    loader._mcp.add_tool(func, name=name, description=description)
    logger.info("Dynamically registered tool: %s", name)
    return True


def unregister_dynamic_tool(name: str):
    """Unregister a dynamic tool by name."""
    loader = getattr(tools, "_tool_loader", None)
    if not loader or not hasattr(loader, "_mcp"):
        logger.warning("Dynamic tool loader not available")
        return False

    loader._mcp.remove_tool(name)
    logger.info("Dynamically unregistered tool: %s", name)
    return True


def list_dynamic_tools():
    """List all currently loaded dynamic tool modules."""
    loader = getattr(tools, "_tool_loader", None)
    if loader and hasattr(loader, "get_loaded_modules"):
        return loader.get_loaded_modules()
    return {}
