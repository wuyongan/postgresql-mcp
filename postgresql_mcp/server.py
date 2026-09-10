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

    # Register all 8 base tools with MCP descriptions
    mcp.add_tool(tools.execute_query, description="Execute SQL queries (SELECT/INSERT/UPDATE/DELETE)")
    mcp.add_tool(tools.list_schemas, description="List all database schemas (excludes system schemas)")
    mcp.add_tool(tools.list_all_tables, description="List all tables across all schemas with approximate counts")
    mcp.add_tool(tools.list_tables, description="List tables in a specific schema")
    mcp.add_tool(tools.describe_table, description="Get table structure including columns, types, defaults, and primary keys")
    mcp.add_tool(tools.get_table_count, description="Get approximate row count for a table")
    mcp.add_tool(tools.get_table_indexes, description="Get index information for a table")
    mcp.add_tool(tools.get_version, description="Get PostgreSQL database version")

    # Inject db_pool reference into tools module
    tools.db_pool = db_pool

    return mcp
