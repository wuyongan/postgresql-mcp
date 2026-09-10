#!/usr/bin/env bash
# PostgreSQL MCP Server - Linux/macOS Launcher
# One-click startup script for Unix-like systems

set -euo pipefail

echo "========================================"
echo "  PostgreSQL MCP Server"
echo "========================================"
echo ""

# Check if Python is available
if ! command -v python3 &> /dev/null && ! command -v python &> /dev/null; then
    echo "[ERROR] Python is not installed or not in PATH."
    echo "Please install Python 3.10+ from https://www.python.org/"
    exit 1
fi

PYTHON_BIN=$(command -v python3 || command -v python)
echo "[OK] Python found:"
"$PYTHON_BIN" --version
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "[INFO] Virtual environment not found, creating..."
    "$PYTHON_BIN" -m venv venv
    echo "[OK] Virtual environment created."
    echo ""
else
    echo "[INFO] Virtual environment found."
fi

# Activate virtual environment
echo "[INFO] Activating virtual environment..."
source venv/bin/activate

# Install/update dependencies
echo "[INFO] Installing dependencies..."
python -m pip install --upgrade pip -q
python -m pip install -r requirements.txt -q

if [ $? -ne 0 ]; then
    echo "[ERROR] Failed to install dependencies."
    echo "Try running: pip install -r requirements.txt"
    exit 1
fi

echo ""
echo "[OK] Dependencies installed."
echo ""

# Check for .env file
if [ ! -f ".env" ]; then
    echo "[WARNING] .env file not found."
    echo "Creating a default .env file..."
    cat > .env << 'EOF'
# PostgreSQL Connection
PG_HOST=127.0.0.1
PG_PORT=5432
PG_DATABASE=postgres
PG_USER=postgres
PG_PASSWORD=

# Server Configuration
SERVER_PORT=8000
SERVER_HOST=0.0.0.0
LOG_LEVEL=INFO
EOF
    echo "[OK] Default .env file created."
    echo "Please edit .env and set your database credentials."
    echo ""
else
    echo "[OK] .env file found."
fi

echo ""
echo "========================================"
echo "  Starting PostgreSQL MCP Server..."
echo "========================================"
echo ""
echo "Server URL: http://127.0.0.1:8000/mcp"
echo "Health check: http://127.0.0.1:8000/"
echo ""
echo "Press Ctrl+C to stop the server."
echo ""

# Start the server
python http_mcp_server.py "$@"
