"""PostgreSQL MCP Tools - All tool implementations"""

import json
import logging

logger = logging.getLogger(__name__)

# Forward imports - will be set up in server.py
db_pool = None


async def execute_query(sql: str, limit: int = 100) -> str:
    """Execute SQL query, supports SELECT/INSERT/UPDATE/DELETE"""
    if not sql or not sql.strip():
        return json.dumps({"status": "error", "message": "SQL parameter is empty"}, ensure_ascii=False)
    
    if len(sql) > 100000:
        return json.dumps({"status": "error", "message": "SQL query too long"}, ensure_ascii=False)
    
    async with db_pool.connection() as conn:
        try:
            rows = await conn.fetch(sql)
            if not rows:
                return json.dumps({
                    "status": "ok",
                    "message": "Query returned no results",
                    "rows": [],
                    "count": 0,
                }, ensure_ascii=False)
            
            columns = list(rows[0].keys())
            result_rows = [dict(row) for row in rows[:limit]]
            
            result = {
                "status": "ok",
                "columns": columns,
                "rows": result_rows,
                "count": len(result_rows),
            }
            
            text = json.dumps(result, ensure_ascii=False, default=str)
            if len(text) > 10000:
                text = text[:10000] + "\n... (data truncated)"
            return text
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False)


async def list_schemas() -> str:
    """Get list of database schemas"""
    async with db_pool.connection() as conn:
        try:
            rows = await conn.fetch("""
                SELECT schema_name FROM information_schema.schemata
                WHERE schema_name NOT IN ('information_schema', 'pg_catalog')
                ORDER BY schema_name
            """)
            schemas = [r["schema_name"] for r in rows]
            return json.dumps({"schemas": schemas, "count": len(schemas)}, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False)


async def list_tables(schema: str = "public") -> str:
    """Get list of tables under specified schema"""
    async with db_pool.connection() as conn:
        try:
            rows = await conn.fetch("""
                SELECT c.relname AS table_name, c.reltuples::int AS approx_count
                FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE n.nspname::text = $1 AND c.relkind = 'r'
                ORDER BY c.relname
            """, schema)
            tables = [{"name": r["table_name"], "approx_count": int(r["approx_count"] or 0)} 
                      for r in rows]
            return json.dumps({"tables": tables, "schema": schema, "count": len(tables)}, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False)


async def describe_table(schema: str, table_name: str) -> str:
    """Describe table structure including columns, types, defaults, primary and foreign keys"""
    async with db_pool.connection() as conn:
        try:
            cols = await conn.fetch("""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns
                WHERE table_schema::text = $1 AND table_name = $2
                ORDER BY ordinal_position
            """, schema, table_name)
            
            relnames = await conn.fetch("""
                SELECT c.relname, c.oid FROM pg_class c
                JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE n.nspname::text = $1 AND c.relkind = 'r'
            """, schema)
            
            oid_map = {r["relname"]: r["oid"] for r in relnames}
            our_oid = oid_map.get(table_name)
            
            pks = []
            if our_oid:
                pks = [r["attname"] for r in await conn.fetch("""
                    SELECT a.attname FROM pg_index i
                    JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
                    WHERE i.indrelid = $1 AND i.indisprimary ORDER BY a.attnum
                """, our_oid)]
            
            columns_info = []
            for c in cols:
                columns_info.append({
                    "name": c["column_name"],
                    "type": c["data_type"],
                    "nullable": c["is_nullable"] == "YES",
                    "default": str(c["column_default"]) if c["column_default"] else None,
                    "is_primary_key": c["column_name"] in pks,
                })
            
            return json.dumps({
                "table": table_name,
                "schema": schema,
                "columns": columns_info,
                "primary_keys": pks,
                "columns_count": len(columns_info),
            }, ensure_ascii=False, default=str)
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False)


async def get_table_count(schema: str, table_name: str) -> str:
    """Get row count for specified table"""
    async with db_pool.connection() as conn:
        try:
            rows = await conn.fetch("""
                SELECT c.reltuples::int AS approx_count
                FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE n.nspname::text = $1 AND c.relname = $2
            """, schema, table_name)
            count = int(rows[0]["approx_count"]) if rows else 0
            return json.dumps({"table": table_name, "schema": schema, "count": count}, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False)


