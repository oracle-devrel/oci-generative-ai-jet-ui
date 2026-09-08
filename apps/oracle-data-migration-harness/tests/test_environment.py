import pytest
from data_migration_harness.environment import mongo_client, oracle_pool

pytestmark = pytest.mark.integration


def test_oracle_pool_smoke():
    pool = oracle_pool()
    with pool.acquire() as conn:
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM DUAL")
        (val,) = cur.fetchone()
    assert val == 1


def test_mongo_smoke():
    client = mongo_client()
    assert client.admin.command("ping").get("ok") == 1.0
