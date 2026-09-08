# Migrating MongoDB to Oracle

## Overview

Migrating from MongoDB to Oracle represents a fundamental shift in data modeling philosophy: from a document-oriented, schema-flexible NoSQL approach to a relational, schema-enforced model. However, Oracle has invested significantly in bridging this gap. Oracle Database 21c introduced native JSON storage with binary-encoded OSON format, and Oracle 23c introduced **JSON Relational Duality Views**, which allow document-style access over relational tables — reducing the friction between the two worlds considerably.

This guide covers document-to-relational mapping strategies, Oracle's JSON capabilities, aggregation pipeline translation, BSON type mapping, and data extraction from MongoDB.

---

## Document Model to Relational Mapping Strategies

### Strategy 1 — Full Normalization (Classic Relational)

Convert each MongoDB collection to a table. Decompose embedded documents and arrays into child tables with foreign keys. This approach gives maximum query flexibility and referential integrity.

**MongoDB document:**

```json
{
  "_id": ObjectId("65a1234567890abcdef12345"),
  "customer_name": "Acme Corp",
  "email": "contact@acme.com",
  "addresses": [
    { "type": "billing", "street": "123 Main St", "city": "Springfield", "zip": "12345" },
    { "type": "shipping", "street": "456 Elm Ave", "city": "Shelbyville", "zip": "67890" }
  ],
  "tags": ["enterprise", "preferred"],
  "metadata": { "created_by": "admin", "source": "CRM" }
}
```

**Oracle normalized schema:**

```sql
CREATE TABLE customers (
    customer_id   NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    mongo_id      VARCHAR2(24) UNIQUE NOT NULL,  -- preserve original _id
    customer_name VARCHAR2(500) NOT NULL,
    email         VARCHAR2(255),
    created_by    VARCHAR2(100),
    source        VARCHAR2(100)
);

CREATE TABLE customer_addresses (
    address_id  NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    customer_id NUMBER NOT NULL,
    addr_type   VARCHAR2(20),
    street      VARCHAR2(500),
    city        VARCHAR2(200),
    zip         VARCHAR2(20),
    CONSTRAINT fk_addr_customer FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);

CREATE TABLE customer_tags (
    tag_id      NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    customer_id NUMBER NOT NULL,
    tag_value   VARCHAR2(100),
    CONSTRAINT fk_tag_customer FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);
```

### Strategy 2 — Store as JSON in Oracle (Hybrid)

Keep the document structure in Oracle's native JSON column. Best for documents with highly variable or nested structures where relational normalization would be cumbersome.

```sql
-- Oracle 21c+ native JSON type
CREATE TABLE customers (
    customer_id NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    mongo_id    VARCHAR2(24) UNIQUE NOT NULL,
    doc         JSON NOT NULL
);

-- Oracle 12c-20c using CLOB with IS JSON check constraint
CREATE TABLE customers (
    customer_id NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    mongo_id    VARCHAR2(24) UNIQUE NOT NULL,
    doc         CLOB,
    CONSTRAINT chk_customers_json CHECK (doc IS JSON)
);

-- Insert a document
INSERT INTO customers (mongo_id, doc)
VALUES ('65a1234567890abcdef12345',
        '{"customer_name":"Acme Corp","email":"contact@acme.com"}');
```

### Strategy 3 — Oracle JSON Duality Views (23c) — Best of Both Worlds

JSON Relational Duality Views, introduced in Oracle 23ai, let you treat a relational schema as a document store. Applications can read and write JSON documents while Oracle stores data relationally. This is the most powerful approach for new Oracle-target migrations.

```sql
-- Underlying relational tables
CREATE TABLE customers (
    customer_id   NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    customer_name VARCHAR2(500) NOT NULL,
    email         VARCHAR2(255)
);

CREATE TABLE addresses (
    address_id  NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    customer_id NUMBER NOT NULL,
    addr_type   VARCHAR2(20),
    street      VARCHAR2(500),
    city        VARCHAR2(200),
    zip         VARCHAR2(20),
    CONSTRAINT fk_addr FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);

-- JSON Duality View — exposes relational data as documents
CREATE OR REPLACE JSON RELATIONAL DUALITY VIEW customers_dv AS
SELECT JSON {
    '_id'           : c.customer_id,
    'customerName'  : c.customer_name,
    'email'         : c.email,
    'addresses'     : [
        SELECT JSON {
            'type'   : a.addr_type,
            'street' : a.street,
            'city'   : a.city,
            'zip'    : a.zip
        }
        FROM addresses a WITH INSERT UPDATE DELETE
        WHERE a.customer_id = c.customer_id
    ]
}
FROM customers c WITH INSERT UPDATE DELETE;

-- Applications can now query and update via the duality view as if it were MongoDB:
SELECT doc FROM customers_dv WHERE json_value(doc, '$._id') = '42';
```