async def get_table_indexes(schema: str, table_name: str) -> str:
    """Get index information for specified table (supports partitioned tables)"""
    async with db_pool.connection() as conn:
        try:
            # 修复：支持普通表 (relkind='r') 和分区表根表 (relkind='p')
            oid_row = await conn.fetchval("""
                SELECT c.oid
                FROM pg_class c
                JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE n.nspname = $1 AND c.relname = $2 AND c.relkind IN ('r', 'p')
            """, schema, table_name)
            
            if oid_row is None:
                return json.dumps({"status": "error", "message": f"Table not found: {schema}.{table_name}"}, ensure_ascii=False)
            
            our_oid = oid_row
            
            rows = await conn.fetch("""
                SELECT i.relname AS index_name, ix.indisunique AS is_unique,
                       array_to_string(array_agg(a.attname), ',') AS columns
                FROM pg_index ix JOIN pg_class i ON i.oid = ix.indexrelid
                JOIN pg_attribute a ON a.attrelid = ix.indrelid AND a.attnum = ANY(ix.indkey)
                WHERE ix.indrelid = $1
                GROUP BY i.relname, ix.indisunique ORDER BY i.relname
            """, our_oid)
            
            indexes = [{
                "name": r["index_name"],
                "unique": r["is_unique"],
                "columns": r["columns"].split(",") if r["columns"] else [],
            } for r in rows]
            
            return json.dumps({"table": table_name, "schema": schema, "indexes": indexes, "count": len(indexes)}, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False)


async def get_version() -> str:
    """Get PostgreSQL database version info"""
    async with db_pool.connection() as conn:
        try:
            version = await conn.fetchval("SELECT version()")
            return f"PostgreSQL version: {version}"
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False)


async def list_all_tables() -> str:
    """Get all tables under all schemas"""
    async with db_pool.connection() as conn:
        try:
            schemas_rows = await conn.fetch("""
                SELECT schema_name FROM information_schema.schemata
                WHERE schema_name NOT IN ('information_schema', 'pg_catalog')
                ORDER BY schema_name
            """)
            schemas = [r["schema_name"] for r in schemas_rows]
            
            all_tables = []
            for schema in schemas:
                tables_rows = await conn.fetch("""
                    SELECT c.relname AS table_name, c.reltuples::int AS approx_count
                    FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
                    WHERE n.nspname::text = $1 AND c.relkind = 'r'
                    ORDER BY c.relname
                """, schema)
                
                for r in tables_rows:
                    all_tables.append({
                        "schema": schema,
                        "name": r["table_name"],
                        "approx_count": int(r["approx_count"] or 0),
                    })
            
            return json.dumps({"schemas": schemas, "tables": all_tables, "total_count": len(all_tables)}, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False)


