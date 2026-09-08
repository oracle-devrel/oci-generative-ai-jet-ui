# Migration Assessment Guide

## Overview

A thorough pre-migration assessment is the most critical phase of any database migration project. Skipping or rushing the assessment is the single most common cause of budget overruns, missed deadlines, and production incidents during migration projects. The assessment answers four questions: What needs to move? How complex is it? What will not translate automatically? And what is the risk?

This guide provides a comprehensive assessment checklist, schema complexity scoring methodology, a framework for identifying incompatible features, effort estimation guidance, a risk matrix, and guidance on using Oracle's Database Migration Assessment tools.

---

## Pre-Migration Assessment Checklist

### 1. Inventory and Scope

Work through the following inventory before writing a single line of migration code:

**Schema Objects:**

- [ ] Count all tables (include approximate row counts for each)
- [ ] Count all indexes (including clustered/covering/partial indexes)
- [ ] Count all views (regular, materialized/indexed, partitioned)
- [ ] Count all stored procedures
- [ ] Count all functions
- [ ] Count all triggers
- [ ] Count all packages (DB2, Oracle-to-Oracle)
- [ ] Count all sequences
- [ ] Count all synonyms
- [ ] Count all database links / linked servers
- [ ] Count all scheduled jobs / agents
- [ ] Count all external tables or linked file locations
- [ ] List all schemas/users in scope

**Data Characteristics:**

- [ ] Total database size in GB/TB
- [ ] Largest individual table (rows and bytes)
- [ ] Tables with LOB columns (CLOB, BLOB, TEXT, IMAGE, BYTEA, etc.)
- [ ] Tables with more than 50 columns (complexity indicator)
- [ ] Tables with JSON/XML/semi-structured data columns
- [ ] Tables with spatial/geometry columns
- [ ] Identification of binary or encrypted columns

**Feature Usage:**

- [ ] Partitioned tables (partition type and strategy)
- [ ] Full-text search indexes
- [ ] Proprietary index types (GiST, GIN for PostgreSQL; XML indexes for SQL Server)
- [ ] Row-level security / Virtual Private Database
- [ ] Audit logging mechanisms
- [ ] Replication configuration (publications, subscriptions, logical replication)
- [ ] Linked servers or database links to other systems
- [ ] CLR objects (SQL Server), C extensions (PostgreSQL), or Java stored procedures
- [ ] Custom aggregate functions
- [ ] User-defined types
- [ ] Proprietary procedural language features

**Application Connectivity:**

- [ ] List all applications connecting to the source database
- [ ] Identify connection strings / DSN configurations
- [ ] Identify connection pooling configurations (DRCP, pgBouncer, ProxySQL, etc.)
- [ ] List ORMs in use (Hibernate, SQLAlchemy, Entity Framework, etc.)
- [ ] Identify raw SQL in application code vs ORM-generated SQL
- [ ] Identify reporting tools (Tableau, Power BI, Crystal Reports, etc.) with direct DB connections

---

## Schema Complexity Scoring

Use this scoring model to estimate migration effort per object. Multiply the unit cost by the count to get total estimated days.

### Scoring Table

| Object Type                                                      | Low Complexity | Medium Complexity | High Complexity |
| ---------------------------------------------------------------- | -------------- | ----------------- | --------------- |
| Simple table (< 20 cols, no LOB, no partitioning)                | 0.1 days       | —                 | —               |
| Complex table (> 50 cols, LOB, or partitioned)                   | —              | 0.5 days          | 1 day           |
| Simple view (single table, basic filters)                        | 0.1 days       | —                 | —               |
| Complex view (multi-table joins, window functions)               | —              | 0.5 days          | 1 day           |
| Simple stored procedure (< 50 lines, basic CRUD)                 | 0.5 days       | —                 | —               |
| Medium stored procedure (50–200 lines, cursors, loops)           | —              | 1–2 days          | —               |
| Complex stored procedure (> 200 lines, dynamic SQL, temp tables) | —              | —                 | 3–5 days        |
| Simple trigger (audit logging, timestamp update)                 | 0.25 days      | —                 | —               |
| Complex trigger (multi-table, conditional, calling procedures)   | —              | 1 day             | —               |
| Simple function                                                  | 0.25 days      | —                 | —               |
| Complex function (recursive, polymorphic input)                  | —              | 1–2 days          | —               |
| Package (DB2/Oracle)                                             | —              | 2–5 days          | —               |
| Scheduled job / agent                                            | 0.5 days each  | —                 | —               |
| Full-text search feature                                         | —              | —                 | 3–10 days       |
| Spatial / geometry feature                                       | —              | —                 | 5–15 days       |
| CLR object                                                       | —              | —                 | 5–20 days       |

