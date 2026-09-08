# Migration Data Validation

## Overview

Data validation is the most overlooked phase of database migrations. The schema can be converted automatically, the data can load without errors, and the migration can appear successful — only for the application to silently return wrong results because rows are missing, numeric values have been truncated, dates are offset by hours due to timezone differences, or NULL handling differs between the source and Oracle.

This guide provides a comprehensive, query-driven data validation framework. Use these patterns to validate immediately after initial load, after each incremental sync, and as ongoing drift detection after cutover.

---

## Row Count Validation

The first and simplest validation is a row count comparison across all migrated tables.

### Basic Row Count Query

Run this on both source and target and compare results:

```sql
-- Source (PostgreSQL)
SELECT 'customers'::text AS table_name, COUNT(*) AS row_count FROM customers
UNION ALL SELECT 'orders', COUNT(*) FROM orders
UNION ALL SELECT 'order_items', COUNT(*) FROM order_items
UNION ALL SELECT 'products', COUNT(*) FROM products
ORDER BY table_name;

-- Oracle target (same pattern)
SELECT 'customers' AS table_name, COUNT(*) AS row_count FROM customers
UNION ALL SELECT 'orders', COUNT(*) FROM orders
UNION ALL SELECT 'order_items', COUNT(*) FROM order_items
UNION ALL SELECT 'products', COUNT(*) FROM products
ORDER BY table_name;
```

### Automated Row Count Comparison (PL/SQL)

This procedure stores expected row counts from the source and compares them to Oracle:

```sql
CREATE TABLE migration_row_counts (
    table_name       VARCHAR2(128)  NOT NULL,
    source_count     NUMBER         NOT NULL,
    oracle_count     NUMBER,
    captured_at      TIMESTAMP      DEFAULT SYSTIMESTAMP,
    validation_at    TIMESTAMP,
    difference       NUMBER GENERATED ALWAYS AS (oracle_count - source_count) VIRTUAL,
    status           VARCHAR2(10)   GENERATED ALWAYS AS
                         (CASE WHEN oracle_count = source_count THEN 'PASS'
                               WHEN oracle_count IS NULL THEN 'PENDING'
                               ELSE 'FAIL' END) VIRTUAL
);

-- After loading source counts (from source database query):
INSERT INTO migration_row_counts (table_name, source_count) VALUES
    ('CUSTOMERS',   150000),
    ('ORDERS',      1200000),
    ('ORDER_ITEMS', 4800000),
    ('PRODUCTS',    5000);

-- After migration, update with Oracle counts:
BEGIN
    FOR t IN (SELECT table_name FROM migration_row_counts WHERE oracle_count IS NULL) LOOP
        EXECUTE IMMEDIATE
            'UPDATE migration_row_counts
             SET oracle_count = (SELECT COUNT(*) FROM ' || t.table_name || '),
                 validation_at = SYSTIMESTAMP
             WHERE table_name = ''' || t.table_name || '''';
    END LOOP;
    COMMIT;
END;
/

-- Review results
SELECT table_name, source_count, oracle_count, difference, status
FROM migration_row_counts
ORDER BY status DESC, ABS(difference) DESC;
```

### Partitioned Table Row Count Validation

For partitioned tables, also validate per-partition counts:

```sql
-- Oracle: row count per partition
SELECT table_name, partition_name, num_rows
FROM user_tab_partitions
WHERE table_name = 'FACT_SALES'
ORDER BY partition_position;

-- Force fresh stats first if needed:
EXEC DBMS_STATS.GATHER_TABLE_STATS(USER, 'FACT_SALES', GRANULARITY => 'ALL');
```

---

## Hash-Based Comparison with ORA_HASH

Row counts confirm quantity but not content. Hash-based validation compares the actual data values.

### ORA_HASH Overview

`ORA_HASH(expr, max_bucket, seed)` returns a deterministic hash bucket number (0 to max_bucket) for any scalar expression. By concatenating all column values and hashing each row, then summing or XOR-ing the row hashes, you can produce a "fingerprint" of an entire table's content.

```sql
-- Oracle: compute a table-level hash fingerprint
SELECT
    SUM(ORA_HASH(
        customer_id || '|' || first_name || '|' || last_name || '|' ||
        email || '|' || TO_CHAR(created_date, 'YYYY-MM-DD HH24:MI:SS'),
        4294967295  -- max bucket = max 32-bit unsigned int
    )) AS table_hash,
    COUNT(*) AS row_count
FROM customers;
```