---

## BSON Types to Oracle Types

| MongoDB BSON Type            | Oracle Type                                               | Notes                                                 |
| ---------------------------- | --------------------------------------------------------- | ----------------------------------------------------- |
| `ObjectId`                   | `VARCHAR2(24)` or `RAW(12)`                               | 24-char hex string; store as VARCHAR2 for readability |
| `String`                     | `VARCHAR2(4000)` or `CLOB`                                | Depends on length                                     |
| `Number (int32)`             | `NUMBER(10)`                                              |                                                       |
| `Number (int64)`             | `NUMBER(19)`                                              |                                                       |
| `Number (double)`            | `BINARY_DOUBLE`                                           | IEEE 754 64-bit                                       |
| `Number (Decimal128)`        | `NUMBER(38,18)`                                           | High-precision decimal                                |
| `Boolean`                    | `NUMBER(1)` with CHECK (0,1)                              | Or Oracle 23ai/26ai BOOLEAN                           |
| `Date`                       | `TIMESTAMP WITH TIME ZONE`                                | BSON Date is UTC milliseconds since epoch             |
| `Null`                       | `NULL`                                                    |                                                       |
| `Array`                      | Child table (normalized) or JSON array in JSON column     |                                                       |
| `Embedded document`          | Separate table (normalized) or JSON object in JSON column |                                                       |
| `Binary data (BinData)`      | `BLOB` or `RAW(n)`                                        |                                                       |
| `ObjectId as _id`            | `VARCHAR2(24)` + primary key                              |                                                       |
| `UUID (BinData subtype 3/4)` | `RAW(16)` or `VARCHAR2(36)`                               |                                                       |
| `Regular expression`         | `VARCHAR2(500)`                                           | Store pattern and flags separately                    |
| `JavaScript code`            | `CLOB`                                                    | Store as text; not executable in Oracle               |
| `Timestamp (internal)`       | `TIMESTAMP`                                               | Internal BSON type; map to standard TIMESTAMP         |
| `MinKey / MaxKey`            | No equivalent                                             | Internal MongoDB comparison values                    |
| `Symbol` (deprecated)        | `VARCHAR2(500)`                                           |                                                       |

### Date Conversion

MongoDB BSON Date is stored as milliseconds since Unix epoch (UTC). Converting to Oracle TIMESTAMP WITH TIME ZONE:

```sql
-- Given mongo_ts as milliseconds since epoch (stored as NUMBER)
SELECT TIMESTAMP '1970-01-01 00:00:00 UTC' +
       NUMTODSINTERVAL(mongo_ts / 1000, 'SECOND') AS oracle_ts
FROM staging_raw;

-- Reverse: Oracle TIMESTAMP to MongoDB epoch ms (for comparison)
SELECT (oracle_ts - TIMESTAMP '1970-01-01 00:00:00 UTC') * 86400000 AS mongo_ms
FROM orders;
```

---

## Aggregation Pipeline to Oracle SQL

MongoDB's aggregation pipeline is a sequence of stages that transform documents. Each stage has an Oracle SQL equivalent.

### $match → WHERE

```javascript
// MongoDB
db.orders.aggregate([{ $match: { status: "shipped", total: { $gte: 100 } } }]);
```

```sql
-- Oracle
SELECT * FROM orders WHERE status = 'shipped' AND total >= 100;
```

### $group → GROUP BY / Aggregate Functions

```javascript
// MongoDB
db.orders.aggregate([
  {
    $group: {
      _id: "$customer_id",
      order_count: { $sum: 1 },
      total_spent: { $sum: "$amount" },
      avg_order: { $avg: "$amount" },
      max_order: { $max: "$amount" },
    },
  },
]);
```

```sql
-- Oracle
SELECT customer_id,
       COUNT(*)          AS order_count,
       SUM(amount)       AS total_spent,
       AVG(amount)       AS avg_order,
       MAX(amount)       AS max_order
FROM orders
GROUP BY customer_id;
```

### $project → SELECT column list

```javascript
// MongoDB
db.customers.aggregate([
  {
    $project: {
      customer_name: 1,
      email: 1,
      _id: 0,
      full_address: { $concat: ["$street", " ", "$city"] },
    },
  },
]);
```

