"""Layer 8: row count validation per the Oracle migration validation skill."""

from data_migration_harness import source_config
from data_migration_harness.environment import oracle_pool


def check() -> bool:
    mongo_count = source_config.collection().count_documents({})
    pool = oracle_pool()
    with pool.acquire() as conn:
        cur = conn.cursor()
        try:
            cur.execute("SELECT COUNT(*) FROM products")
            (oracle_count,) = cur.fetchone()
        except Exception:
            # products table missing (e.g. after a rehearsal reset);
            # counts can't match if the target side has no table.
            return False
    return mongo_count == oracle_count
