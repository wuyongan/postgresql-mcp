# PostgreSQL MCP Server v1.0.2 (2025-06-19)

---

## Bug Fixes - explain_query Tool

Complete rewrite of the explain_query tool to fix critical parsing and usability issues:

| Bug | Description | Status |
|-----|-------------|--------|
| Bug 1 (Critical) | SQL with WHERE clause and string literals failed - e.g., WHERE tablename = test -> syntax error | Fixed |
| Bug 2 | message field showed No plan data found even on successful queries | Fixed |
| Bug 3 | Raw JSON with escape characters instead of readable Markdown | Fixed |
| Bug 4 | No extracted performance metrics (Total Time, index usage, parallel, etc.) | Fixed |
| Bug 5 | No warning for unbounded queries on large tables | Fixed |

### Changes

- explain_query - Complete rewrite of EXPLAIN plan parsing:
  - Properly parses EXPLAIN (FORMAT JSON) response: row["QUERY PLAN"] is a JSON string, not a dict - uses json.loads() to deserialize
  - Auto-quotes non-ASCII identifiers (Chinese, hyphens, special chars) while preserving simple ASCII names and string literals
  - Returns structured Markdown report with Operation, Time, Cost, Index, Parallel, Warnings sections
  - Returns extracted metrics dict: operation, total_time_ms, startup_time_ms, rows_estimated, rows_actual, cost_startup, cost_total, index_used, parallel, warnings, tables
  - Adds LIMIT warning when no LIMIT clause and estimated rows > 10,000
  - Improved error messages with available keys for debugging

- _quote_identifiers - New identifier quoting helper:
  - Character-by-character parser with 4 modes: preserve string literals, preserve quoted identifiers, build identifier tokens, pass-through
  - Correctly handles string literals (single-quoted values with escape sequences)
  - Smart quoting: only wraps identifiers that need it (non-ASCII, special characters like hyphens)
  - Preserves schema.table dot notation between simple ASCII identifiers

### New Tool

| Tool | Description |
|------|-------------|
| explain_query | Analyze SQL execution plan via EXPLAIN (ANALYZE, VERBOSE, FORMAT JSON) with auto-quoted identifiers, Markdown report, and extracted performance metrics |

### Testing

- Identifier quoting: 6/6 test cases pass (simple SQL, WHERE + string literals, schema.table, hyphenated names, Chinese identifiers, multi-literal queries)
- Plan extraction: correctly parses QUERY PLAN JSON string -> dict -> metrics

---

# PostgreSQL MCP Server v1.0.0

First stable release of the PostgreSQL Model Context Protocol server -- a modular toolkit for database administration via HTTP.

## What Included

**8 MCP Tools** exposed via HTTP/JSON-RPC:

| Tool | Description |
|------|-------------|
| execute_query | Execute SQL (SELECT / INSERT / UPDATE / DELETE) |
| list_schemas | List database schemas |
| list_all_tables | List all tables across all schemas |
| list_tables | List tables in a specific schema |
| describe_table | Get table structure (columns, types, default values, PKs) |
| get_table_count | Get approximate row count |
| get_table_indexes | Get index information for a table |
| get_version | Get PostgreSQL version info |

## Architecture

Layered modular design with clear separation of concerns:

```
postgresql_mcp/
├── config.py            # Environment config, dataclass settings
├── db/pool.py           # asyncpg connection pool management
├── queries/             # SQL statement definitions (schema, table, version)
├── common/              # Response formatting, error handling, data formatting
├── tools/               # MCP tool implementations
│   ├── query.py         # execute_query, explain_query
│   ├── schema.py        # list_schemas, list_all_tables
│   ├── table.py         # list_tables, describe_table, get_table_count, get_table_indexes
│   └── version.py       # get_version
├── server.py            # FastMCP server setup & tool registration
└── tests/               # Placeholder test (CI compliance)
```

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
# or
pip install mcp asyncpg uvicorn python-dotenv starlette
```

### 2. Configure

Create a .env file:

```env
PG_HOST=127.0.0.1
PG_PORT=5432
PG_DATABASE=postgres
PG_USER=postgres
PG_PASSWORD=your_password
SERVER_PORT=8000
```

### 3. Start server

**Cross-platform launcher (recommended):**

```bash
python run.py              # Windows / macOS / Linux
```

**Direct entry point (with CLI overrides):**

```bash
python http_mcp_server.py --port 9000 --db-host 192.168.1.100
```

### 4. Connect from MCP client

```json
{
  "mcpServers": {
    "postgres": {
      "url": "http://127.0.0.1:8000/mcp"
    }
  }
}
```

## Configuration

### Environment Variables

| Variable    | Default     | Description          |
|-------------|-------------|----------------------|
| PG_HOST   | 127.0.0.1 | PostgreSQL host       |
| PG_PORT   | 5432      | PostgreSQL port       |
| PG_DATABASE | postgres | Database name        |
| PG_USER   | postgres  | Database user        |
| PG_PASSWORD | (empty)   | Database password     |
| SERVER_PORT | 8000    | Server listen port    |
| SERVER_HOST | 0.0.0.0 | Server bind host      |
| LOG_LEVEL | INFO      | Logging level         |

### Command-line Arguments

CLI flags override .env values:

```bash
python http_mcp_server.py --port 8000 --db-host 192.168.1.100 --db-name mydb
```

## Example Request

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "explain_query",
    "arguments": {
      "sql": "SELECT * FROM users WHERE status = active LIMIT 10"
    }
  }
}
```

## Release Notes

- Initial release
- Layered modular architecture (config -> db -> queries -> common -> tools -> server)
- Cross-platform launcher (run.py, run.bat, run.sh)
- Environment-based configuration with .env support
- Connection pooling via asyncpg
- MCP protocol via fastmcp / HTTP transport
- 9 tools for database introspection and SQL execution
- MIT License

## Links

- **Source:** [github.com/wuyongan/postgresql-mcp](https://github.com/wuyongan/postgresql-mcp)
- **Issues:** [github.com/wuyongan/postgresql-mcp/issues](https://github.com/wuyongan/postgresql-mcp/issues)
- **MCP Config:** docs/mcp_config.json (sample client config)

## Security Notes

- Use environment variables for sensitive configuration -- never commit credentials
- .env is gitignored by default
- execute_query enforces a 100,000-character SQL length limit
- Use least-privilege database user accounts
- Consider SSL/TLS for database connections in production
