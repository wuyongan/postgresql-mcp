"""Table Management Tools"""

import logging

from .. import db
from ..common.formatting import rows_to_dicts
from ..common.response import error_result, ok_result
from ..queries.table import table_queries

logger = logging.getLogger(__name__)


def _resolve_schema(schema: str, schema_name: str | None = None) -> str:
    """Resolve schema name: prefer non-default value.

    MCP clients may send "schema" or "schema_name". Accept both.
    """
    if schema and schema != "public":
        return schema
    if schema_name and schema_name != "public":
        return schema_name
    return "public"


async def list_tables(schema: str = "public", schema_name: str | None = None) -> str:
    """Get list of tables under specified schema.

    Accepts both "schema" and "schema_name" parameters.

    Args:
        schema: Schema name (default: public).
        schema_name: Alternative parameter name for schema.

    Returns:
        JSON string with list of tables and approximate counts.
    """
    target_schema = _resolve_schema(schema, schema_name)
    try:
        async with db.db_pool.connection() as conn:
            rows = await conn.fetch(table_queries["tables_in_schema"], target_schema)
        tables = [{"name": r["table_name"], "approx_count": int(r["approx_count"] or 0)} for r in rows]
        return ok_result(
            {
                "tables": tables,
                "schema": target_schema,
                "count": len(tables),
            }
        )
    except Exception as e:
        logger.error("Failed to list tables: %s", e)
        return error_result(str(e))


async def describe_table(
    schema: str = "public",
    table_name: str | None = None,
    schema_name: str | None = None,
) -> str:
    """Describe table structure including columns, types, defaults,
    and primary keys.

    Args:
        schema: Schema name.
        table_name: Table name.
        schema_name: Alternative parameter name for schema.

    Returns:
        JSON string with table structure.
    """
    target_schema = _resolve_schema(schema, schema_name)
    try:
        async with db.db_pool.connection() as conn:
            # Step 1: Get column info
            cols = await conn.fetch(table_queries["columns"], target_schema, table_name)

            # Step 2: Resolve table OID for PK lookup (direct query, no scan)
            our_oid = await conn.fetchval(table_queries["table_oid"], target_schema, table_name)

            # Step 3: Get primary key columns
            pks = []
            if our_oid:
                pk_rows = await conn.fetch(table_queries["primary_keys"], our_oid)
                pks = [r["attname"] for r in pk_rows]

            # Step 4: Build column metadata
            columns_info = []
            plain_cols = rows_to_dicts(cols)
            for c in plain_cols:
                columns_info.append(
                    {
                        "name": c["column_name"],
                        "type": c["data_type"],
                        "nullable": c["is_nullable"] == "YES",
                        "default": str(c["column_default"]) if c["column_default"] else None,
                        "is_primary_key": c["column_name"] in pks,
                    }
                )

        return ok_result(
            {
                "table": table_name,
                "schema": target_schema,
                "columns": columns_info,
                "primary_keys": pks,
                "columns_count": len(columns_info),
            }
        )
    except Exception as e:
        logger.error("Failed to describe table: %s", e)
        return error_result(str(e))


async def get_table_count(
    schema: str = "public",
    table_name: str | None = None,
    schema_name: str | None = None,
) -> str:
    """Get approximate row count for a table.

    Args:
        schema: Schema name.
        table_name: Table name.
        schema_name: Alternative parameter name for schema.

    Returns:
        JSON string with row count.
    """
    target_schema = _resolve_schema(schema, schema_name)
    try:
        async with db.db_pool.connection() as conn:
            rows = await conn.fetch(table_queries["table_count"], target_schema, table_name)
        count = int(rows[0]["approx_count"]) if rows else 0
        return ok_result(
            {
                "table": table_name,
                "schema": target_schema,
                "count": count,
            }
        )
    except Exception as e:
        logger.error("Failed to get table count: %s", e)
        return error_result(str(e))


async def get_table_indexes(
    schema: str = "public",
    table_name: str | None = None,
    schema_name: str | None = None,
) -> str:
    """Get index information for a table.

    Supports both regular (relkind=r) and partitioned (relkind=p) tables.

    Args:
        schema: Schema name.
        table_name: Table name.
        schema_name: Alternative parameter name for schema.

    Returns:
        JSON string with index information.
    """
    target_schema = _resolve_schema(schema, schema_name)
    try:
        async with db.db_pool.connection() as conn:
            # Get table OID
            oid_result = await conn.fetchval(table_queries["table_oid"], target_schema, table_name)
            if oid_result is None:
                return error_result(f"Table not found: {target_schema}.{table_name}", log=False)

            # Get indexes
            rows = await conn.fetch(table_queries["indexes"], oid_result)
        indexes = [
            {
                "name": r["index_name"],
                "unique": r["is_unique"],
                "columns": r["columns"].split(",") if r["columns"] else [],
            }
            for r in rows
        ]

        return ok_result(
            {
                "table": table_name,
                "schema": target_schema,
                "indexes": indexes,
                "count": len(indexes),
            }
        )
    except Exception as e:
        logger.error("Failed to get table indexes: %s", e)
        return error_result(str(e))