The result on Oracle should match a corresponding hash computed on the source database. Since hash functions differ by platform, you need to use the same hash algorithm or compare intermediate results.

### Cross-Platform Hash Comparison Strategy

Because `ORA_HASH` is Oracle-specific, use a platform-neutral approach: hash individual columns to strings, then compare those strings:

**Step 1: Export ordered key + hash from source (PostgreSQL):**

```sql
-- PostgreSQL: compute MD5 of each row, order by PK
SELECT
    customer_id,
    MD5(COALESCE(first_name, '') || '|' ||
        COALESCE(last_name, '')  || '|' ||
        COALESCE(email, '')      || '|' ||
        COALESCE(TO_CHAR(created_date, 'YYYY-MM-DD'), ''))
    AS row_hash
FROM customers
ORDER BY customer_id
LIMIT 1000;  -- validate a sample first
```

**Step 2: Compute the same hash in Oracle:**

```sql
-- Oracle: compute MD5 of each row using DBMS_CRYPTO
SELECT
    customer_id,
    LOWER(RAWTOHEX(
        DBMS_CRYPTO.HASH(
            UTL_I18N.STRING_TO_RAW(
                NVL(first_name, '') || '|' ||
                NVL(last_name, '')  || '|' ||
                NVL(email, '')      || '|' ||
                NVL(TO_CHAR(created_date, 'YYYY-MM-DD'), ''),
                'AL32UTF8'
            ),
            DBMS_CRYPTO.HASH_MD5
        )
    )) AS row_hash
FROM customers
WHERE customer_id <= 1000
ORDER BY customer_id;
```

**Step 3: Compare results** — export both result sets to CSV and diff them, or load Oracle results into a comparison table and join:

```sql
-- Load source hashes into staging
CREATE TABLE hash_staging_src (
    customer_id NUMBER,
    row_hash    VARCHAR2(32)
);

-- After loading source hashes via SQL*Loader or INSERT:
-- Compare against Oracle-computed hashes
SELECT
    o.customer_id,
    s.row_hash AS source_hash,
    o.row_hash AS oracle_hash,
    CASE WHEN s.row_hash = o.row_hash THEN 'MATCH' ELSE 'MISMATCH' END AS result
FROM (
    SELECT
        customer_id,
        LOWER(RAWTOHEX(DBMS_CRYPTO.HASH(
            UTL_I18N.STRING_TO_RAW(
                NVL(first_name,'') || '|' || NVL(last_name,'') || '|' ||
                NVL(email,'') || '|' || NVL(TO_CHAR(created_date,'YYYY-MM-DD'),''),
                'AL32UTF8'
            ), DBMS_CRYPTO.HASH_MD5
        ))) AS row_hash
    FROM customers
) o
JOIN hash_staging_src s ON o.customer_id = s.customer_id
WHERE s.row_hash != o.row_hash
ORDER BY o.customer_id;
```

---

## Data Sampling Strategies

Full-table hash validation is impractical for billion-row tables during initial validation. Use stratified sampling to achieve statistical confidence in less time.

### Random Sample Validation

```sql
-- Oracle: validate a random 0.1% sample of a large table
SELECT customer_id, email, created_date, status
FROM customers
SAMPLE(0.1)
ORDER BY customer_id;
-- SAMPLE(n) is Oracle-specific: selects approximately n% of rows
```

### Boundary Value Sampling

Always validate the extremes of value ranges:

```sql
-- Validate min/max values across key columns
SELECT
    'order_amount' AS column_name,
    MIN(total_amount) AS min_val,
    MAX(total_amount) AS max_val,
    AVG(total_amount) AS avg_val,
    STDDEV(total_amount) AS stddev_val,
    COUNT(*) AS total_rows,
    COUNT(CASE WHEN total_amount IS NULL THEN 1 END) AS null_count
FROM orders

UNION ALL

SELECT
    'customer_id',
    MIN(customer_id), MAX(customer_id), AVG(customer_id), STDDEV(customer_id),
    COUNT(*), COUNT(CASE WHEN customer_id IS NULL THEN 1 END)
FROM orders

UNION ALL

SELECT
    'order_date',
    TO_NUMBER(TO_CHAR(MIN(order_date),'YYYYMMDD')),
    TO_NUMBER(TO_CHAR(MAX(order_date),'YYYYMMDD')),
    NULL, NULL, COUNT(*),
    COUNT(CASE WHEN order_date IS NULL THEN 1 END)
FROM orders;
```