```sql
-- Oracle
SELECT customer_name, email, street || ' ' || city AS full_address
FROM customers;
```

### $sort → ORDER BY

```javascript
// MongoDB
db.orders.aggregate([{ $sort: { total: -1, order_date: 1 } }]);
```

```sql
-- Oracle
SELECT * FROM orders ORDER BY total DESC, order_date ASC;
```

### $limit / $skip → FETCH FIRST / OFFSET

```javascript
// MongoDB
db.orders.aggregate([{ $skip: 20 }, { $limit: 10 }]);
```

```sql
-- Oracle
SELECT * FROM orders OFFSET 20 ROWS FETCH NEXT 10 ROWS ONLY;
```

### $lookup → JOIN

```javascript
// MongoDB $lookup (left outer join)
db.orders.aggregate([
  {
    $lookup: {
      from: "customers",
      localField: "customer_id",
      foreignField: "_id",
      as: "customer",
    },
  },
]);
```

```sql
-- Oracle
SELECT o.*, c.customer_name, c.email
FROM orders o
LEFT JOIN customers c ON o.customer_id = c.customer_id;
```

### $unwind → JSON_TABLE or Lateral Join

```javascript
// MongoDB $unwind (expand array into separate documents)
db.orders.aggregate([{ $unwind: "$line_items" }]);
```

```sql
-- Oracle: if line_items is a JSON array in a JSON column
SELECT o.order_id, o.order_date, li.*
FROM orders o,
     JSON_TABLE(o.line_items, '$[*]'
         COLUMNS (
             product_id NUMBER  PATH '$.product_id',
             qty        NUMBER  PATH '$.qty',
             price      NUMBER  PATH '$.price'
         )
     ) li;

-- Oracle: if line_items is a child table (normalized approach)
SELECT o.order_id, o.order_date, li.product_id, li.qty, li.price
FROM orders o
JOIN order_line_items li ON li.order_id = o.order_id;
```

### $addFields → SELECT with computed columns or CTE

```javascript
// MongoDB
db.orders.aggregate([{ $addFields: { tax_amount: { $multiply: ["$subtotal", 0.08] } } }]);
```

```sql
-- Oracle
SELECT o.*, subtotal * 0.08 AS tax_amount FROM orders o;
-- Or with CTE to carry the field forward:
WITH enriched AS (
    SELECT o.*, subtotal * 0.08 AS tax_amount FROM orders o
)
SELECT * FROM enriched WHERE tax_amount > 10;
```

### $facet → Multiple Aggregations

```javascript
// MongoDB $facet runs parallel aggregations
db.products.aggregate([
  {
    $facet: {
      byCategory: [{ $group: { _id: "$category", count: { $sum: 1 } } }],
      priceStats: [{ $group: { _id: null, avg: { $avg: "$price" }, max: { $max: "$price" } } }],
    },
  },
]);
```

```sql
-- Oracle: run as separate queries or combine with UNION
-- In a single query using GROUPING SETS:
SELECT category, COUNT(*) AS count, NULL AS avg_price, NULL AS max_price, 'CATEGORY' AS facet_type
FROM products
GROUP BY category
UNION ALL
SELECT NULL, NULL, AVG(price), MAX(price), 'PRICE_STATS'
FROM products;
```

### $bucket / $bucketAuto → WIDTH_BUCKET

```javascript
// MongoDB $bucket
db.orders.aggregate([
  {
    $bucket: {
      groupBy: "$amount",
      boundaries: [0, 100, 500, 1000, 5000],
      default: "Other",
    },
  },
]);
```

```sql
-- Oracle
SELECT
    CASE
        WHEN amount < 100   THEN '0-100'
        WHEN amount < 500   THEN '100-500'
        WHEN amount < 1000  THEN '500-1000'
        WHEN amount < 5000  THEN '1000-5000'
        ELSE 'Other'
    END AS bucket,
    COUNT(*) AS count
FROM orders
GROUP BY
    CASE
        WHEN amount < 100   THEN '0-100'
        WHEN amount < 500   THEN '100-500'
        WHEN amount < 1000  THEN '500-1000'
        WHEN amount < 5000  THEN '1000-5000'
        ELSE 'Other'
    END
ORDER BY MIN(amount);
```

---

## JSON_TABLE for Document Querying

`JSON_TABLE` is Oracle's most powerful tool for working with JSON data that has been stored in JSON or CLOB columns.

