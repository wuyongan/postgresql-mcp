"""SQL query definitions — separates raw SQL from business logic"""

from .schema import schema_queries
from .table import table_queries

__all__ = ["schema_queries", "table_queries"]
