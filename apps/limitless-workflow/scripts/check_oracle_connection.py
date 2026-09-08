from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from limitless.db.pool import get_pool
from limitless.settings import Settings


def main() -> int:
    try:
        settings = Settings()
    except Exception as exc:
        print(f"Failed to load settings: {exc}")
        return 1

    print(f"Connection target: {settings.oracle_dsn}")
    print(f"Wallet mode: {'enabled' if settings.uses_wallet else 'disabled'}")
    print(f"Vector enabled: {settings.oracle_vector_enabled}")

    try:
        pool = get_pool(settings)
        with pool.acquire() as connection:
            with connection.cursor() as cursor:
                cursor.execute("select 'ok' from dual")
                result = cursor.fetchone()
        print(f"Connection successful: {result[0]}")
        return 0
    except Exception as exc:
        print(f"Connection failed: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