### Complexity Classification SQL Queries

Run these queries on the source database to classify objects by complexity:

```sql
-- SQL Server: Classify stored procedures by line count
SELECT
    OBJECT_NAME(p.object_id) AS proc_name,
    (SELECT COUNT(*) FROM sys.sql_modules m
     WHERE m.object_id = p.object_id) AS has_definition,
    LEN(sm.definition) AS char_count,
    CASE
        WHEN LEN(sm.definition) < 1000 THEN 'Low'
        WHEN LEN(sm.definition) < 5000 THEN 'Medium'
        ELSE 'High'
    END AS complexity
FROM sys.procedures p
JOIN sys.sql_modules sm ON p.object_id = sm.object_id
ORDER BY LEN(sm.definition) DESC;
```

```sql
-- PostgreSQL: classify functions by line count
SELECT
    n.nspname AS schema,
    p.proname AS function_name,
    pg_get_functiondef(p.oid) AS definition,
    CASE
        WHEN LENGTH(pg_get_functiondef(p.oid)) < 500  THEN 'Low'
        WHEN LENGTH(pg_get_functiondef(p.oid)) < 2500 THEN 'Medium'
        ELSE 'High'
    END AS complexity
FROM pg_proc p
JOIN pg_namespace n ON p.pronamespace = n.oid
WHERE n.nspname NOT IN ('pg_catalog', 'information_schema')
ORDER BY LENGTH(pg_get_functiondef(p.oid)) DESC;
```

```sql
-- Oracle source (for Oracle-to-Oracle migration):
SELECT
    owner,
    object_type,
    object_name,
    status,
    CASE
        WHEN dbms_metadata.get_ddl(object_type, object_name, owner) IS NULL THEN 'Unknown'
        WHEN LENGTH(dbms_metadata.get_ddl(object_type, object_name, owner)) < 500 THEN 'Low'
        WHEN LENGTH(dbms_metadata.get_ddl(object_type, object_name, owner)) < 3000 THEN 'Medium'
        ELSE 'High'
    END AS complexity
FROM all_objects
WHERE owner = 'SOURCE_SCHEMA'
  AND object_type IN ('PROCEDURE', 'FUNCTION', 'PACKAGE', 'TRIGGER', 'VIEW')
ORDER BY object_type, object_name;
```

---

## Identifying Incompatible Features

### PostgreSQL Incompatible Features

```sql
-- Find SERIAL columns (need IDENTITY or SEQUENCE in Oracle)
SELECT table_name, column_name, column_default
FROM information_schema.columns
WHERE column_default LIKE 'nextval(%'
  AND table_schema = 'public';

-- Find ARRAY columns (need normalization in Oracle)
SELECT table_name, column_name, data_type, udt_name
FROM information_schema.columns
WHERE data_type = 'ARRAY'
  AND table_schema = 'public';

-- Find BOOLEAN columns (need NUMBER(1) in Oracle pre-23ai)
SELECT table_name, column_name
FROM information_schema.columns
WHERE data_type = 'boolean'
  AND table_schema = 'public';

-- Find ENUM types (need VARCHAR2 + CHECK in Oracle)
SELECT typname, enumlabel
FROM pg_enum
JOIN pg_type ON pg_enum.enumtypid = pg_type.oid
ORDER BY typname, enumsortorder;

-- Find TEXT columns (may need CLOB decision)
SELECT table_name, column_name
FROM information_schema.columns
WHERE data_type = 'text'
  AND table_schema = 'public';

-- Find functions using PostgreSQL-specific features
SELECT routine_name, routine_definition
FROM information_schema.routines
WHERE routine_schema = 'public'
  AND (
    routine_definition ILIKE '%$1%'           -- PL/pgSQL variable syntax
    OR routine_definition ILIKE '%ILIKE%'     -- Case-insensitive LIKE
    OR routine_definition ILIKE '%generate_series%'  -- PG-specific
    OR routine_definition ILIKE '%array_agg%'        -- PG-specific
  );
```

