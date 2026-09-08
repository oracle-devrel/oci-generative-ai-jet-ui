"""
Oracle Database connection configuration for the reasoning datalake.

Uses python-oracledb in thin mode (no Oracle Client required).
Connection parameters are read from environment variables with sensible
defaults for a local Oracle 26ai Free container.

Environment variables:
    ORACLE_DB_HOST       - Database host (default: localhost)
    ORACLE_DB_PORT       - Database port (default: 1521)
    ORACLE_DB_SERVICE    - Service name  (default: FREEPDB1)
    ORACLE_DB_USER       - Database user (default: reasoning)
    ORACLE_DB_PASSWORD   - Database password (default: reasoning)
    ORACLE_DB_POOL_MIN   - Minimum pool size (default: 2)
    ORACLE_DB_POOL_MAX   - Maximum pool size (default: 10)
"""

import os
from dataclasses import dataclass


@dataclass
class DatabaseConfig:
    """Oracle Database connection configuration."""

    host: str = "localhost"
    port: int = 1521
    service_name: str = "FREEPDB1"
    user: str = "reasoning"
    password: str = "reasoning"
    pool_min: int = 2
    pool_max: int = 10
    echo: bool = False

    @property
    def connection_url(self) -> str:
        """SQLAlchemy connection URL using oracledb dialect (thin mode)."""
        return (
            f"oracle+oracledb://{self.user}:{self.password}"
            f"@{self.host}:{self.port}/?service_name={self.service_name}"
        )

    @property
    def dsn(self) -> str:
        """Raw DSN string for direct oracledb connections."""
        return f"{self.host}:{self.port}/{self.service_name}"

    def __repr__(self) -> str:
        return (
            f"DatabaseConfig(host={self.host!r}, port={self.port}, "
            f"service_name={self.service_name!r}, user={self.user!r})"
        )


def get_db_config() -> DatabaseConfig:
    """
    Build a DatabaseConfig from environment variables.

    Falls back to defaults suitable for a local Oracle 26ai Free container
    (localhost:1521/FREEPDB1, user/pass = reasoning/reasoning).
    """
    return DatabaseConfig(
        host=os.environ.get("ORACLE_DB_HOST", "localhost"),
        port=int(os.environ.get("ORACLE_DB_PORT", "1521")),
        service_name=os.environ.get("ORACLE_DB_SERVICE", "FREEPDB1"),
        user=os.environ.get("ORACLE_DB_USER", "reasoning"),
        password=os.environ.get("ORACLE_DB_PASSWORD", "reasoning"),
        pool_min=int(os.environ.get("ORACLE_DB_POOL_MIN", "2")),
        pool_max=int(os.environ.get("ORACLE_DB_POOL_MAX", "10")),
    )
