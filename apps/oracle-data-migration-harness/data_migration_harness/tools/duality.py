"""Layer 3: JSON Relational Duality. The unlock."""

from data_migration_harness.environment import oracle_pool

PRODUCT_DDL = """
CREATE TABLE products (
    product_id NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    mongo_id   VARCHAR2(48) UNIQUE NOT NULL,
    name       VARCHAR2(200) NOT NULL,
    category   VARCHAR2(60)  NOT NULL,
    price      NUMBER(10, 2) NOT NULL,
    description VARCHAR2(1000),
    vendor_name VARCHAR2(120),
    vendor_country VARCHAR2(8),
    released_at DATE
)
"""

REVIEW_DDL = """
CREATE TABLE reviews (
    review_id NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    product_id NUMBER NOT NULL REFERENCES products(product_id),
    reviewer_id VARCHAR2(48),
    rating NUMBER(1) NOT NULL CHECK (rating BETWEEN 1 AND 5),
    verified_buyer NUMBER(1) NOT NULL,
    text VARCHAR2(2000),
    posted_at DATE
)
"""

DUALITY_VIEW = """
CREATE OR REPLACE JSON RELATIONAL DUALITY VIEW products_dv AS
  SELECT JSON {
    '_id'         : p.product_id,
    'mongo_id'    : p.mongo_id,
    'name'        : p.name,
    'category'    : p.category,
    'price'       : p.price,
    'description' : p.description,
    'vendor'      : { 'name' : p.vendor_name, 'country' : p.vendor_country },
    'released_at' : p.released_at,
    'reviews'     : [
        SELECT JSON {
          'review_id'      : r.review_id,
          'reviewer_id'    : r.reviewer_id,
          'rating'         : r.rating,
          'verified_buyer' : r.verified_buyer,
          'text'           : r.text,
          'posted_at'      : r.posted_at
        }
        FROM reviews r WITH UPDATE
        WHERE r.product_id = p.product_id
    ]
  }
  FROM products p WITH UPDATE
"""


def create_relational_schema():
    pool = oracle_pool()
    with pool.acquire() as conn:
        cur = conn.cursor()
        for stmt in (
            "DROP VIEW products_dv",
            "DROP TABLE reviews",
            "DROP TABLE products",
        ):
            try:
                cur.execute(stmt)
            except Exception:
                pass
        cur.execute(PRODUCT_DDL)
        cur.execute(REVIEW_DDL)
        cur.execute(DUALITY_VIEW)
        conn.commit()


def populate_from_landing(table: str = "products_raw"):
    pool = oracle_pool()
    with pool.acquire() as conn:
        cur = conn.cursor()
        cur.execute(
            f"""
            INSERT INTO products (mongo_id, name, category, price, description, vendor_name, vendor_country, released_at)
            SELECT
                JSON_VALUE(doc, '$._mongo_id'),
                JSON_VALUE(doc, '$.name'),
                JSON_VALUE(doc, '$.category'),
                TO_NUMBER(JSON_VALUE(doc, '$.price')),
                JSON_VALUE(doc, '$.description'),
                JSON_VALUE(doc, '$.vendor.name'),
                JSON_VALUE(doc, '$.vendor.country'),
                TO_DATE(SUBSTR(JSON_VALUE(doc, '$.released_at'), 1, 10), 'YYYY-MM-DD')
            FROM {table}
        """
        )
        cur.execute(
            f"""
            INSERT INTO reviews (product_id, reviewer_id, rating, verified_buyer, text, posted_at)
            SELECT
                p.product_id, jt.reviewer_id, jt.rating,
                CASE WHEN jt.verified_buyer = 'true' THEN 1 ELSE 0 END,
                jt.text,
                TO_DATE(SUBSTR(jt.posted_at, 1, 10), 'YYYY-MM-DD')
            FROM {table} l
            JOIN products p ON p.mongo_id = JSON_VALUE(l.doc, '$._mongo_id')
            CROSS APPLY JSON_TABLE(l.doc, '$.reviews[*]'
                COLUMNS (
                    reviewer_id    VARCHAR2(48)   PATH '$.reviewer_id',
                    rating         NUMBER         PATH '$.rating',
                    verified_buyer VARCHAR2(8)    PATH '$.verified_buyer',
                    text           VARCHAR2(2000) PATH '$.text',
                    posted_at      VARCHAR2(40)   PATH '$.posted_at'
                )
            ) jt
        """
        )
        conn.commit()


def run_sql_aggregation(sql: str, params: dict | None = None) -> list[dict]:
    pool = oracle_pool()
    with pool.acquire() as conn:
        cur = conn.cursor()
        cur.execute(sql, params or {})
        cols = [c[0].lower() for c in cur.description]
        return [dict(zip(cols, row, strict=False)) for row in cur.fetchall()]


DEMO_AGGREGATION = """
SELECT p.category,
       ROUND(AVG(r.rating), 2) AS avg_rating,
       COUNT(*) AS review_count
FROM products p
JOIN reviews r ON r.product_id = p.product_id
WHERE p.price < :max_price
  AND r.verified_buyer = 1
  AND r.posted_at > SYSDATE - 90
GROUP BY p.category
ORDER BY avg_rating DESC
"""
