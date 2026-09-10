"""MCP Tools Package - Base tools for PostgreSQL operations"""

# SQL Execution
from .query import execute_query

# Schema Management
from .schema import list_schemas, list_all_tables

# Table Management
from .table import list_tables, describe_table, get_table_count, get_table_indexes

# Version
from .version import get_version

# Global db_pool reference (set by server.py)
db_pool = None

__all__ = [
    "execute_query",
    "list_schemas",
    "list_all_tables",
    "list_tables",
    "describe_table",
    "get_table_count",
    "get_table_indexes",
    "get_version",
    "db_pool",
]
