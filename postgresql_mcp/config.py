"""Configuration management for PostgreSQL MCP Server"""

import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

# Load .env file immediately when module is imported
try:
    from dotenv import load_dotenv
    # Find .env file in current directory or parent directories
    dotenv_path = Path(__file__).parent.parent / ".env"
    if dotenv_path.exists():
        load_dotenv(dotenv_path=dotenv_path)
        print(f"Loaded .env from {dotenv_path}")
except ImportError:
    pass  # python-dotenv not installed, use os.getenv only


@dataclass
class DatabaseConfig:
    """Database connection configuration"""
    host: str = "127.0.0.1"
    port: int = 5432
    database: str = "postgres"
    user: str = "postgres"
    password: str = ""
    
    @classmethod
    def from_env(cls) -> 'DatabaseConfig':
        """Create config from environment variables"""
        return cls(
            host=os.getenv("PG_HOST", "127.0.0.1"),
            port=int(os.getenv("PG_PORT", "5432")),
            database=os.getenv("PG_DATABASE", "postgres"),
            user=os.getenv("PG_USER", "postgres"),
            password=os.getenv("PG_PASSWORD", ""),
        )
    
    def to_dict(self) -> dict:
        """Convert to dictionary for asyncpg"""
        return {
            "host": self.host,
            "port": self.port,
            "database": self.database,
            "user": self.user,
            "password": self.password,
        }


@dataclass
class ServerConfig:
    """Server configuration"""
    port: int = 8000
    host: str = "0.0.0.0"
    log_level: str = "INFO"
    mcp_name: str = "postgresql-mcp"
    max_query_size: int = 100000
    result_limit: int = 1000
    
    @classmethod
    def from_env(cls) -> 'ServerConfig':
        """Create config from environment variables"""
        return cls(
            port=int(os.getenv("SERVER_PORT", "8000")),
            host=os.getenv("SERVER_HOST", "0.0.0.0"),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
        )


@dataclass
class AppConfig:
    """Complete application configuration"""
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    server: ServerConfig = field(default_factory=ServerConfig)
    
    @classmethod
    def from_env(cls) -> 'AppConfig':
        """Create complete config from environment"""
        return cls(
            database=DatabaseConfig.from_env(),
            server=ServerConfig.from_env(),
        )


# Global config instance - use from_env to load from .env
config = AppConfig.from_env()