### Stratified Sample by Date Range

```sql
-- Validate row counts by month — should match source exactly
SELECT
    TO_CHAR(order_date, 'YYYY-MM') AS order_month,
    COUNT(*) AS row_count,
    SUM(total_amount) AS total_revenue,
    MIN(total_amount) AS min_order,
    MAX(total_amount) AS max_order
FROM orders
WHERE order_date >= DATE '2020-01-01'
GROUP BY TO_CHAR(order_date, 'YYYY-MM')
ORDER BY order_month;
```

### Top-N Validation

Check that the largest/most important records migrated correctly:

```sql
-- Compare the top 100 orders by value
SELECT order_id, customer_id, total_amount, status, order_date
FROM orders
ORDER BY total_amount DESC
FETCH FIRST 100 ROWS ONLY;
```

---

## Date and Numeric Precision Checks

### Date Offset Detection

One of the most common migration bugs is a timezone offset applied during migration that silently shifts all dates by hours.

```sql
-- Compare date distribution: verify no systematic shift
SELECT
    TRUNC(order_date, 'HH24') AS hour_of_day,
    COUNT(*) AS order_count
FROM orders
WHERE order_date BETWEEN DATE '2024-01-01' AND DATE '2024-01-31'
GROUP BY TRUNC(order_date, 'HH24')
ORDER BY hour_of_day;
-- Compare this distribution against the source — should be identical
```

```sql
-- Check for suspicious midnight concentration (may indicate DATE precision loss)
SELECT
    CASE WHEN TO_CHAR(order_date, 'HH24:MI:SS') = '00:00:00' THEN 'Midnight' ELSE 'Non-midnight' END AS time_class,
    COUNT(*) AS row_count
FROM orders
GROUP BY CASE WHEN TO_CHAR(order_date, 'HH24:MI:SS') = '00:00:00' THEN 'Midnight' ELSE 'Non-midnight' END;
-- If all dates are midnight and source had actual times, data has been truncated
```

```sql
-- Check TIMESTAMP precision
SELECT
    order_id,
    order_timestamp,
    TO_CHAR(order_timestamp, 'YYYY-MM-DD HH24:MI:SS.FF6') AS ts_with_microseconds
FROM orders
WHERE EXTRACT(SECOND FROM order_timestamp) != TRUNC(EXTRACT(SECOND FROM order_timestamp))
FETCH FIRST 10 ROWS ONLY;
-- If this returns rows, fractional seconds are preserved
```

### Numeric Precision Validation

```sql
-- Check for truncation in decimal columns
SELECT
    order_id,
    original_amount,  -- from source system (loaded into staging)
    oracle_amount,    -- in Oracle table
    original_amount - oracle_amount AS difference
FROM (
    SELECT
        o.order_id,
        s.amount  AS original_amount,
        o.amount  AS oracle_amount
    FROM orders o
    JOIN orders_source_staging s ON o.order_id = s.order_id
)
WHERE ABS(original_amount - oracle_amount) > 0.0001  -- tolerance for float comparison
ORDER BY ABS(original_amount - oracle_amount) DESC;
```

```sql
-- Check for scientific notation issues (BINARY_DOUBLE vs DECIMAL)
SELECT order_id, amount, TO_CHAR(amount, 'FM9999999999.999999') AS formatted_amount
FROM orders
WHERE amount != ROUND(amount, 4)  -- find amounts with more than 4 decimal places
FETCH FIRST 20 ROWS ONLY;
```

---

## NULL Handling Differences

### Empty String vs NULL (PostgreSQL → Oracle)

The most common NULL-related migration issue is empty string to NULL conversion. Oracle 21c and earlier treat `''` as NULL. PostgreSQL treats `''` as an empty string distinct from NULL.

