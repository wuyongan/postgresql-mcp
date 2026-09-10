# PostgreSQL MCP Server

A PostgreSQL Model Context Protocol (MCP) server that provides tools for interacting with PostgreSQL databases via HTTP/JSON-RPC.

## Features

- **SQL Query Execution** — SELECT, INSERT, UPDATE, DELETE with result formatting
- **Schema & Table Management** — introspect schemas, tables, columns, constraints
- **Index Analysis** — list indexes, support for partitioned tables
- **Query Plan Analysis** — EXPLAIN and EXPLAIN ANALYZE with performance stats
- **User/Role Management** — list roles, memberships, privileges
- **Permission Analysis** — table/column-level GRANT/privilege inspection
- **Database Monitoring** — long-running queries, cache hit ratio, connection stats

## Project Structure

```
postgresql_mcp/
├── __init__.py          # Package initialization
├── config.py            # Configuration management (env vars, CLI args)
├── database.py          # Async database connection pool (asyncpg)
├── server.py            # MCP server setup and HTTP routing
├── tools.py             # 12 MCP tool implementations
├── utils.py             # Utility functions
├── tests/               # Test suite
│   ├── __init__.py
│   ├── test_config.py
│   ├── test_database.py
│   └── test_tools.py
http_mcp_server.py       # CLI entry point (asyncio + uvicorn)
http_mcp_config.json     # MCP client config (SSE/Streamable HTTP)
pyproject.toml           # Project metadata, dependencies, install config
requirements.txt         # Dependencies
```

## Installation

### Prerequisites

- Python 3.10+
- PostgreSQL 12+ database access

### Install Dependencies

```bash
pip install -r requirements.txt
```

This installs:
- `mcp>=1.0.0` — MCP protocol framework
- `asyncpg>=0.29.0` — Async PostgreSQL driver
- `uvicorn>=0.29.0` — ASGI server
- `python-dotenv>=1.0.0` — .env file loading
- `starlette>=0.35.0` — ASGI framework (transitive dependency)

### Or Install as a Package

```bash
pip install .
```

### Editable Install (Development)

For active development, install in editable mode so changes to source files take effect immediately:

```bash
pip install -e ".[test]"
```

## Configuration

### Environment Variables

Create a `.env` file or set these environment variables:

```bash
# PostgreSQL Connection
PG_HOST=127.0.0.1
PG_PORT=5432
PG_DATABASE=postgres
PG_USER=postgres
PG_PASSWORD=your_password

# Server Configuration
SERVER_PORT=8000
SERVER_HOST=0.0.0.0
LOG_LEVEL=INFO
```

> **Never commit `.env`** — it is excluded by `.gitignore`.

### Command Line Arguments

Command-line flags override `.env` values:

```bash
python http_mcp_server.py --host 0.0.0.0 --port 8000 \
    --db-host 192.168.1.100 --db-port 5432 --db-name mydb \
    --db-user myuser --db-password secret
```

### MCP Client Config

`http_mcp_config.json` provides a ready-to-use MCP client configuration (e.g., for Windsurf/Cursor or other MCP-compatible editors). Edit the URL/port to match your server's configuration:

```bash
python http_mcp_server.py
# Then connect your MCP client to http://localhost:8000/mcp
```

## Quick Start

### 1. Start the server

```bash
python http_mcp_server.py
```

The server starts on `http://0.0.0.0:8000`.

### 2. Health Check

```bash
curl http://127.0.0.1:8000/
```

### 3. MCP Protocol Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST   | /mcp | Streamable HTTP MCP endpoint (JSON-RPC 2.0) |

### 4. MCP Tools (12 available)

