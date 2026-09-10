"""Schema Management Tools"""

import logging

from ..common.response import error_result, ok_result
from ..common.formatting import rows_to_dicts
from ..queries.schema import schema_queries
from .. import db

logger = logging.getLogger(__name__)


async def list_schemas() -> str:
    """Get list of database schemas.

    Excludes information_schema and pg_catalog.

    Returns:
        JSON string with list of schemas.
    """
    try:
        async with db.db_pool.connection() as conn:
            rows = await conn.fetch(schema_queries["list_schemas"])
        schemas = [r["schema_name"] for r in rows]
        return ok_result({"schemas": schemas, "count": len(schemas)})
    except Exception as e:
        logger.error("Failed to list schemas: %s", e)
        return error_result(str(e))


async def list_all_tables() -> str:
    """Get all tables under all schemas.

    All records are consumed inside the async with block to avoid
    accessing them after the connection returns to the pool.

    Returns:
        JSON string with all tables grouped by schema.
    """
    try:
        async with db.db_pool.connection() as conn:
            # Fetch schemas first
            schema_rows = await conn.fetch(schema_queries["all_schemas"])
        schemas = [r["schema_name"] for r in schema_rows]

        all_tables = []
        # Fetch tables for each schema
        # Note: each async with creates a NEW connection from pool
        # because the loop can be long and we need to be safe
        for schema in schemas:
            async with db.db_pool.connection() as conn:
                rows = await conn.fetch(
                    schema_queries["list_all_tables_query"], schema
                )
                # Convert to plain dicts inside the connection scope
                plain_rows = rows_to_dicts(rows)
                for r in plain_rows:
                    all_tables.append({
                        "schema": schema,
                        "name": r["table_name"],
                        "approx_count": int(r["approx_count"] or 0),
                    })

        return ok_result({
            "schemas": schemas,
            "tables": all_tables,
            "total_count": len(all_tables),
        })
    except Exception as e:
        logger.error("Failed to list all tables: %s", e)
        return error_result(str(e))
