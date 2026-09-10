"""MCP Server setup and tool registration"""

import logging
from mcp.server.fastmcp import FastMCP

from .config import config
from .database import db_pool

logger = logging.getLogger(__name__)


def create_mcp_server() -> FastMCP:
    """Create and configure the MCP server with all tools"""
    import sys
    sys.path.insert(0, '.')  # Make sure tools module can be imported
    
    from . import tools
    
    mcp = FastMCP(
        name=config.server.mcp_name,
        instructions="HTTP interface for PostgreSQL MCP Server",
    )
    
    # Register all tools
    mcp.add_tool(tools.execute_query)
    mcp.add_tool(tools.list_schemas)
    mcp.add_tool(tools.list_tables)
    mcp.add_tool(tools.describe_table)
    mcp.add_tool(tools.get_table_count)
    mcp.add_tool(tools.get_table_indexes)
    mcp.add_tool(tools.get_version)
    mcp.add_tool(tools.list_all_tables)
    mcp.add_tool(tools.explain_query)
    mcp.add_tool(tools.get_query_statistics)
    mcp.add_tool(tools.list_roles)
    mcp.add_tool(tools.list_grants)
    
    # Store db_pool reference for tools
    tools.db_pool = db_pool
    
    return mcp
