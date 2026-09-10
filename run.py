#!/usr/bin/env python3
"""Cross-platform launcher for PostgreSQL MCP Server.

Replaces run.bat and run.sh with a single Python script
that works on Windows, macOS, and Linux.
"""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


def get_python() -> str:
    """Find the best python executable for this platform."""
    candidates = ["python3", "python"] if os.name != "nt" else ["python", "py"]
    for name in candidates:
        path = shutil.which(name)
        if path:
            return path
    print("[ERROR] Python is not installed or not in PATH.")
    print("Please install Python 3.10+ from https://www.python.org/")
    sys.exit(1)


def ensure_venv(python: str, venv_path: Path) -> str:
    """Create venv if missing, return path to python inside it."""
    if venv_path.is_dir():
        print("[INFO] Virtual environment found.")
        bin_dir = venv_path / ("Scripts" if os.name == "nt" else "bin")
        return str(bin_dir / "python")

    print("[INFO] Virtual environment not found, creating...")
    result = subprocess.run(
        [python, "-m", "venv", str(venv_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        print("[ERROR] Failed to create virtual environment.")
        if result.stderr:
            print(result.stderr)
        sys.exit(1)
    print("[OK] Virtual environment created.")

    bin_dir = venv_path / ("Scripts" if os.name == "nt" else "bin")
    return str(bin_dir / "python")


def install_deps(venv_python: str) -> int:
    """Install/update dependencies in the venv."""
    print("[INFO] Installing dependencies...")

    # Upgrade pip quietly
    rc = subprocess.run(
        [venv_python, "-m", "pip", "install", "--upgrade", "pip", "-q"],
        capture_output=True,
        text=True,
        check=False,
    )
    if rc.returncode != 0:
        print("[WARN] Failed to upgrade pip (non-fatal)")

    # Install requirements
    rc = subprocess.run(
        [venv_python, "-m", "pip", "install", "-r", "requirements.txt", "-q"],
        capture_output=True,
        text=True,
        check=False,
    )
    if rc.returncode != 0:
        print("[ERROR] Failed to install dependencies.")
        print("Try running: pip install -r requirements.txt")
        return rc.returncode

    print("[OK] Dependencies installed.")
    return 0


def ensure_env(env_path: Path):
    """Create default .env if it doesn't exist."""
    if env_path.exists():
        print("[OK] .env file found.")
        return

    print("[WARNING] .env file not found.")
    print("Creating a default .env file...")
    content = """# PostgreSQL Connection
PG_HOST=127.0.0.1
PG_PORT=5432
PG_DATABASE=postgres
PG_USER=postgres
PG_PASSWORD=

# Server Configuration
SERVER_PORT=8000
SERVER_HOST=0.0.0.0
LOG_LEVEL=INFO
"""
    env_path.write_text(content)
    print("[OK] Default .env file created.")
    print("Please edit .env and set your database credentials.")


def main():
    parser = argparse.ArgumentParser(description="PostgreSQL MCP Server - Cross-platform launcher")
    parser.add_argument("--host", type=str, default=None, help="Bind host")
    parser.add_argument("--port", type=int, default=None, help="Listen port")
    parser.add_argument("--db-host", type=str, default=None, help="PostgreSQL host")
    parser.add_argument("--db-port", type=int, default=None, help="PostgreSQL port")
    parser.add_argument("--db-name", type=str, default=None, help="PostgreSQL database")
    parser.add_argument("--db-user", type=str, default=None, help="PostgreSQL user")
    parser.add_argument("--db-password", type=str, default=None, help="PostgreSQL password")
    args, extra_args = parser.parse_known_args()

    root = Path(__file__).resolve().parent
    venv_path = root / "venv"
    env_path = root / ".env"

    print("========================================")
    print("  PostgreSQL MCP Server")
    print("========================================")
    print()

    # Find python
    python = get_python()
    print(f"[OK] Python found: {python}")
    print()

    # Ensure venv
    venv_python = ensure_venv(python, venv_path)

    # Install deps
    if install_deps(venv_python) != 0:
        sys.exit(1)

    # Ensure .env
    ensure_env(env_path)

    print()
    print("========================================")
    print("  Starting PostgreSQL MCP Server...")
    print("========================================")
    print()

    # Determine the effective server URL
    effective_host = args.host or "127.0.0.1"
    effective_port = args.port or 8000
    print(f"Server URL: http://{effective_host}:{effective_port}/mcp")
    print(f"Health check: http://{effective_host}:{effective_port}/")
    print()
    print("Press Ctrl+C to stop the server.")
    print()

    # Run the server via venv python, passing through CLI args
    server_script = root / "http_mcp_server.py"
    cmd = [venv_python, str(server_script)]

    # Pass through known args
    if args.host:
        cmd += ["--host", args.host]
    if args.port:
        cmd += ["--port", str(args.port)]
    if args.db_host:
        cmd += ["--db-host", args.db_host]
    if args.db_port:
        cmd += ["--db-port", str(args.db_port)]
    if args.db_name:
        cmd += ["--db-name", args.db_name]
    if args.db_user:
        cmd += ["--db-user", args.db_user]
    if args.db_password:
        cmd += ["--db-password", args.db_password]
    if extra_args:
        cmd += extra_args

    try:
        os.execv(venv_python, cmd)
    except Exception:
        # Fallback: execv may fail on some platforms
        import subprocess as _sub

        _sub.run(cmd, check=False)


if __name__ == "__main__":
    main()