All tools accept a JSON-RPC 2.0 request body. Example:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "execute_query",
    "arguments": {
      "sql": "SELECT * FROM users LIMIT 10",
      "limit": 10
    }
  }
}
```

---

## Tool Reference

### `execute_query`

Execute SQL queries against the database.

| Parameter | Required | Type   | Default | Description              |
|-----------|----------|--------|---------|--------------------------|
| `sql`     | yes      | string | —       | SQL query string         |
| `limit`   | no       | int    | 100     | Maximum rows to return   |

**Response:** `{"status": "ok", "columns": [...], "rows": [...], "count": N}`

**Example:**
```json
{
  "sql": "SELECT * FROM users LIMIT 10",
  "limit": 10
}
```

---

### `list_schemas`

Get list of database schemas (excludes `information_schema` and `pg_catalog`).

| Parameter | Required | Type | Default | Description |
|-----------|----------|------|---------|-------------|
| *(none)*  | —        | —    | —       | —           |

**Response:** `{"schemas": ["public", "public_1", ...], "count": N}`

---

### `list_tables`

Get list of tables in a specific schema.

| Parameter | Required | Type   | Default  | Description     |
|-----------|----------|--------|----------|-----------------|
| `schema`  | no       | string | `"public"` | Schema name   |

**Response:** `{"tables": [{"name": "t", "approx_count": 1000}], "schema": "public", "count": N}`

---

### `describe_table`

Get detailed table structure including columns, types, defaults, and primary keys.

| Parameter   | Required | Type   | Description  |
|-------------|----------|--------|--------------|
| `schema`    | yes      | string | Schema name  |
| `table_name`| yes      | string | Table name   |

**Response:** `{"table": "...", "schema": "...", "columns": [{"name": "...", "type": "...", "nullable": bool, "default": "...", "is_primary_key": bool}], "primary_keys": [...]}`

---

### `get_table_count`

Get approximate row count for a table.

| Parameter   | Required | Type   | Description  |
|-------------|----------|--------|--------------|
| `schema`    | yes      | string | Schema name  |
| `table_name`| yes      | string | Table name   |

**Response:** `{"table": "...", "schema": "...", "count": N}`

---

### `get_table_indexes`

Get index information for a table (supports both regular and partitioned tables).

| Parameter   | Required | Type   | Description  |
|-------------|----------|--------|--------------|
| `schema`    | yes      | string | Schema name  |
| `table_name`| yes      | string | Table name   |

**Response:** `{"indexes": [{"name": "...", "unique": bool, "columns": [...]}]}`

---

### `get_version`

Get PostgreSQL database version info.

| Parameter | Required | Type | Default | Description |
|-----------|----------|------|---------|-------------|
| *(none)*  | —        | —    | —       | —           |

**Response:** Plain text, e.g. `"PostgreSQL version: PostgreSQL 18.1 ..."`.

---

### `list_all_tables`

Get all tables under all schemas.

| Parameter | Required | Type | Default | Description |
|-----------|----------|------|---------|-------------|
| *(none)*  | —        | —    | —       | —           |

**Response:** `{"schemas": [...], "tables": [{"schema": "...", "name": "...", "approx_count": N}], "total_count": N}`

---

### `explain_query`

Run EXPLAIN / EXPLAIN ANALYZE to view query execution plan.

| Parameter  | Required | Type  | Default | Description                                      |
|------------|----------|-------|---------|--------------------------------------------------|
| `sql`      | yes      | string| —       | SQL query to explain                             |
| `analyze`  | no       | bool  | false   | True = EXPLAIN ANALYZE (runs query, returns stats); False = plan-only |

**Response (plan-only):**
```json
{
  "explain_type": "EXPLAIN",
  "description": "Plan-only: estimated query plan",
  "plan": [...]
}
```

**Response (with analyze):**
```json
{
  "explain_type": "EXPLAIN ANALYZE",
  "description": "Query took 45.23ms",
  "performance_stats": [{"actual_time_ms": 45.23, "actual_rows": 10}],
  "plan": [...],
  "notes": []
}
```

`notes` includes `"Execution time > 1s"` warning when `Actual Total Time > 1000ms`.

---

### `get_query_statistics`

View current PostgreSQL database activity: long-running queries, connections, table stats, cache hit ratio, blocked queries.

| Parameter | Required | Type | Default | Description |
|-----------|----------|------|---------|-------------|
| *(none)*  | —        | —    | —       | —           |

**Response:**
```json
{
  "long_running_queries": [{"pid": 123, "user": "...", "duration": "00:00:05", "state": "active", "query": "..."}],
  "connections": {"total": 5, "active": 2, "idle": 3},
  "table_stats": [{"table": "...", "schema": "...", "approx_count": N, "total_size": "100MB"}],
  "cache_hit_ratio": "99.8%",
  "blocked_queries": 0
}
```

---

### `list_roles`

List all roles (users) and their membership.

| Parameter | Required | Type | Default | Description |
|-----------|----------|------|---------|-------------|
| *(none)*  | —        | —    | —       | —           |

**Response:**
```json
{
  "roles": [
    {
      "role_name": "postgres",
      "is_superuser": true,
      "can_create_role": true,
      "can_create_db": true,
      "can_login": true,
      "member_of": ["admin"]
    }
  ]
}
```

---

### `list_grants`

List table/column level GRANT authorization info.

| Parameter | Required | Type   | Default  | Description    |
|-----------|----------|--------|----------|----------------|
| `schema`  | no       | string | `"public"` | Target schema |

**Response:**
```json
{
  "grants": [
    {
      "schema": "public",
      "table": "users",
      "type": "r",
      "owner": "postgres",
      "grants": [
        {"grantee": "app_user", "privileges": ["SELECT", "INSERT"], "with_grant_option": false}
      ]
    }
  ]
}
```

---

## Testing

Run the test suite:

```bash
# Install test dependencies
pip install pytest pytest-asyncio

# Run all tests
pytest

# Verbose output
pytest -v

# Specific test file
pytest postgresql_mcp/tests/test_config.py

# Coverage report
pytest --cov=postgresql_mcp --cov-report=html
```

## Using with Hermes Agent

### Configuring Hermes Agent

Add the MCP server to your Hermes Agent configuration:

```json
{
  "mcpServers": {
    "postgres-new": {
      "url": "http://127.0.0.1:8000/mcp"
    }
  }
}
```

Hermes Agent will automatically read this configuration and discover all 12 tools provided by `postgres-new` via the MCP protocol.

### Using in Conversations

After configuration, simply describe your needs in the Hermes conversation (e.g., "show table structure", "explain slow query"), and Hermes will automatically:

1. Select the appropriate tool (such as `describe_table`, `explain_query`)
2. Construct and call the MCP server with the required parameters
3. Format and return the results to you

No need to manually construct JSON-RPC requests.

### Verifying the Connection

After starting the server, you can quickly verify it with `curl`:

```bash
# Check if the server is running
curl http://127.0.0.1:8000/

# Test MCP connection
curl -X POST http://127.0.0.1:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
      "protocolVersion": "2024-11-05",
      "capabilities": {},
      "clientInfo": { "name": "test", "version": "1.0.0" }
    }
  }'
```

## Security Notes

- Use environment variables for sensitive configuration
- Never commit database credentials (`.env` is gitignored)
- Use connection pooling (enabled by default)
- Set appropriate database user permissions (least privilege)
- Consider using SSL/TLS for database connections in production
- `execute_query` has a 100,000-character SQL length limit to prevent abuse

## License

MIT License

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Make your changes and add tests
4. Run tests: `pytest`
5. Commit with a descriptive message
6. Push and open a Pull Request
