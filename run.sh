#!/usr/bin/env bash
# PostgreSQL MCP Server - Linux/macOS Launcher (thin wrapper)
# Use run.py for cross-platform compatibility instead.
# This file is kept for backward compatibility.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="$(command -v python3 || command -v python)"

if [ -f "$SCRIPT_DIR/venv/bin/python" ]; then
    PYTHON_BIN="$SCRIPT_DIR/venv/bin/python"
fi

exec "$PYTHON_BIN" "$SCRIPT_DIR/run.py" "$@"