```sql
-- Sample data
CREATE TABLE mongo_import (
    id   NUMBER GENERATED ALWAYS AS IDENTITY,
    doc  JSON
);

-- Query nested document fields
SELECT jt.*
FROM mongo_import mi,
     JSON_TABLE(mi.doc, '$'
         COLUMNS (
             mongo_id      VARCHAR2(24)  PATH '$._id.$oid',
             customer_name VARCHAR2(500) PATH '$.customer_name',
             email         VARCHAR2(255) PATH '$.email',
             NESTED PATH '$.addresses[*]'
                 COLUMNS (
                     addr_type VARCHAR2(20)  PATH '$.type',
                     street    VARCHAR2(500) PATH '$.street',
                     city      VARCHAR2(200) PATH '$.city',
                     zip       VARCHAR2(20)  PATH '$.zip'
                 )
         )
     ) jt;
```

---

## Data Extraction from MongoDB

### Method 1 — mongoexport (JSON)

```bash
# Export collection to JSON (one document per line)
mongoexport \
  --host localhost:27017 \
  --db myapp \
  --collection orders \
  --out orders.json

# Export with query filter
mongoexport \
  --host localhost:27017 \
  --db myapp \
  --collection orders \
  --query '{"status": "shipped"}' \
  --out shipped_orders.json
```

### Method 2 — mongoexport (CSV)

```bash
# Export specific fields as CSV
mongoexport \
  --host localhost:27017 \
  --db myapp \
  --collection customers \
  --type csv \
  --fields _id,customer_name,email,created_at \
  --out customers.csv
```

### Method 3 — Python ETL with pymongo and cx_Oracle

For complex document structures requiring transformation:

```python
from pymongo import MongoClient
import oracledb  # python-oracledb (successor to cx_Oracle; install with: pip install oracledb)
import json
from bson import ObjectId
from datetime import datetime

# Source
mongo = MongoClient("mongodb://localhost:27017/")
db = mongo["myapp"]

# Target (thin mode — no Oracle Client libs required)
ora = oracledb.connect(user="user", password="pass", dsn="localhost:1521/ORCL")
ora_cur = ora.cursor()

# Stage 1: Load raw documents into staging JSON table
ora_cur.execute("DELETE FROM mongo_staging")

insert_sql = "INSERT INTO mongo_staging (mongo_id, raw_doc) VALUES (:1, :2)"
batch = []
for doc in db.orders.find():
    mongo_id = str(doc['_id'])
    # Convert ObjectId and datetime objects to serializable types
    doc['_id'] = str(doc['_id'])
    if 'created_at' in doc:
        doc['created_at'] = doc['created_at'].isoformat()
    batch.append((mongo_id, json.dumps(doc)))
    if len(batch) >= 1000:
        ora_cur.executemany(insert_sql, batch)
        batch = []

if batch:
    ora_cur.executemany(insert_sql, batch)
ora.commit()

# Stage 2: Transform and insert into target tables
ora_cur.execute("""
    INSERT INTO orders (mongo_id, customer_id, status, total, created_at)
    SELECT
        jt.mongo_id,
        TO_NUMBER(jt.customer_id),
        jt.status,
        TO_NUMBER(jt.total),
        TO_TIMESTAMP(jt.created_at, 'YYYY-MM-DD"T"HH24:MI:SS')
    FROM mongo_staging ms,
         JSON_TABLE(ms.raw_doc, '$' COLUMNS (
             mongo_id    VARCHAR2(24) PATH '$._id',
             customer_id VARCHAR2(50) PATH '$.customer_id',
             status      VARCHAR2(50) PATH '$.status',
             total       VARCHAR2(50) PATH '$.total',
             created_at  VARCHAR2(50) PATH '$.created_at'
         )) jt
""")
ora.commit()

mongo.close()
ora.close()
```

---

## Best Practices

1. **Preserve MongoDB \_id values during migration.** Store the original MongoDB ObjectId in a `mongo_id` column on the Oracle side. This allows reconciliation and simplifies rollback if needed.

2. **Use a staging JSON table as an intermediate step.** Load raw MongoDB JSON documents into an Oracle JSON staging table first, then transform to the relational target schema using SQL and JSON_TABLE. This separates the extraction and transformation phases.

