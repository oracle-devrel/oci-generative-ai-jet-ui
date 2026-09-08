"""Layer 8: generic JSON landing validation."""

from data_migration_harness import source_config
from data_migration_harness.environment import oracle_pool
from data_migration_harness.tools import generic_oracle


def check() -> bool:
    source_count = source_config.collection().count_documents({})
    pool = oracle_pool()
    with pool.acquire() as conn:
        cur = conn.cursor()
        try:
            cur.execute(f"SELECT COUNT(*) FROM {generic_oracle.RAW_TABLE}")
            target_count = cur.fetchone()[0]
        except Exception:
            return False
    return source_count == target_count
