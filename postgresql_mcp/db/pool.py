"""Database connection pool management"""

import logging
from contextlib import asynccontextmanager

import asyncpg

from ..config import config

logger = logging.getLogger(__name__)


class DatabasePool:
    """PostgreSQL connection pool manager"""

    def __init__(self, **kwargs):
        self.pool = None
        self.kwargs = kwargs

    async def init(self):
        """Initialize the asyncpg connection pool"""
        db = config.database
        self.pool = await asyncpg.create_pool(
            host=db.host,
            port=db.port,
            database=db.database,
            user=db.user,
            password=db.password,
            min_size=2,
            max_size=10,
        )
        logger.info(
            "Pool initialized: %s:%d/%s (min=2, max=10)",
            db.host,
            db.port,
            db.database,
        )

    async def close(self):
        """Close the connection pool"""
        if self.pool:
            await self.pool.close()
            logger.info("Pool closed")

    @asynccontextmanager
    async def connection(self):
        """Context manager: acquire a connection from the pool"""
        if not self.pool:
            raise RuntimeError("Database pool not initialized — call init() first")
        async with self.pool.acquire() as conn:
            yield conn


# Singleton instance — created at import time
db_pool = DatabasePool()
