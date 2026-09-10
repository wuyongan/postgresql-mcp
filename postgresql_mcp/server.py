"""MCP Server setup and tool registration"""

import logging
from mcp.server.fastmcp import FastMCP

from .config import config
from .db import db_pool
from . import tools

logger = logging.getLogger(__name__)


def create_mcp_server() -> FastMCP:
    """Create and configure the MCP server with all tools."""
    mcp = FastMCP(
        name=config.server.mcp_name,
        instructions="HTTP interface for PostgreSQL MCP Server",
    )

    # Register all 8 base tools
    mcp.add_tool(tools.execute_query)
    mcp.add_tool(tools.list_schemas)
    mcp.add_tool(tools.list_all_tables)
    mcp.add_tool(tools.list_tables)
    mcp.add_tool(tools.describe_table)
    mcp.add_tool(tools.get_table_count)
    mcp.add_tool(tools.get_table_indexes)
    mcp.add_tool(tools.get_version)

    # Inject db_pool reference into tools module
    tools.db_pool = db_pool

    return mcp
