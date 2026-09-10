"""Utility functions"""

import json
from typing import Any


def format_query_result(rows: list, limit: int = 1000) -> dict:
    """Format query result with pagination"""
    if not rows:
        return {
            "status": "ok",
            "rows": [],
            "count": 0,
            "total_count": 0,
            "truncated": False,
        }
    
    columns = list(rows[0].keys())
    display_rows = rows[:limit]
    
    # Convert all values to JSON-serializable types
    result_rows = []
    for row in rows[:limit]:
        result_rows.append({
            col: (None if val is None else str(val))
            for col, val in row.items()
        })
    
    truncated = len(rows) > limit
    
    return {
        "status": "ok",
        "columns": columns,
        "rows": result_rows,
        "count": len(result_rows),
        "total_count": len(rows),
        "truncated": truncated,
    }


def format_error(error: Exception, message: str = "Query failed") -> str:
    """Format error response as JSON"""
    return json.dumps({
        "status": "error",
        "message": f"{message}: {str(error)}",
    }, ensure_ascii=False, default=str)


def create_safe_pool_connection():
    """Create a standalone connection (not from pool)"""
    import asyncpg
    from .config import config
    
    db_config = config.database
    return asyncpg.connect(
        host=db_config.host,
        port=db_config.port,
        database=db_config.database,
        user=db_config.user,
        password=db_config.password,
    )


async def create_safe_pool_connection_async():
    """Create a standalone async connection (not from pool)"""
    import asyncpg
    from .config import config
    
    db_config = config.database
    return await asyncpg.connect(
        host=db_config.host,
        port=db_config.port,
        database=db_config.database,
        user=db_config.user,
        password=db_config.password,
    )
