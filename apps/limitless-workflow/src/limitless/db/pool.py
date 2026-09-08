from __future__ import annotations

from typing import Any

from limitless.settings import Settings

try:
    import oracledb
except ImportError:  # pragma: no cover - import guard for fresh environments
    oracledb = None  # type: ignore[assignment]

_pool = None


def _build_connect_kwargs(settings: Settings) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "user": settings.oracle_user,
        "password": settings.oracle_password,
        "dsn": settings.oracle_dsn,
    }

    if settings.uses_wallet:
        wallet_location = str(settings.oracle_wallet_location)
        kwargs["config_dir"] = wallet_location
        kwargs["wallet_location"] = wallet_location
        if settings.oracle_wallet_password:
            kwargs["wallet_password"] = settings.oracle_wallet_password

    return kwargs


def get_pool(settings: Settings | None = None):
    global _pool

    if oracledb is None:
        raise RuntimeError(
            "python-oracledb is not installed. Install dependencies from requirements.txt first."
        )

    if _pool is None:
        resolved_settings = settings or Settings()
        _pool = oracledb.create_pool(
            **_build_connect_kwargs(resolved_settings),
            min=1,
            max=4,
            increment=1,
        )

    return _pool


def close_pool() -> None:
    global _pool
    if _pool is not None:
        _pool.close()
        _pool = None
