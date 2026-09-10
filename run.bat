@echo off
REM PostgreSQL MCP Server - Windows Launcher (thin wrapper)
REM Use run.py for cross-platform compatibility instead.
REM This file is kept for backward compatibility.

setlocal enabledelayedexpansion
set "PYTHON_PATH=%~dp0venv\Scripts\python.exe"

if exist "%PYTHON_PATH%" (
    "%PYTHON_PATH%" "%~dp0run.py" %*
) else (
    python "%~dp0run.py" %*
)
