"""Layer 8: content sampling per the Oracle migration validation skill."""

from data_migration_harness import source_config
from data_migration_harness.environment import oracle_pool


def check(n: int = 10) -> bool:
    mongo_sample = list(source_config.collection().aggregate([{"$sample": {"size": n}}]))
    pool = oracle_pool()
    with pool.acquire() as conn:
        cur = conn.cursor()
        for doc in mongo_sample:
            cur.execute("SELECT name FROM products WHERE mongo_id = :m", {"m": str(doc["_id"])})
            row = cur.fetchone()
            if not row or row[0] != doc["name"]:
                return False
    return True