async def explain_query(sql: str, analyze: bool = False) -> str:
    """Run EXPLAIN / EXPLAIN ANALYZE to view query execution plan
    
    If True, execute EXPLAIN ANALYZE to get actual performance stats;
    If False, only show the planned execution strategy

    Args:
        sql: The SQL query to explain
        analyze: True=run EXPLAIN ANALYZE (executes and returns stats);
                 False=only show execution plan without running
    """
    if not sql or not sql.strip():
        return json.dumps({'status': 'error', 'message': 'SQL parameter is empty'}, ensure_ascii=False)
    
    async with db_pool.connection() as conn:
        try:
            opts = ['ANALYZE'] if analyze else []
            opts.append('FORMAT JSON')
            explain_sql = 'EXPLAIN (' + ', '.join(opts) + ') ' + sql
            
            rows = await conn.fetch(explain_sql)
            
            plan_data = []
            for row in rows:
                plan_line = row.get('QUERY PLAN') or str(row.values())
                try:
                    plan_data.append(json.loads(plan_line))
                except json.JSONDecodeError:
                    plan_data.append({'raw_plan': str(row)})
            
            if analyze:
                def extract_stats(plans):
                    stats = []
                    if isinstance(plans, list):
                        for p in plans:
                            stats.extend(extract_stats(p))
                    elif isinstance(plans, dict):
                        if 'Actual Total Time' in plans:
                            stats.append({'actual_time_ms': float(plans['Actual Total Time'])})
                        if 'Actual Rows' in plans:
                            stats.append({'actual_rows': int(plans['Actual Rows'])})
                        if 'Plans' in plans:
                            stats.extend(extract_stats(plans['Plans']))
                    return stats
                
                perf_stats = extract_stats(plan_data)
                total_time = 0
                for s in perf_stats:
                    if 'actual_time_ms' in s:
                        total_time = s['actual_time_ms']
                
                return json.dumps({
                    'status': 'ok',
                    'explain_type': 'EXPLAIN ANALYZE',
                    'description': f'Query took {total_time:.2f}ms',
                    'performance_stats': perf_stats,
                    'plan': plan_data,
                    'notes': ['Execution time > 1s'] if total_time > 1000 else [],
                }, ensure_ascii=False, default=str)
            else:
                return json.dumps({
                    'status': 'ok',
                    'explain_type': 'EXPLAIN',
                    'description': 'Plan-only: estimated query plan',
                    'plan': plan_data,
                }, ensure_ascii=False, default=str)
        
        except Exception as e:
            return json.dumps({'status': 'error', 'message': str(e)}, ensure_ascii=False)


async def get_query_statistics() -> str:
    """View current PostgreSQL database activity, including running queries, connections, table stats, cache hit ratio, blocked queries, etc.

    This includes but is not limited to:
    - Long-running queries (> 5 seconds)
    - Connection count statistics
    - Table size statistics
    - Cache hit ratio
    - Number of blocked queries
    """
    async with db_pool.connection() as conn:
        try:
            result = {}
            
            rows = await conn.fetch("""
                SELECT pid, now() - pg_stat_activity.query_start AS duration,
                       query, state, usename
                FROM pg_stat_activity
                WHERE (now() - pg_stat_activity.query_start > interval '5 seconds')
                  AND state = 'active' AND datname = current_database()
                ORDER BY duration DESC
            """)
            
            result['long_running_queries'] = []
            for r in rows:
                result['long_running_queries'].append({
                    'pid': int(r['pid']),
                    'user': str(r['usename']),
                    'duration': str(r['duration']),
                    'state': r['state'],
                    'query': (r['query'] or '')[:500],
                })
            
            row = await conn.fetchval("""
                SELECT json_build_object(
                    'total', count(*),
                    'active', sum(CASE WHEN state = 'active' THEN 1 ELSE 0 END),
                    'idle', sum(CASE WHEN state = 'idle' THEN 1 ELSE 0 END)
                ) FROM pg_stat_activity WHERE datname = current_database()
            """)
            try:
                result['connections'] = json.loads(row) if row else {}
            except:
                result['connections'] = row
            
            rows = await conn.fetch("""
                SELECT c.relname AS table_name, n.nspname AS schema,
                    c.reltuples::bigint AS approx_count,
                    pg_size_pretty(pg_total_relation_size(c.oid)) AS total_size
                FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE n.nspname NOT IN ('information_schema', 'pg_catalog')
                  AND c.relkind = 'r'
                ORDER BY pg_total_relation_size(c.oid) DESC LIMIT 20
            """)
            
            result['table_stats'] = []
            for r in rows:
                result['table_stats'].append({
                    'table': str(r['table_name']),
                    'schema': str(r['schema']),
                    'approx_count': int(r['approx_count']) if r['approx_count'] else 0,
                    'total_size': str(r['total_size']),
                })
            
            row = await conn.fetchval("""
                SELECT round(100.0 * sum(heap_blks_hit) /
                       nullif(sum(heap_blks_hit) + sum(heap_blks_read), 0), 2)
                FROM pg_statio_user_tables
            """)
            result['cache_hit_ratio'] = f'{row or 0}%'
            
            rows = await conn.fetch("""
                SELECT count(*) AS blocked FROM pg_locks l
                JOIN pg_stat_activity a ON l.pid = a.pid
                WHERE NOT l.granted AND a.datname = current_database()
            """)
            if rows:
                result['blocked_queries'] = int(rows[0]['blocked'] or 0)
            
            return json.dumps(result, ensure_ascii=False, default=str)
        
        except Exception as e:
            return json.dumps({'status': 'error', 'message': str(e)}, ensure_ascii=False)