```sql
-- Oracle: find rows where expected-non-null values are NULL
-- (may indicate empty strings from source were converted)
SELECT
    COUNT(*) AS total_rows,
    COUNT(CASE WHEN email IS NULL THEN 1 END) AS null_email_count,
    COUNT(CASE WHEN email = '' THEN 1 END) AS empty_email_count,  -- should always be 0 in Oracle
    COUNT(CASE WHEN LENGTH(email) = 0 THEN 1 END) AS zero_len_email_count  -- also 0
FROM customers;

-- Compare null percentages against source
-- Source NULL% should match Oracle NULL% + empty string %
```

```sql
-- Audit unexpected NULLs in NOT NULL columns
DECLARE
    v_count NUMBER;
BEGIN
    FOR col IN (
        SELECT table_name, column_name
        FROM user_tab_columns
        WHERE nullable = 'N'
          AND table_name IN ('CUSTOMERS', 'ORDERS', 'PRODUCTS')
    ) LOOP
        EXECUTE IMMEDIATE
            'SELECT COUNT(*) FROM ' || col.table_name ||
            ' WHERE ' || col.column_name || ' IS NULL'
        INTO v_count;
        IF v_count > 0 THEN
            DBMS_OUTPUT.PUT_LINE('UNEXPECTED NULL: ' || col.table_name ||
                                 '.' || col.column_name || ' = ' || v_count);
        END IF;
    END LOOP;
END;
/
```

### BOOLEAN Value Validation

```sql
-- Verify BOOLEAN columns migrated to 0/1 correctly
SELECT
    COUNT(*) AS total,
    COUNT(CASE WHEN is_active = 1 THEN 1 END) AS active_count,
    COUNT(CASE WHEN is_active = 0 THEN 1 END) AS inactive_count,
    COUNT(CASE WHEN is_active NOT IN (0, 1) THEN 1 END) AS invalid_count,
    COUNT(CASE WHEN is_active IS NULL THEN 1 END) AS null_count
FROM customers;
-- invalid_count and null_count should both be 0
```

---

## Building a Reconciliation Report

### Master Validation Report Query

This query produces a single summary report across all validated tables:

```sql
-- Create a validation results table
CREATE TABLE migration_validation_results (
    check_id        NUMBER GENERATED ALWAYS AS IDENTITY,
    table_name      VARCHAR2(128),
    check_type      VARCHAR2(50),
    check_detail    VARCHAR2(500),
    expected_value  NUMBER,
    actual_value    NUMBER,
    difference      NUMBER GENERATED ALWAYS AS (actual_value - expected_value) VIRTUAL,
    status          VARCHAR2(10),
    checked_at      TIMESTAMP DEFAULT SYSTIMESTAMP
);

-- Insert validation results
INSERT INTO migration_validation_results (table_name, check_type, check_detail, expected_value, actual_value, status)
-- Row counts (expected values loaded from source earlier)
SELECT
    mrc.table_name,
    'ROW_COUNT',
    'Total row count',
    mrc.source_count,
    mrc.oracle_count,
    CASE WHEN mrc.source_count = mrc.oracle_count THEN 'PASS' ELSE 'FAIL' END
FROM migration_row_counts mrc;

COMMIT;

-- Generate summary report
SELECT
    check_type,
    COUNT(*) AS total_checks,
    SUM(CASE WHEN status = 'PASS' THEN 1 ELSE 0 END) AS passed,
    SUM(CASE WHEN status = 'FAIL' THEN 1 ELSE 0 END) AS failed,
    SUM(CASE WHEN status = 'WARN' THEN 1 ELSE 0 END) AS warnings,
    ROUND(SUM(CASE WHEN status = 'PASS' THEN 1 ELSE 0 END) / COUNT(*) * 100, 1) AS pass_pct
FROM migration_validation_results
GROUP BY check_type
ORDER BY failed DESC, check_type;
```

### Executive Summary Report

```sql
SELECT
    'Migration Validation Summary' AS report_title,
    SYSTIMESTAMP AS report_time,
    COUNT(*) AS total_checks,
    SUM(CASE WHEN status = 'PASS' THEN 1 ELSE 0 END) AS total_passed,
    SUM(CASE WHEN status = 'FAIL' THEN 1 ELSE 0 END) AS total_failed,
    ROUND(SUM(CASE WHEN status = 'PASS' THEN 1 ELSE 0 END) / COUNT(*) * 100, 1) AS overall_pass_pct,
    CASE
        WHEN SUM(CASE WHEN status = 'FAIL' THEN 1 ELSE 0 END) = 0 THEN 'READY FOR CUTOVER'
        WHEN SUM(CASE WHEN status = 'FAIL' THEN 1 ELSE 0 END) <= 5 THEN 'REVIEW REQUIRED'
        ELSE 'NOT READY — FAILURES MUST BE RESOLVED'
    END AS overall_status
FROM migration_validation_results;
```