### SQL Server Incompatible Features

```sql
-- Find IDENTITY columns
SELECT
    t.name AS table_name,
    c.name AS column_name,
    c.seed_value,
    c.increment_value
FROM sys.tables t
JOIN sys.columns c ON t.object_id = c.object_id
JOIN sys.identity_columns ic ON c.object_id = ic.object_id AND c.column_id = ic.column_id;

-- Find UNIQUEIDENTIFIER columns (need RAW(16) in Oracle)
SELECT TABLE_NAME, COLUMN_NAME
FROM INFORMATION_SCHEMA.COLUMNS
WHERE DATA_TYPE = 'uniqueidentifier';

-- Find procedures using dynamic SQL
SELECT OBJECT_NAME(object_id) AS proc_name
FROM sys.sql_modules
WHERE definition LIKE '%EXEC%(%'
   OR definition LIKE '%sp_executesql%'
   OR definition LIKE '%EXECUTE%(%';

-- Find CLR objects
SELECT assembly_name, create_date
FROM sys.assemblies
WHERE is_user_defined = 1;

-- Find linked server references
SELECT DISTINCT OBJECT_NAME(referencing_id) AS obj_name
FROM sys.sql_expression_dependencies
WHERE referenced_server_name IS NOT NULL;

-- Find full-text indexes
SELECT t.name AS table_name, c.name AS column_name
FROM sys.fulltext_index_columns fic
JOIN sys.tables t ON fic.object_id = t.object_id
JOIN sys.columns c ON fic.object_id = c.object_id AND fic.column_id = c.column_id;
```

### MySQL Incompatible Features

```sql
-- Find AUTO_INCREMENT columns
SELECT table_name, column_name
FROM information_schema.columns
WHERE extra = 'auto_increment'
  AND table_schema = DATABASE();

-- Find ENUM and SET columns
SELECT table_name, column_name, data_type, column_type
FROM information_schema.columns
WHERE data_type IN ('enum', 'set')
  AND table_schema = DATABASE();

-- Find columns with zero-date defaults
SELECT table_name, column_name, column_default
FROM information_schema.columns
WHERE column_default IN ('0000-00-00', '0000-00-00 00:00:00')
  AND table_schema = DATABASE();

-- Find stored procedures/functions using MySQL-specific functions
SELECT routine_name, routine_definition
FROM information_schema.routines
WHERE routine_schema = DATABASE()
  AND (
    routine_definition LIKE '%GROUP_CONCAT%'
    OR routine_definition LIKE '%LIMIT %'
    OR routine_definition LIKE '%IF(%'   -- MySQL IF() function
    OR routine_definition LIKE '%IFNULL%'
  );
```

---

## Estimating Effort

### Effort Estimation Framework

Use this formula as a baseline, then adjust for project-specific factors:

```
Total Effort = Schema Effort + Data Migration Effort + Testing Effort + Buffer

Schema Effort   = SUM(object_count × unit_cost_per_complexity_level)
Data Migration  = (total_GB / throughput_GB_per_hour) × validation_factor
Testing Effort  = 40% of Schema Effort (minimum)
Buffer          = 25% of total (for unknowns)
```

### Typical Throughput Benchmarks

| Migration Method                | Typical Throughput                             |
| ------------------------------- | ---------------------------------------------- |
| SQL\*Loader DIRECT path (local) | 1–5 GB/minute                                  |
| SQL\*Loader via network         | 100 MB–1 GB/minute                             |
| Data Pump (same server)         | 2–10 GB/minute                                 |
| JDBC row-by-row insert          | 10–50 MB/minute                                |
| Oracle ZDM + GoldenGate         | Varies; replication lag depends on change rate |

### Project Complexity Multipliers

| Factor                                      | Multiplier |
| ------------------------------------------- | ---------- |
| First Oracle migration for team             | 1.5×       |
| Complex stored procedures (> 50% of effort) | 1.3×       |
| Spatial / full-text / CLR features present  | 1.4×       |
| Low-downtime requirement (< 4 hours)        | 1.6×       |
| Data quality issues known to exist          | 1.4×       |
| Legacy codebase without test coverage       | 1.5×       |

### Sample Effort Estimate Worksheet

