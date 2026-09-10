"""SQL queries for schema introspection"""

# Exclude system schemas
SCHEMAS = """SELECT schema_name FROM information_schema.schemata
WHERE schema_name NOT IN ('information_schema', 'pg_catalog')
ORDER BY schema_name
"""

# Tables across all schemas
ALL_TABLES = """SELECT c.relname AS table_name, c.reltuples::int AS approx_count
FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname::text = $1 AND c.relkind = 'r'
ORDER BY c.relname
"""

# All non-system schemas
ALL_SCHEMAS = """SELECT schema_name FROM information_schema.schemata
WHERE schema_name NOT IN ('information_schema', 'pg_catalog')
ORDER BY schema_name
"""

schema_queries = {
    "list_schemas": SCHEMAS,
    "list_all_tables_query": ALL_TABLES,
    "all_schemas": ALL_SCHEMAS,
}
