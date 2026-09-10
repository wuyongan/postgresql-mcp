"""SQL queries for table introspection"""

# Column metadata from information_schema
COLUMNS_INFO = """SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_schema::text = $1 AND table_name = $2
ORDER BY ordinal_position
"""

# Table OID lookup (supports regular + partition tables)
TABLE_OID = """SELECT c.oid
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = $1 AND c.relname = $2 AND c.relkind IN ('r', 'p')
"""

# Primary key columns
PRIMARY_KEYS = """SELECT a.attname
FROM pg_index i
JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
WHERE i.indrelid = $1 AND i.indisprimary
ORDER BY a.attnum
"""

# Table row count estimate
TABLE_COUNT = """SELECT c.reltuples::int AS approx_count
FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname::text = $1 AND c.relname = $2
"""

# Index information
INDEXES = """SELECT i.relname AS index_name, ix.indisunique AS is_unique,
       array_to_string(array_agg(a.attname), ',') AS columns
FROM pg_index ix
JOIN pg_class i ON i.oid = ix.indexrelid
JOIN pg_attribute a ON a.attrelid = ix.indrelid AND a.attnum = ANY(ix.indkey)
WHERE ix.indrelid = $1
GROUP BY i.relname, ix.indisunique
ORDER BY i.relname
"""

# List tables in a schema
TABLES_IN_SCHEMA = """SELECT c.relname AS table_name, c.reltuples::int AS approx_count
FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname::text = $1 AND c.relkind = 'r'
ORDER BY c.relname
"""

# Table OID lookup by schema (for foreign key / constraint work)
TABLE_OID_BY_SCHEMA = """SELECT c.relname, c.oid FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname::text = $1 AND c.relkind = 'r'
"""

table_queries = {
    "columns": COLUMNS_INFO,
    "table_oid": TABLE_OID,
    "primary_keys": PRIMARY_KEYS,
    "table_count": TABLE_COUNT,
    "indexes": INDEXES,
    "tables_in_schema": TABLES_IN_SCHEMA,
    "table_oid_by_schema": TABLE_OID_BY_SCHEMA,
}
