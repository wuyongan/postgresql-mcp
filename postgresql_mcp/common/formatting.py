"""Common data formatting helpers"""


def rows_to_dicts(rows):
    """Convert an array of asyncpg Records to a list of plain dicts.

    Must be called inside the async with block while the connection
    is still active. Record objects become invalid after pool return.
    """
    if not rows:
        return []
    return [dict(r) for r in rows]


def truncate_rows(rows, limit):
    """Slice rows to limit and compute metadata.

    The rows list should already be plain dicts.
    """
    display = rows[:limit]
    return display, len(display), len(rows) > limit
