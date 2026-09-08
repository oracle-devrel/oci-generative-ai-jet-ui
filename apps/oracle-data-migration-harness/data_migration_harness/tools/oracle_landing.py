"""Layer 3: Oracle landing path. Stages Mongo docs as JSON in Oracle."""

import json

from data_migration_harness.environment import oracle_pool


def create_landing_table(table: str = "products_raw"):
    pool = oracle_pool()
    with pool.acquire() as conn:
        cur = conn.cursor()
        cur.execute(
            f"BEGIN EXECUTE IMMEDIATE 'DROP TABLE {table}'; EXCEPTION WHEN OTHERS THEN NULL; END;"
        )
        cur.execute(
            f"""
            CREATE TABLE {table} (
                id NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                mongo_id VARCHAR2(48) UNIQUE,
                doc JSON NOT NULL
            )
        """
        )
        conn.commit()


def land_documents(docs: list[dict], table: str = "products_raw") -> int:
    pool = oracle_pool()
    with pool.acquire() as conn:
        cur = conn.cursor()
        rows = []
        for d in docs:
            mid = str(d.get("_id"))
            payload = {k: v for k, v in d.items() if k not in ("_id", "review_embedding")}
            payload["_mongo_id"] = mid
            rows.append((mid, json.dumps(payload, default=str)))
        cur.executemany(f"INSERT INTO {table} (mongo_id, doc) VALUES (:1, :2)", rows)
        conn.commit()
    return len(rows)
