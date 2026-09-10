"""Unified JSON response helpers -- eliminates boilerplate in every tool"""

import json
import logging

logger = logging.getLogger(__name__)

# Maximum JSON output size before truncation
_MAX_OUTPUT = 10000


def error_result(message: str, log: bool = True) -> str:
    """Build an error response string.

    Args:
        message: Human-readable error description.
        log: Whether to log the error (default True).

    Returns:
        JSON string: {"status": "error", "message": ...}
    """
    if log:
        logger.error("Error: %s", message)
    return json.dumps(
        {"status": "error", "message": message}, ensure_ascii=False
    )


def error_result_traceback(message: str, log: bool = True) -> str:
    """Build an error response string with full traceback logging.

    Use sparingly — only for unexpected errors that warrant investigation.

    Args:
        message: Human-readable error description.
        log: Whether to log the traceback (default True).

    Returns:
        JSON string: {"status": "error", "message": ...}
    """
    if log:
        logger.exception("Error: %s", message)
    return json.dumps(
        {"status": "error", "message": message}, ensure_ascii=False
    )


def ok_result(data: dict, *, truncate: bool = True) -> str:
    """Build a successful response string.

    Args:
        data: Payload to serialize.
        truncate: Truncate oversized responses (default True).

    Returns:
        JSON string: {"status": "ok", ...}
    """
    try:
        text = json.dumps(data, ensure_ascii=False, default=str)
    except TypeError:
        return error_result("Internal error while serializing result")

    if truncate and len(text) > _MAX_OUTPUT:
        text = text[:_MAX_OUTPUT] + "\n... (data truncated)"
    return text
