"""SQL Query Execution Tool"""

import logging

from .. import db
from ..common.formatting import rows_to_dicts, truncate_rows
from ..common.response import error_result, ok_result
from ..config import config

logger = logging.getLogger(__name__)


async def execute_query(sql: str, limit: int | None = None) -> str:
    """Execute SQL query, supports SELECT/INSERT/UPDATE/DELETE.

    Args:
        sql: SQL query string.
        limit: Maximum rows to return (default: config.result_limit).

    Returns:
        JSON string with query results.
    """
    if not sql or not sql.strip():
        return error_result("SQL parameter is empty")

    max_size = getattr(config.server, "max_query_size", 100000)
    if len(sql) > max_size:
        return error_result(f"SQL query too long (max {max_size:,} characters)")

    default_limit = getattr(config.server, "result_limit", 1000)
    if limit is None:
        limit = default_limit

    try:
        async with db.db_pool.connection() as conn:
            # Fetch and immediately convert to plain dicts while
            # connection is still valid (Bug 1/5 fix)
            rows = await conn.fetch(sql)

            if not rows:
                return ok_result(
                    {
                        "status": "ok",
                        "message": "Query returned no results",
                        "rows": [],
                        "count": 0,
                    }
                )

            # Convert asyncpg.Record objects to plain dicts NOW
            plain_rows = rows_to_dicts(rows)
            columns = list(rows[0].keys())

            # Truncate and return (all data is now plain dicts)
            display, count, truncated = truncate_rows(plain_rows, limit)
            return ok_result(
                {
                    "status": "ok",
                    "columns": columns,
                    "rows": display,
                    "count": count,
                    "truncated": truncated,
                }
            )
    except Exception as e:
        logger.error("Query execution failed: %s", e)
        return error_result(str(e))