3. **Profile your collections before normalizing.** MongoDB's schema flexibility means documents in the same collection may have very different structures. Query your collections to understand the actual field distribution:

   ```javascript
   // MongoDB: find all distinct top-level keys in a collection
   db.orders.aggregate([
     { $project: { keys: { $objectToArray: "$$ROOT" } } },
     { $unwind: "$keys" },
     { $group: { _id: "$keys.k", count: { $sum: 1 } } },
     { $sort: { count: -1 } },
   ]);
   ```

4. **Consider Oracle JSON Duality Views for applications needing document-style access.** If your application was written expecting MongoDB's document API, Duality Views (introduced in Oracle 23ai, available in 26ai) allow you to keep the JSON interface while storing data relationally.

5. **Handle missing fields gracefully.** MongoDB documents may be missing fields that others have. In Oracle, these become NULL. Use `JSON_VALUE(doc, '$.field' DEFAULT NULL ON ERROR)` for safe extraction.

6. **Index frequently queried JSON fields.** If using the hybrid JSON storage approach, create JSON Search Indexes or function-based indexes on frequently queried JSON paths:

   ```sql
   -- Function-based index on a JSON field
   CREATE INDEX idx_orders_status ON orders (JSON_VALUE(doc, '$.status'));

   -- Full JSON search index (Oracle Text based)
   CREATE SEARCH INDEX idx_orders_json ON orders (doc) FOR JSON;
   ```

---

## Common Migration Pitfalls

**Pitfall 1 — Polymorphic collections:**
MongoDB collections often contain documents of mixed shapes (e.g., an "events" collection with different fields per event type). In Oracle, use a base table with common fields plus a JSON column for variable fields, or use table-per-type with a discriminator column.

**Pitfall 2 — \_id type assumptions:**
Not all MongoDB \_id fields are ObjectIds. Applications sometimes use custom strings, integers, or compound values. Check the actual \_id types in each collection:

```javascript
db.orders.aggregate([{ $group: { _id: { $type: "$_id" }, count: { $sum: 1 } } }]);
```

**Pitfall 3 — Embedded arrays with updates:**
MongoDB allows efficient array element updates (`$push`, `$pull`, `$set.array.0`). Oracle relational requires DELETE + INSERT on child tables for equivalent operations. Review all array mutation patterns in your application code.

**Pitfall 4 — MongoDB transactions vs Oracle transactions:**
MongoDB only supports multi-document ACID transactions from version 4.0 (replica sets) and 4.2 (sharded clusters). Oracle has always had full ACID transactions. Applications that worked around MongoDB's historical lack of transactions may have complex compensation logic that can be simplified in Oracle.

**Pitfall 5 — Field name case sensitivity:**
MongoDB field names are case-sensitive. Oracle column names are case-insensitive (folded to uppercase) unless double-quoted. Map MongoDB camelCase field names to Oracle SNAKE_CASE column names to avoid quoting requirements:

- MongoDB: `customerName` → Oracle: `CUSTOMER_NAME`
- MongoDB: `createdAt` → Oracle: `CREATED_AT`

**Pitfall 6 — Date timezone handling:**
MongoDB BSON Date is always UTC. Oracle TIMESTAMP stores without timezone; TIMESTAMP WITH TIME ZONE stores the offset. Load as `TIMESTAMP WITH TIME ZONE` to preserve UTC intent, then let the application convert to local time as needed.

---

## Oracle Version Notes (19c vs 26ai)

- Baseline guidance in this file is valid for Oracle Database 19c unless a newer minimum version is explicitly called out.
- Features marked as 21c, 23c, or 23ai should be treated as Oracle Database 26ai-capable features; keep 19c-compatible alternatives for mixed-version estates.
- For dual-support environments, test syntax and package behavior in both 19c and 26ai because defaults and deprecations can differ by release update.

## Sources

- [Oracle Database 19c SQL Language Reference — JSON_TABLE](https://docs.oracle.com/en/database/oracle/oracle-database/19/sqlrf/JSON_TABLE.html)
- [Oracle Database 19c SQL Language Reference — JSON_VALUE](https://docs.oracle.com/en/database/oracle/oracle-database/19/sqlrf/JSON_VALUE.html)
- [Oracle Database 19c JSON Developer's Guide — Overview of Oracle Database Support for JSON](https://docs.oracle.com/en/database/oracle/oracle-database/19/adjsn/json-in-oracle-database.html)
- [Oracle Database 19c SQL Language Reference — CREATE TABLE (JSON column)](https://docs.oracle.com/en/database/oracle/oracle-database/19/sqlrf/CREATE-TABLE.html)
- [python-oracledb documentation](https://python-oracledb.readthedocs.io/en/latest/)
