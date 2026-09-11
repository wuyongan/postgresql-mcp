# PostgreSQL MCP Server

A PostgreSQL Model Context Protocol (MCP) server that provides tools for interacting with PostgreSQL databases via HTTP/JSON-RPC.

## Architecture

This project follows a **layered modular design**:

```
postgresql_mcp/
├── config.py            # Configuration (env vars, CLI args)
├── db/
│   └── pool.py          # Connection pool management
├── queries/
│   ├── schema.py        # Schema SQL definitions
│   ├── table.py         # Table SQL definitions
│   └── version.py       # Version SQL
├── common/
│   ├── response.py      # Unified JSON response helpers
│   └── formatting.py    # Data formatting helpers
├── tools/
│   ├── query.py         # execute_query
│   ├── schema.py        # list_schemas, list_all_tables
│   ├── table.py         # list_tables, describe_table, etc.
│   └── version.py       # get_version
├── server.py            # MCP server setup
└── tests/
```

| Layer | Module | Responsibility |
|-------|--------|----------------|
| Config | `config.py` | Environment variable loading, dataclass configs |
| DB | `db/pool.py` | asyncpg connection pool, context manager |
| SQL | `queries/*` | Raw SQL statements (string constants) |
| Common | `common/*` | Response formatting, error handling, row processing |
| Tools | `tools/*` | MCP tool implementations (business logic) |
| Server | `server.py` | FastMCP instantiation, tool registration |

## Features

- **SQL Query Execution** - SELECT, INSERT, UPDATE, DELETE with result formatting
- **Schema Management** - introspect schemas, list all tables
- **Table Management** - list tables, describe structure, row counts, indexes
- **Version Query** - get PostgreSQL version info

## Quick Start

### 1. Install

```bash
pip install -r requirements.txt
```

### 2. Configure

Create a `.env` file:

```bash
PG_HOST=127.0.0.1
PG_PORT=5432
PG_DATABASE=postgres
PG_USER=postgres
PG_PASSWORD=your_password
SERVER_PORT=8000
```

### 3. Start Server

#### Recommended: Cross-platform launcher (one command)
```bash
# Windows: run.bat or run.py
# macOS/Linux: run.sh or run.py
python run.py
```

#### Advanced: Direct entry point with CLI options
```bash
python http_mcp_server.py --port 9000 --db-host 192.168.1.100
```

The server starts on `http://0.0.0.0:8000`.

### 4. Verify

```bash
curl http://127.0.0.1:8000/
```

## MCP Tools

The server exposes 9 tools via the MCP protocol:

| Tool | Description |
|------|-------------|
| `execute_query` | Execute SQL (SELECT/INSERT/UPDATE/DELETE) |
| `explain_query` | Analyze SQL execution plan (EXPLAIN) with performance metrics |
| `list_schemas` | List database schemas |
| `list_all_tables` | List all tables across all schemas |
| `list_tables` | List tables in a specific schema |
| `describe_table` | Get table structure (columns, types, PKs) |
| `get_table_count` | Get approximate row count |
| `get_table_indexes` | Get index information |
| `get_version` | Get PostgreSQL version |

## Dynamic Tool Loading (Hot-Plug)

The server supports automatic discovery of tool modules from the `tools/` directory.
When you add a new `.py` file to `tools/`, it is automatically registered at runtime
without restarting the server.

### Creating a Dynamic Tool

1. Create a `.py` file in the `tools/` directory (e.g., `tools/_example_tool.py`)
2. Define async functions and add them to a `__tools__` list:

```python
async def my_tool(param: str) -> str:
    """Description of my tool.

    Args:
        param: Description of parameter.

    Returns:
        JSON string with results.
    """
    ...your code...

__tools__ = [
    (my_tool, "my_tool", "Description of my tool"),
]
```

3. Save the file — the server auto-discovers and registers it

### Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `HOTPLUG_ENABLED` | `true` | Enable/disable dynamic tool loading |

To disable: set `HOTPLUG_ENABLED=false` in `.env`.

### Example

The `tools/_example_tool.py` file demonstrates how to create a dynamic tool.
It queries the `orders` table and returns weekly sales data.

### Example Request

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

## Using with MCP Clients

Add this server to your MCP client configuration:

```json
{
  "mcpServers": {
    "postgres": {
      "url": "http://127.0.0.1:8000/mcp"
    }
  }
}
```

A sample config file is available in `docs/mcp_config.json`.

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PG_HOST` | `127.0.0.1` | PostgreSQL host |
| `PG_PORT` | `5432` | PostgreSQL port |
| `PG_DATABASE` | `postgres` | Database name |
| `PG_USER` | `postgres` | Database user |
| `PG_PASSWORD` | (empty) | Database password |
| `SERVER_PORT` | `8000` | Server port |
| `SERVER_HOST` | `0.0.0.0` | Server host |
| `LOG_LEVEL` | `INFO` | Log level |

### Command Line Arguments

Command-line flags override `.env` values:

```bash
python http_mcp_server.py --port 8000 --db-host 192.168.1.100 --db-name mydb
```

## Project Structure

```
postgresql-mcp/
├── postgresql_mcp/
│   ├── __init__.py
│   ├── config.py            # Configuration management
│   ├── db/
│   │   ├── __init__.py
│   │   └── pool.py          # Connection pool (asyncpg)
│   ├── queries/
│   │   ├── __init__.py
│   │   ├── schema.py        # Schema SQL queries
│   │   ├── table.py         # Table SQL queries
│   │   └── version.py       # Version SQL query
│   ├── common/
│   │   ├── __init__.py
│   │   ├── response.py      # Response helpers
│   │   └── formatting.py    # Data formatting helpers
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── query.py
│   │   ├── schema.py
│   │   ├── table.py
│   │   └── version.py
│   ├── server.py            # MCP server setup
│   └── tests/
├── run.py                   # Cross-platform launcher (Windows/macOS/Linux)
├── run.bat                  # Windows wrapper (delegates to run.py)
├── run.sh                   # macOS/Linux wrapper (delegates to run.py)
├── http_mcp_server.py       # Direct entry point
├── docs/
│   ├── README.md
│   └── mcp_config.json      # Sample MCP client config
├── pyproject.toml           # Project metadata
├── requirements.txt         # Dependencies
├── .env.example             # Environment template
└── README.md
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