---

## Ongoing Drift Detection

After cutover, if the source database remains online for fallback purposes, or if you are running in parallel-write mode, detect drift between source and Oracle continuously.

### Drift Detection Framework

```sql
-- Drift check: track high-watermark row counts
CREATE TABLE drift_monitor (
    table_name      VARCHAR2(128)  NOT NULL,
    check_timestamp TIMESTAMP      DEFAULT SYSTIMESTAMP,
    oracle_count    NUMBER,
    expected_count  NUMBER,
    delta           NUMBER GENERATED ALWAYS AS (oracle_count - expected_count) VIRTUAL,
    drift_pct       NUMBER GENERATED ALWAYS AS
                        (ROUND((oracle_count - expected_count) / NULLIF(expected_count, 0) * 100, 4)) VIRTUAL
);

-- Scheduled drift check (run via DBMS_SCHEDULER)
CREATE OR REPLACE PROCEDURE run_drift_check AS
    v_count NUMBER;
BEGIN
    FOR t IN (SELECT DISTINCT table_name FROM migration_row_counts) LOOP
        EXECUTE IMMEDIATE 'SELECT COUNT(*) FROM ' || t.table_name INTO v_count;
        INSERT INTO drift_monitor (table_name, oracle_count, expected_count)
        SELECT t.table_name, v_count, MAX(oracle_count)
        FROM migration_row_counts
        WHERE table_name = t.table_name;
    END LOOP;
    COMMIT;
END;
/

-- Schedule drift check every hour
BEGIN
    DBMS_SCHEDULER.CREATE_JOB(
        job_name        => 'DRIFT_CHECK_JOB',
        job_type        => 'PLSQL_BLOCK',
        job_action      => 'BEGIN run_drift_check; END;',
        repeat_interval => 'FREQ=HOURLY',
        enabled         => TRUE
    );
END;
/
```

### Alert on Significant Drift

```sql
-- Query to identify tables with > 0.01% drift
SELECT table_name, check_timestamp, oracle_count, expected_count, drift_pct
FROM drift_monitor
WHERE drift_pct > 0.01  -- more than 0.01% row count difference
  AND check_timestamp > SYSTIMESTAMP - INTERVAL '24' HOUR
ORDER BY ABS(drift_pct) DESC;
```

### Checksum Drift Detection

For critical financial tables, run checksum drift checks on a scheduled basis:

```sql
-- Track aggregate checksums over time for critical tables
CREATE TABLE checksum_monitor (
    table_name       VARCHAR2(128),
    check_timestamp  TIMESTAMP DEFAULT SYSTIMESTAMP,
    row_count        NUMBER,
    sum_of_key_col   NUMBER,  -- e.g., SUM(total_amount)
    max_of_key_col   NUMBER,
    min_of_key_col   NUMBER
);

-- Financial integrity check for orders table
INSERT INTO checksum_monitor (table_name, row_count, sum_of_key_col, max_of_key_col, min_of_key_col)
SELECT 'ORDERS', COUNT(*), SUM(total_amount), MAX(total_amount), MIN(total_amount)
FROM orders;
COMMIT;

-- Compare current state to baseline
SELECT
    c.check_timestamp,
    c.row_count,
    b.row_count AS baseline_row_count,
    c.sum_of_key_col,
    b.sum_of_key_col AS baseline_sum,
    c.sum_of_key_col - b.sum_of_key_col AS revenue_drift
FROM checksum_monitor c
CROSS JOIN (
    SELECT row_count, sum_of_key_col
    FROM checksum_monitor
    WHERE table_name = 'ORDERS'
    ORDER BY check_timestamp ASC
    FETCH FIRST 1 ROW ONLY
) b
WHERE c.table_name = 'ORDERS'
ORDER BY c.check_timestamp DESC;
```

---

## Constraint Validation

After migration, verify that Oracle's constraints are actually enforced and that all data conforms:

