"""MCP Tools Package - Base tools for PostgreSQL operations"""

# SQL Execution
from .query import execute_query

# Schema Management
from .schema import list_all_tables, list_schemas

# Table Management
from .table import describe_table, get_table_count, get_table_indexes, list_tables

# Version
from .version import get_version

# Global db_pool reference (set by server.py)
db_pool = None

__all__ = [
    "db_pool",
    "describe_table",
    "execute_query",
    "get_table_count",
    "get_table_indexes",
    "get_version",
    "list_all_tables",
    "list_schemas",
    "list_tables",
]