```
Source: SQL Server 2016
Target: Oracle 19c
Schema: 200 tables, 45 views, 120 stored procedures, 30 functions, 15 triggers

OBJECT EFFORT:
  200 tables × 0.2 days (mixed complexity avg)         =  40 days
   45 views × 0.3 days (mixed complexity avg)          =  14 days
   60 simple procedures × 0.5 days                     =  30 days
   40 medium procedures × 1.5 days                     =  60 days
   20 complex procedures × 4 days                      =  80 days
   30 functions × 0.5 days                             =  15 days
   15 triggers × 0.5 days                              =   8 days
SCHEMA SUBTOTAL:                                          247 days

DATA MIGRATION:
  500 GB / 1 GB/min = ~8 hours loading time
  + 16 hours for validation, re-runs, and error resolution =  4 days

TESTING:
  40% of 247 days                                       =  99 days

SUBTOTAL:                                               350 days

BUFFER (25%):                                            88 days

TOTAL ESTIMATE:                                         438 days
Multiplier (first Oracle migration):                    × 1.5
ADJUSTED TOTAL:                                         657 developer-days
```

---

## Risk Matrix

Rate each risk factor on a 1–5 scale for Likelihood and Impact. Multiply to get Risk Score.

| Risk Factor                      | Example Indicators                     | Likelihood (1-5) | Impact (1-5) | Mitigation                                           |
| -------------------------------- | -------------------------------------- | ---------------- | ------------ | ---------------------------------------------------- |
| Schema complexity high           | > 100 stored procedures, CLR objects   | ?                | ?            | Run tools assessment first; phase the migration      |
| Data quality issues              | Null violations, constraint mismatches | ?                | ?            | Run data quality profiling before migration          |
| Low-downtime requirement         | SLA < 4 hours maintenance window       | ?                | ?            | Plan GoldenGate / ZDM; test cutover in staging       |
| Application behavior differences | NULL semantics, case sensitivity       | ?                | ?            | Run full regression suite on migrated data           |
| Performance regression           | Different optimizer, missing stats     | ?                | ?            | Benchmark key queries before production cutover      |
| Rollback complexity              | Large data volume, no backups          | ?                | ?            | Plan rollback procedures; test them                  |
| Team skill gap                   | No Oracle experience on team           | ?                | ?            | Training, external Oracle DBA for support            |
| Third-party tool compatibility   | BI tools, ETL pipelines                | ?                | ?            | Audit all connections; test each tool against Oracle |

### Risk Scoring

| Score | Level    | Action                                        |
| ----- | -------- | --------------------------------------------- |
| 1–4   | Low      | Monitor; document in risk register            |
| 5–9   | Medium   | Assign owner; develop mitigation plan         |
| 10–15 | High     | Escalate; may delay project start             |
| 16–25 | Critical | Blocker; must resolve before migration starts |

---

## Oracle Database Migration Assessment Resources

Note: "Database Migration Assessment Framework (DMAF)" is not an Oracle product name. Oracle migration assessment resources are provided through Oracle SQL Developer Migration Workbench and OCI migration tooling for Oracle cloud targets.

### Oracle Cloud Migration Advisor

If the target is OCI (Oracle Autonomous Database or DBCS), use the Oracle Cloud Migration Advisor:

Note: The exact Oracle Cloud Migration Advisor setup flow can differ by OCI service generation and region. Check the current OCI documentation for your target service before use.

1. Install the **Oracle Cloud Database Migration** service or use the built-in OCI migration tooling
2. Connect the advisor to the source database
3. Run the workload capture to collect SQL and schema metadata
4. Review the advisor report for:
   - Compatibility issues
   - Performance risks
   - Recommended Oracle features to replace source features

### Manual Assessment Using Oracle Data Dictionary Queries

When assessing an Oracle-to-Oracle migration (e.g., on-prem to cloud):

