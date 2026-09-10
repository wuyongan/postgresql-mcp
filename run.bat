@echo off
REM PostgreSQL MCP Server - Windows Launcher
REM One-click startup script for Windows

setlocal enabledelayedexpansion

echo ========================================
echo   PostgreSQL MCP Server
echo ========================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH.
    echo Please install Python 3.10+ from https://www.python.org/
    pause
    exit /b 1
)

echo [OK] Python found:
python --version
echo.

REM Check if virtual environment exists
if not exist "venv\" (
    echo [INFO] Virtual environment not found, creating...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo [OK] Virtual environment created.
    echo.
) else (
    echo [INFO] Virtual environment found.
)

REM Activate virtual environment
echo [INFO] Activating virtual environment...
call venv\Scripts\activate.bat
if %errorlevel% neq 0 (
    echo [ERROR] Failed to activate virtual environment.
    pause
    exit /b 1
)

REM Install/update dependencies
echo [INFO] Installing dependencies...
python -m pip install --upgrade pip -q
python -m pip install -r requirements.txt -q
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install dependencies.
    echo Try running: pip install -r requirements.txt
    pause
    exit /b 1
)

echo.
echo [OK] Dependencies installed.
echo.

REM Check for .env file
if not exist ".env" (
    echo [WARNING] .env file not found.
    echo Creating a default .env file...
    (
        echo # PostgreSQL Connection
        echo PG_HOST=127.0.0.1
        echo PG_PORT=5432
        echo PG_DATABASE=postgres
        echo PG_USER=postgres
        echo PG_PASSWORD=
        echo.
        echo # Server Configuration
        echo SERVER_PORT=8000
        echo SERVER_HOST=0.0.0.0
        echo LOG_LEVEL=INFO
    ) > .env
    echo [OK] Default .env file created.
    echo Please edit .env and set your database credentials.
    echo.
) else (
    echo [OK] .env file found.
)

echo.
echo ========================================
echo   Starting PostgreSQL MCP Server...
echo ========================================
echo.
echo Server URL: http://127.0.0.1:8000/mcp
echo Health check: http://127.0.0.1:8000/
echo.
echo Press Ctrl+C to stop the server.
echo.

REM Start the server
python http_mcp_server.py %*
