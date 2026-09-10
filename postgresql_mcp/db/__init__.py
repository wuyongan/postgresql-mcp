"""Database module - connection pool and health management"""

from .pool import DatabasePool, db_pool

__all__ = ["DatabasePool", "db_pool"]