```sql
-- Object count by type in source schema
SELECT object_type, COUNT(*) AS object_count, COUNT(CASE WHEN status != 'VALID' THEN 1 END) AS invalid_count
FROM all_objects
WHERE owner = 'SOURCE_SCHEMA'
GROUP BY object_type
ORDER BY object_count DESC;

-- Tables with partitions
SELECT table_name, partitioning_type, partition_count
FROM all_part_tables
WHERE owner = 'SOURCE_SCHEMA';

-- Tables with LOB columns
SELECT c.table_name, c.column_name, c.data_type
FROM all_tab_columns c
WHERE c.owner = 'SOURCE_SCHEMA'
  AND c.data_type IN ('CLOB', 'BLOB', 'NCLOB', 'BFILE')
ORDER BY c.table_name;

-- Database links in use
SELECT db_link, username, host FROM all_db_links WHERE owner = 'SOURCE_SCHEMA';

-- Packages with compile errors
SELECT owner, name, type, line, text
FROM all_errors
WHERE owner = 'SOURCE_SCHEMA'
ORDER BY name, line;

-- Sequences approaching max value
SELECT sequence_name, max_value, last_number,
       ROUND((last_number / NULLIF(max_value, 0)) * 100, 2) AS pct_used
FROM all_sequences
WHERE sequence_owner = 'SOURCE_SCHEMA'
ORDER BY pct_used DESC;
```

---

## Questions to Ask Before Starting

### Technical Questions

1. **What is the source database version?** Older versions may have deprecated features that add migration complexity.

2. **Are there any proprietary data types or extensions?** PostGIS, pg_trgm, hstore, SQL Server spatial, XML, etc. each require specific Oracle equivalents.

3. **What character sets are in use?** Source encoding (UTF-8, Latin-1, UTF-16) affects data conversion and Oracle NLS settings.

4. **What is the largest table?** And what is the acceptable load time for that table during migration?

5. **Are there any tables with no primary key?** These cause issues for replication-based migration tools.

6. **What is the maximum acceptable downtime?** This drives the choice between offline (Data Pump / SQL\*Loader) and online (GoldenGate / ZDM) migration methods.

7. **Is the database schema stable or actively changing?** A schema that is changing during migration requires change management procedures to capture DDL changes.

### Organizational Questions

8. **Who owns the application code?** Stored procedure changes may require application team involvement, not just DBA work.

9. **What is the test coverage?** A well-tested application makes it possible to detect regressions. No test coverage means manual regression testing is required.

10. **What are the compliance and audit requirements?** GDPR, HIPAA, PCI-DSS, SOX requirements may affect Oracle security configuration, encryption settings, and audit configuration.

11. **What is the rollback plan?** If migration fails at cutover, how quickly can you revert? Is a point-in-time restore available? Is the source system kept available during parallel operation?

12. **What is the go-live criteria?** Define specific, measurable go/no-go criteria before starting (see `migration-cutover-strategy.md`).

13. **Are there regulatory or contractual freeze periods?** Many organizations have change freeze windows (year-end, quarter-end) that must be avoided for major migrations.

14. **What are the performance SLAs?** Identify the top 10–20 most performance-critical queries. These must be benchmarked on Oracle before cutover.

---

## Assessment Deliverables

A complete migration assessment should produce the following deliverables:

1. **Schema Inventory Report:** Complete object counts by type and schema, with data size and row counts per table.

2. **Complexity Assessment Report:** Per-object complexity scores with justification and recommended approach.

3. **Incompatible Features List:** Specific features in the source database that have no Oracle equivalent or require significant redesign.

4. **Effort Estimate:** Days-effort broken down by phase and adjusted for complexity multipliers.

5. **Risk Register:** Identified risks with likelihood, impact, and mitigation plans.

6. **Migration Approach Document:** Recommended tool stack, migration phases, and timeline.

7. **Go/No-Go Criteria:** Specific, measurable criteria that must be met before production cutover.

8. **Rollback Plan:** Step-by-step procedure for reverting to the source database if migration fails.

---

## Oracle Version Notes (19c vs 26ai)

- Baseline guidance in this file is valid for Oracle Database 19c unless a newer minimum version is explicitly called out.
- Features marked as 21c, 23c, or 23ai should be treated as Oracle Database 26ai-capable features; keep 19c-compatible alternatives for mixed-version estates.
- For dual-support environments, test syntax and package behavior in both 19c and 26ai because defaults and deprecations can differ by release update.

## Sources

- [Oracle SQL Developer Migration documentation](https://docs.oracle.com/en/database/oracle/sql-developer/23.1/rptug/migration-workbench.html)
- [AWS Schema Conversion Tool — Assessment Reports](https://docs.aws.amazon.com/SchemaConversionTool/latest/userguide/CHAP_AssessmentReport.html)
- [Oracle Database 19c — DBMS_METADATA package](https://docs.oracle.com/en/database/oracle/oracle-database/19/arpls/DBMS_METADATA.html)