```sql
-- Check for constraint violations using Oracle's VALIDATE feature
-- This re-validates existing data against existing constraints
ALTER TABLE customers ENABLE VALIDATE CONSTRAINT pk_customers;
ALTER TABLE orders ENABLE VALIDATE CONSTRAINT fk_orders_customer;

-- If Oracle raises ORA-02293, the data does not satisfy the constraint
-- Find the violating rows:
SELECT o.order_id, o.customer_id
FROM orders o
WHERE NOT EXISTS (
    SELECT 1 FROM customers c WHERE c.customer_id = o.customer_id
);

-- Find NOT NULL violations (should be none if data was loaded correctly)
SELECT COUNT(*) FROM customers WHERE customer_id IS NULL;
SELECT COUNT(*) FROM orders WHERE customer_id IS NULL;
SELECT COUNT(*) FROM orders WHERE order_date IS NULL;
```

---

## Best Practices

1. **Automate validation from day one.** Build validation queries into a script that can be run with one command. Manual validation is error-prone and skipped under time pressure.

2. **Validate incrementally, not only at the end.** Run row count checks after each table loads. Do not wait until all tables are loaded to discover a problem.

3. **Keep source row counts in a staging table.** Extract source counts before migration begins and store them in Oracle. This provides the baseline for comparison even after the source database is decommissioned.

4. **Test with edge case data explicitly.** Include rows with NULL values, maximum-length strings, dates near Unix epoch boundaries, negative numbers, and zero values in your sample validation queries.

5. **Compare aggregate checksums for financial data.** For any table containing monetary values, compare SUM(amount), SUM(quantity), etc. between source and Oracle. A row count match does not guarantee amount accuracy.

6. **Document every validation failure and resolution.** Keep a log of what failed, why it failed, and how it was resolved. This becomes the validation sign-off documentation for the go/no-go decision.

---

## Common Validation Pitfalls

**Pitfall 1 — Comparing FLOAT/DOUBLE precision across platforms:**
IEEE 754 floating-point arithmetic can produce slightly different results on different hardware. When comparing float columns across databases, use a tolerance:

```sql
-- Wrong: exact float comparison
WHERE ABS(source_val - oracle_val) = 0

-- Right: tolerance-based comparison
WHERE ABS(source_val - oracle_val) > 0.00001
```

**Pitfall 2 — Timezone in timestamp comparison:**
Source timestamps in UTC may appear as local time in Oracle or vice versa depending on session settings. Always use `AT TIME ZONE 'UTC'` when comparing timestamps from different systems.

**Pitfall 3 — Collation differences cause "missing" rows:**
If source database uses case-insensitive collation and values were normalized differently (e.g., 'ALICE' vs 'alice'), the data is present but appears different. Use `UPPER()` normalization in hash computations for string columns.

**Pitfall 4 — Row count can match but data is wrong:**
A row count match guarantees only that the right number of rows exists. Rows could be in the wrong order, with swapped column values, or corrupted. Always supplement row counts with hash-based or aggregate-based validation for critical tables.

**Pitfall 5 — Partitioned table stats lag:**
Oracle's `ALL_TAB_PARTITIONS.NUM_ROWS` is populated from statistics, not a live count. Use `COUNT(*)` for validation, not the statistics-based NUM_ROWS, until fresh stats are gathered post-load.

---

## Oracle Version Notes (19c vs 26ai)

- Baseline guidance in this file is valid for Oracle Database 19c unless a newer minimum version is explicitly called out.
- Features marked as 21c, 23c, or 23ai should be treated as Oracle Database 26ai-capable features; keep 19c-compatible alternatives for mixed-version estates.
- For dual-support environments, test syntax and package behavior in both 19c and 26ai because defaults and deprecations can differ by release update.

## Sources

- [Oracle Database 19c PL/SQL Packages Reference — DBMS_CRYPTO (for hash functions)](https://docs.oracle.com/en/database/oracle/oracle-database/19/arpls/DBMS_CRYPTO.html)
- [Oracle Database 19c Reference — DBA_TABLES (NUM_ROWS, AVG_ROW_LEN)](https://docs.oracle.com/en/database/oracle/oracle-database/19/refrn/DBA_TABLES.html)
- [Oracle Database 19c SQL Language Reference — DBMS_SQLHASH](https://docs.oracle.com/en/database/oracle/oracle-database/19/arpls/DBMS_SQLHASH.html)
