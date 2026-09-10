"""Example of a dynamic tool (initially disabled).

This file is prefixed with _ to prevent automatic discovery by the loader.
Once you rename it (removing the _ prefix), the server will automatically
discover and register it as a dynamic tool within 2 seconds.

Usage:
  1. Rename this file to: example_tool.py
  2. Wait ~2 seconds
  3. Call the tool via MCP: tools/call example_tool

You can also disable by setting HOTPLUG_ENABLED=false in .env
"""

import logging

logger = logging.getLogger(__name__)


async def example_tool(param: str = "") -> str:
    """Example dynamic tool for testing hot-plug functionality.

    This tool is currently disabled (filename starts with _).
    Rename the file to remove the _ prefix to enable it.

    Args:
        param: Optional test parameter (unused).

    Returns:
        JSON string with example data and usage instructions.
    """
    from ..common.response import ok_result

    return ok_result(
        {
            "status": "ok",
            "message": "Dynamic tool example: rename file to enable",
            "example": {
                "step1": "Rename this file from _example_tool.py to example_tool.py",
                "step2": "Wait ~2 seconds for auto-discovery",
                "step3": "Call via MCP: tools/call example_tool",
            },
            "data": [
                {"id": 1, "name": "Test Record 1", "value": 100},
                {"id": 2, "name": "Test Record 2", "value": 200},
                {"id": 3, "name": "Test Record 3", "value": 300},
            ],
            "count": 3,
        }
    )


# Define the tools exported from this module.
# Format: (function_reference, tool_name, description)
__tools__ = [
    (example_tool, "example_tool", "Example: demonstrates how to write a dynamic tool (temporarily disabled)"),
]