async def list_roles() -> str:
    """List all roles (users) and their membership"""
    async with db_pool.connection() as conn:
        try:
            rows = await conn.fetch("""
                SELECT r.rolname AS role_name,
                       r.rolsuper AS is_superuser,
                       r.rolcreaterole AS can_create_role,
                       r.rolcreatedb AS can_create_db,
                       r.rolcanlogin AS can_login,
                       m.member::regrole AS member_of
                FROM pg_roles r
                LEFT JOIN pg_auth_members m ON m.member = r.oid
                WHERE r.rolname NOT LIKE 'pg_%'
                ORDER BY r.rolname
            """)
            
            roles = {}
            for r in rows:
                name = r['role_name']
                if name not in roles:
                    roles[name] = {
                        'role_name': name,
                        'is_superuser': bool(r['is_superuser']),
                        'can_create_role': bool(r['can_create_role']),
                        'can_create_db': bool(r['can_create_db']),
                        'can_login': bool(r['can_login']),
                        'member_of': [],
                    }
                if r['member_of']:
                    roles[name]['member_of'].append(str(r['member_of']))
            
            result = list(roles.values())
            return json.dumps(
                {"roles": result, "count": len(result)},
                ensure_ascii=False, default=str
            )
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False)


async def list_grants(schema: str = "public") -> str:
    """List table/column level GRANT authorization info"""
    async with db_pool.connection() as conn:
        try:
            rows = await conn.fetch("""
                SELECT n.nspname AS schema_name,
                       c.relname AS table_name,
                       c.relkind AS object_type,
                       pg_get_userbyid(c.relowner) AS owner,
                       c.relacl AS privileges
                FROM pg_class c
                JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE c.relkind IN ('r', 'v', 'm')
                  AND n.nspname = $1
                ORDER BY n.nspname, c.relname
            """, schema)
            
            grants = []
            for r in rows:
                acl = r['privileges']
                if not acl:
                    continue
                acl_str = str(acl)
                table_grants = []
                if acl_str and acl_str != '{}' and acl_str != 'NULL':
                    acl_items = acl_str.strip('{}').strip("'").split(',')
                    for item in acl_items:
                        if not item or item == 'NULL':
                            continue
                        parts = item.split('=')
                        if len(parts) < 2:
                            continue
                        user_part = parts[0]
                        priv_part = parts[1]
                        if ':' in user_part:
                            grantor, grantee = user_part.split(':', 1)
                        else:
                            grantor, grantee = 'unknown', user_part
                        
                        priv_map = {
                            'r': 'SELECT', 'w': 'INSERT', 'a': 'REFERENCES',
                            'd': 'DELETE', 'D': 'DELETE', 't': 'TRIGGER',
                            'T': 'TRIGGER', 'x': 'REFERENCES', 'X': 'REFERENCES',
                            'z': 'TRUNCATE', 'R': 'RULE', 'U': 'UPDATE',
                        }
                        granted_privs = []
                        with_opt = ''
                        if priv_part.endswith('/') and len(priv_part) > 2:
                            priv_part, with_opt = priv_part[:-1], priv_part[-1:]
                            if with_opt == 'x':
                                with_opt = ' WITH GRANT OPTION'
                        for ch in priv_part:
                            if ch in priv_map:
                                granted_privs.append(priv_map[ch])
                        if not granted_privs and priv_part:
                            granted_privs = [priv_part]
                        
                        table_grants.append({
                            'grantee': grantee.strip("'"),
                            'privileges': granted_privs,
                            'with_grant_option': bool(with_opt),
                        })
                
                grants.append({
                    'schema': r['schema_name'],
                    'table': r['table_name'],
                    'type': r['object_type'],
                    'owner': r['owner'],
                    'grants': table_grants,
                })
            
            return json.dumps(
                {"schema": schema, "grants": grants, "count": len(grants)},
                ensure_ascii=False, default=str
            )
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False)
