"""Version Query Tool"""

import logging

from ..common.response import error_result, ok_result
from ..queries.version import version_queries
from .. import db

logger = logging.getLogger(__name__)


async def get_version() -> str:
    """Get PostgreSQL database version info.

    Returns:
        String with PostgreSQL version.
    """
    try:
        async with db.db_pool.connection() as conn:
            version = await conn.fetchval(version_queries["version"])
            return f"PostgreSQL version: {version}"
    except Exception as e:
        logger.error("Failed to get version: %s", e)
        return error_result(str(e))
