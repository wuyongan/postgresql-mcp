"""SQL Query Execution Tool"""

import logging

from ..common.response import error_result, ok_result
from ..common.formatting import rows_to_dicts, truncate_rows
from .. import db

logger = logging.getLogger(__name__)


async def execute_query(sql: str, limit: int = 100) -> str:
    """Execute SQL query, supports SELECT/INSERT/UPDATE/DELETE.

    Args:
        sql: SQL query string (max 100,000 characters).
        limit: Maximum rows to return (default 100).

    Returns:
        JSON string with query results.
    """
    if not sql or not sql.strip():
        return error_result("SQL parameter is empty")

    if len(sql) > 100000:
        return error_result("SQL query too long (max 100,000 characters)")

    try:
        async with db.db_pool.connection() as conn:
            # Fetch and immediately convert to plain dicts while
            # connection is still valid (Bug 1/5 fix)
            rows = await conn.fetch(sql)

            if not rows:
                return ok_result({
                    "status": "ok",
                    "message": "Query returned no results",
                    "rows": [],
                    "count": 0,
                })

            # Convert asyncpg.Record objects to plain dicts NOW
            plain_rows = rows_to_dicts(rows)
            columns = list(rows[0].keys())

            # Truncate and return (all data is now plain dicts)
            display, count, truncated = truncate_rows(plain_rows, limit)
            return ok_result({
                "status": "ok",
                "columns": columns,
                "rows": display,
                "count": count,
                "truncated": truncated,
            })
    except Exception as e:
        logger.error("Query execution failed: %s", e)
        return error_result(str(e))
