#!/usr/bin/env python3
"""PostgreSQL MCP Server - Entry point"""

import asyncio
import logging
import argparse
import os
from pathlib import Path

# Load .env file BEFORE importing config
try:
    from dotenv import load_dotenv
    dotenv_path = Path(__file__).parent / ".env"
    if dotenv_path.exists():
        load_dotenv(dotenv_path=dotenv_path)
        print(f"Loaded .env from {dotenv_path}")
except ImportError:
    pass  # python-dotenv not installed

from postgresql_mcp.config import config, DatabaseConfig, ServerConfig
from postgresql_mcp.database import db_pool
from postgresql_mcp.server import create_mcp_server

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("postgresql-mcp-http")


async def main():
    """Main entry point"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="PostgreSQL MCP HTTP Server")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to listen on")
    parser.add_argument("--db-host", type=str, help="PostgreSQL host")
    parser.add_argument("--db-port", type=int, help="PostgreSQL port")
    parser.add_argument("--db-name", type=str, help="PostgreSQL database")
    parser.add_argument("--db-user", type=str, help="PostgreSQL user")
    parser.add_argument("--db-password", type=str, help="PostgreSQL password")
    args = parser.parse_args()
    
    # Override config with command line args if provided
    if args.db_host:
        config.database.host = args.db_host
    if args.db_port:
        config.database.port = args.db_port
    if args.db_name:
        config.database.database = args.db_name
    if args.db_user:
        config.database.user = args.db_user
    if args.db_password:
        config.database.password = args.db_password
    if args.host:
        config.server.host = args.host
    if args.port:
        config.server.port = args.port
    
    logger.info("Starting PostgreSQL MCP Server v1.0.0")
    logger.info("DB: %s:%d/%s", config.database.host, config.database.port, config.database.database)
    logger.info("Server: %s:%d", config.server.host, config.server.port)
    
    # Initialize database pool
    await db_pool.init()
    
    try:
        # Create MCP server
        mcp = create_mcp_server()
        
        # Configure and start server
        mcp.settings.port = config.server.port
        mcp.settings.host = config.server.host
        
        logger.info("Starting PostgreSQL MCP server on %s:%d", config.server.host, config.server.port)
        await mcp.run_streamable_http_async()
    finally:
        # Cleanup
        await db_pool.close()
        logger.info("Server shutdown complete")


if __name__ == "__main__":
    asyncio.run(main())
