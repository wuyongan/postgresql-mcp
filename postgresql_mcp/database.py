"""Database connection management"""

import logging
from contextlib import asynccontextmanager
import asyncpg

from .config import config

logger = logging.getLogger(__name__)


class DatabasePool:
    """Manage PostgreSQL connection pool"""
    
    def __init__(self, **kwargs):
        self.pool = None
        self.kwargs = kwargs
    
    async def init(self):
        """Initialize the connection pool"""
        db_config = config.database
        self.pool = await asyncpg.create_pool(
            host=db_config.host,
            port=db_config.port,
            database=db_config.database,
            user=db_config.user,
            password=db_config.password,
            min_size=2,
            max_size=10,
        )
        logger.info("Database pool initialized: %s:%s/%s", 
                    db_config.host, db_config.port, db_config.database)
    
    async def close(self):
        """Close the connection pool"""
        if self.pool:
            await self.pool.close()
            logger.info("Database pool closed")
    
    @asynccontextmanager
    async def connection(self):
        """Get a connection from the pool"""
        if not self.pool:
            raise RuntimeError("Database pool not initialized")
        async with self.pool.acquire() as conn:
            yield conn
    
    async def health_check(self) -> bool:
        """Check if database connection is healthy"""
        try:
            async with self.pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
                return True
        except Exception:
            return False


# Global database pool instance
db_pool = DatabasePool()
