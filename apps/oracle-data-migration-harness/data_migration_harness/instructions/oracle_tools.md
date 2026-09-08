# Oracle Migration Tools Reference

## Overview

Migrating a database to Oracle is almost never a purely manual effort. A suite of tools exists to automate schema conversion, data migration, assessment, and ongoing replication. This guide covers the most important tools in the Oracle migration ecosystem: Oracle SQL Developer Migration Workbench, AWS Schema Conversion Tool (SCT), SSMA for Oracle, ora2pg, Oracle Zero Downtime Migration (ZDM), and a capability comparison matrix.

Understanding which tool to use — and for which phase — is as important as knowing the tool itself. Most migrations require at least two tools: one for schema conversion and one for data movement.

---

## Oracle SQL Developer Migration Workbench

Oracle SQL Developer includes a built-in Migration Workbench that supports migrations from MySQL, SQL Server, Sybase ASE, DB2, Microsoft Access, PostgreSQL, and Teradata (using their respective JDBC drivers).

### Step-by-Step: SQL Server to Oracle Migration

#### Step 1 — Set Up a Migration Repository

The Migration Workbench requires a dedicated Oracle schema to store migration metadata.

```sql
-- Create a dedicated migration repository schema
CREATE USER migration_repo IDENTIFIED BY "repo_password"
    DEFAULT TABLESPACE users QUOTA UNLIMITED ON users;
GRANT CREATE SESSION, CREATE TABLE, CREATE SEQUENCE, CREATE PROCEDURE TO migration_repo;
GRANT CREATE VIEW TO migration_repo;
GRANT CREATE MATERIALIZED VIEW TO migration_repo;
```

In SQL Developer: **Tools → Migration → Create Migration Repository** — point it at the migration_repo schema.

#### Step 2 — Create Source Database Connection

- File → New Connection → Select "SQL Server" as connection type
- Provide JDBC URL, credentials, and test connectivity
- Tip: You need the SQL Server JDBC driver (jtds or Microsoft JDBC) in SQL Developer's classpath

#### Step 3 — Capture the Source Database

1. In the Migration Workbench (Tools → Migration), start a new migration project
2. Right-click the source connection → **Capture SQL Server Database**
3. Select the databases/schemas to capture
4. SQL Developer reads all DDL, constraints, views, stored procedures, and data

#### Step 4 — Convert

1. Right-click the captured source objects → **Convert to Oracle**
2. SQL Developer generates Oracle DDL for all captured objects
3. Review the **Migration Log** for errors and warnings:
   - Green: converted automatically
   - Yellow: converted with caveats
   - Red: could not convert — requires manual intervention

#### Step 5 — Inspect and Edit Generated DDL

Navigate the converted objects in the Migration Projects tree. Click each object to see the generated Oracle DDL. Edit directly in SQL Developer for objects flagged with warnings.

Common manual corrections:

- Stored procedures with dynamic SQL
- T-SQL-specific system functions
- Identity column seed/increment values
- Collation-specific comparisons

#### Step 6 — Create Target Oracle Connection

- Add a connection to your target Oracle database
- Ensure the target user/schema has CREATE TABLE, CREATE PROCEDURE, CREATE INDEX, etc. privileges

#### Step 7 — Migrate the Schema

1. Right-click the converted schema → **Migrate Schema to Oracle**
2. SQL Developer executes all DDL against the Oracle target
3. Review errors in the output window

#### Step 8 — Migrate Data

1. Right-click the migration project → **Migrate Data**
2. SQL Developer streams rows from SQL Server to Oracle via JDBC
3. Monitor progress in the Migration Data panel

#### Step 9 — Validate

SQL Developer provides a basic row count comparison after migration. For thorough validation, see `migration-data-validation.md`.

### What SQL Developer Migration Workbench Handles Well

- Table definitions with most data types
- Indexes and constraints (primary key, unique, foreign key, check)
- Views (with syntax conversion)
- Sequences and identity columns
- Simple stored procedures and functions
- Triggers (with partial conversion)

### Limitations

- Cannot handle CLR objects (SQL Server)
- Limited support for dynamic SQL in procedures
- Does not handle full-text indexes
- Performance for large data migrations (millions of rows) is slower than SQL\*Loader direct path
- No incremental/CDC capability for low-downtime migrations

---

## AWS Schema Conversion Tool (SCT) — Oracle Target

AWS SCT was primarily designed for AWS-target migrations (RDS, Aurora, Redshift), but it also supports Oracle as both a source and a target. It provides a sophisticated rule engine for procedure conversion.

### Supported Sources for Oracle Target

- SQL Server → Oracle
- MySQL → Oracle
- PostgreSQL → Oracle
- Teradata → Oracle
- SAP ASE (Sybase) → Oracle

### Using AWS SCT for Oracle

1. **Install SCT** from the AWS download page. SCT runs as a standalone desktop application.

2. **Create a new project:**
   - File → New Project
   - Select source database type and target "Oracle"

3. **Connect to source and target databases**

4. **Run the Assessment Report:**
   - View → Assessment Report
   - SCT categorizes each object: automatically converted, converted with warnings, action required
   - Each category has a percentage coverage estimate

5. **Review the conversion dashboard:**
   - The dashboard shows a "conversion complexity" score
   - Objects requiring manual action are highlighted with explanations

6. **Convert the schema:**
   - Right-click source objects → Convert Schema
   - Review the converted Oracle DDL in the right panel

7. **Handle action items:**
   - SCT provides specific "to-do" items with Oracle documentation links
   - For each action item, edit the generated code or accept SCT's suggestion

8. **Apply to Oracle target:**
   - Right-click converted schema → Apply to Database

### SCT Extension Pack

For SQL Server migrations, SCT provides an Extension Pack that creates Oracle implementations of SQL Server system functions:

```sql
-- SCT installs an extension schema with Oracle equivalents of:
-- CHARINDEX → aws_sqlserver_ext.charindex(...)
-- LEFT       → aws_sqlserver_ext.left(...)
-- FORMAT     → aws_sqlserver_ext.format(...)
```

This allows converted code to call these functions without rewriting every occurrence. However, long-term you should replace extension pack calls with native Oracle equivalents.

### AWS SCT Strengths

- Excellent SQL Server to Oracle conversion quality
- Handles complex T-SQL patterns
- Extension pack for unmappable functions
- Good assessment metrics for effort estimation
- Free to use

### AWS SCT Limitations

- Requires AWS account setup even for non-AWS migrations
- Some complex stored procedures still require manual work
- UI can be slow for very large schemas
- Does not perform data migration (use AWS DMS or SQL\*Loader separately)

---

## SSMA (SQL Server Migration Assistant) for Oracle

> **Direction Correction:** SSMA for Oracle migrates FROM Oracle TO SQL Server (not the reverse). The section title can be misleading. This tool is not used when Oracle is the migration target.

Note: SSMA for Oracle migrates FROM Oracle TO SQL Server. For SQL Server-to-Oracle migrations, use AWS SCT or SQL Developer Migration Workbench instead. The note in the `migrate-sqlserver-to-oracle.md` guide referencing "SSMA for Oracle" as enabling SQL Server → Oracle should be understood to mean using AWS SCT or SQL Developer, not SSMA for Oracle specifically.

The SSMA family includes:

- SSMA for Oracle (Oracle → SQL Server)
- SSMA for MySQL (MySQL → SQL Server/Azure SQL)
- SSMA for Sybase (Sybase → SQL Server)
- SSMA for Access (Access → SQL Server)

For SQL Server → Oracle migration specifically, AWS SCT or SQL Developer Migration Workbench are more appropriate.

### What SSMA Converts (Oracle to SQL Server direction)

- Tables, views, sequences, synonyms
- Stored procedures, functions, packages, triggers
- PL/SQL to T-SQL translation
- ROWNUM to TOP/ROW_NUMBER()
- DECODE to CASE
- Oracle date/time functions to SQL Server equivalents

---

## ora2pg — Oracle/MySQL to PostgreSQL (NOT an Oracle target tool)

> **Direction Correction:** ora2pg is an open-source Perl tool that migrates **Oracle** (or MySQL) databases **to PostgreSQL**. It is **not** a tool for migrating to Oracle. The source is Oracle or MySQL; the target is always PostgreSQL. Do not use ora2pg when Oracle is the migration target. For PostgreSQL-to-Oracle migrations use SQL Developer Migration Workbench or manual export/SQL\*Loader workflows instead.

ora2pg is listed here for completeness, as it is sometimes relevant when an organization is migrating away from Oracle to PostgreSQL (the reverse of the focus of this guide). Its assessment report format is also a useful reference for complexity estimation methodology.

### Assessment Report Format (for reference)

```
-------------------------------------------------------------------------------
Ora2Pg migration level : B-5
-------------------------------------------------------------------------------
Total estimated cost: 226 workday(s)
Migration levels:
  A - Migration that might be run automatically
  B - Migration with code rewrite and a human action is required
  C - Migration that has no equivalent in Oracle
-------------------------------------------------------------------------------
Object type | Number | Invalid | Estimated cost | Comments
-------------------------------------------------------------------------------
TABLE       |    145 |       0 |             29 |
VIEW        |     42 |       3 |             21 |
PROCEDURE   |     67 |      12 |            134 |
FUNCTION    |     23 |       2 |             34 |
TRIGGER     |     18 |       0 |              8 |
-------------------------------------------------------------------------------
```

### ora2pg Notes

- Migrates Oracle → PostgreSQL (and MySQL → PostgreSQL); Oracle is the **source**, not the target
- Free and open source; actively maintained
- Provides a migration complexity assessment report
- Not applicable for any migration where Oracle is the destination

---

## Oracle Zero Downtime Migration (ZDM)

Oracle Zero Downtime Migration is Oracle's enterprise tool for migrating Oracle databases to Oracle-hosted targets — including Oracle Cloud Infrastructure (OCI), Oracle Database@Azure, Oracle Database@Google Cloud, Oracle Database@AWS, Exadata Cloud at Customer, and on-premises Exadata — with minimal or zero downtime. It uses Oracle GoldenGate for continuous replication during the online migration cutover window. The source database can be on-premises, on OCI, or on a third-party cloud.

### ZDM Architecture

```
Source Oracle DB
     |
     v (initial bulk copy via Data Pump or RMAN)
Target Oracle DB (OCI, Exadata, Autonomous)
     |
     ^ (continuous redo log replication via GoldenGate)
     |
[Cutover point: redirect application connections]
```

### ZDM Migration Phases

1. **VALIDATE** — Check prerequisites: connectivity, version compatibility, space, privileges
2. **SETUP** — Configure GoldenGate, network, target database
3. **INITIALIZE** — Bulk transfer of initial data via Data Pump or RMAN
4. **REPLICATE** — GoldenGate replicates ongoing changes from source to target
5. **MONITOR** — Track replication lag until lag approaches zero
6. **CUTOVER** — Switch application connections to target; stop replication

### ZDM Configuration Example

```bash
# ZDM is installed on a separate ZDM host
# Configuration file: zdmconfig.rsp

MIGRATION_METHOD=ONLINE_PHYSICAL   # or ONLINE_LOGICAL, OFFLINE_PHYSICAL
PLATFORM_TYPE=EXACS                # Target: EXACS, DBCS, AUTONOMOUS_DATABASE
TARGETDATABASEADMINUSERNAME=admin
TARGETDATABASEADMINPASSWORD=<password>
SOURCEDATABASEADMINUSERNAME=sys
SOURCEDATABASEADMINPASSWORD=<password>

# GoldenGate settings (for online migration)
GOLDENGATESOURCEHOME=/u01/app/goldengate
GOLDENGATESOURCEHOSTUSERNAME=oracle
GOLDENGATETARGETHOME=/u01/app/goldengate_tgt

# Data Pump settings (for initial bulk load)
DATAPUMPSETTINGS_JOBMODE=SCHEMA
DATAPUMPSETTINGS_DATAPUMPPARAMETERS_PARALLELISM=4
```

```bash
# Validate migration
zdmcli migrate database -sourcedb ORCL \
    -sourcenode source_host \
    -srcauth zdmauth -srcarg1 user:oracle \
    -targetdatabase cdb_name \
    -targethostid abc123 \
    -tdbtokenarr token_string \
    -rsp /etc/zdm/zdmconfig.rsp \
    -eval   # -eval flag for dry-run validation only
```

### ZDM Strengths

- Oracle-to-Oracle migrations with near-zero downtime
- Built-in GoldenGate integration
- Supports physical (RMAN) and logical (Data Pump) migration methods
- OCI Autonomous Database as target
- Oracle-supported and documented

### ZDM Limitations

- Only migrates Oracle-to-Oracle (not cross-RDBMS)
- Supported targets are Oracle-branded cloud and on-premises Exadata platforms; not arbitrary on-premises Oracle installations on commodity hardware
- GoldenGate licensing required for online (near-zero downtime) migration; offline migration does not require GoldenGate
- Complex setup for first-time users

---

## Tool Capability Comparison

| Capability                  | SQL Dev Workbench | AWS SCT   | ora2pg                 | ZDM            | GoldenGate |
| --------------------------- | ----------------- | --------- | ---------------------- | -------------- | ---------- |
| PostgreSQL → Oracle         | Yes               | Yes       | No (wrong direction)   | No             | No         |
| MySQL → Oracle              | Yes               | Yes       | No (wrong direction)   | No             | Yes        |
| SQL Server → Oracle         | Yes               | Yes       | No                     | No             | Yes        |
| Sybase → Oracle             | Yes               | Yes       | No                     | No             | No         |
| DB2 → Oracle                | Yes               | No        | No                     | No             | No         |
| Teradata → Oracle           | Yes               | No        | No                     | No             | No         |
| Oracle → PostgreSQL         | No                | No        | Yes (primary use case) | No             | No         |
| Oracle → Oracle             | No                | No        | No                     | Yes            | Yes        |
| Schema conversion           | Yes               | Yes       | Yes (Oracle→PG only)   | No             | No         |
| Data migration              | Yes (slow)        | No        | Yes (Oracle→PG only)   | Yes            | Yes        |
| Assessment report           | Basic             | Detailed  | Detailed (Oracle→PG)   | Validation     | No         |
| Near-zero downtime          | No                | No        | No                     | Yes            | Yes        |
| Cost                        | Free              | Free      | Free                   | Included w/OCI | Licensed   |
| GUI                         | Yes               | Yes       | No (CLI)               | CLI            | Yes        |
| Stored procedure conversion | Good              | Excellent | N/A for Oracle target  | N/A            | N/A        |

---

## Choosing the Right Tool Combination

### For SQL Server → Oracle

1. **AWS SCT** for schema conversion (tables, indexes, procedures)
2. **SQL\*Loader** or **Oracle Data Pump** for bulk data migration
3. **Oracle GoldenGate** if near-zero downtime is required

### For PostgreSQL → Oracle

1. **SQL Developer Migration Workbench** for schema conversion (tables, indexes, views, procedures)
2. **SQL\*Loader** with CSV export (`\COPY` to CSV) for bulk data loading
3. **AWS SCT** as an alternative for schema conversion with a more detailed assessment report

### For MySQL → Oracle

1. **SQL Developer Migration Workbench** for schema conversion
2. **SQL\*Loader** with CSV export for data migration

### For Oracle → Oracle (Cloud Migration)

1. **Oracle ZDM** for the full migration lifecycle
2. **Data Pump** for offline schema/data transfer
3. **GoldenGate** for online continuous replication

### For MongoDB → Oracle

No dedicated tool; use a combination of:

1. **mongoexport** for data extraction
2. Custom Python ETL scripts for transformation
3. **SQL\*Loader** for loading into Oracle
4. **Oracle JSON Duality Views** (introduced in 23ai, available in 26ai) for document-style access layer

---

## Best Practices for Tool Usage

1. **Always run the assessment first.** Every tool above has an assessment or report mode. Run it before doing any actual migration. The assessment reveals unknown complexity and effort estimates.

2. **Migrate in phases.** Use the tool to migrate a subset of tables first, validate thoroughly, then proceed with the next batch. Never attempt a single-shot full migration of a large schema without phased validation.

3. **Keep generated DDL in version control.** All schema conversion tools generate SQL files. Commit these to Git before applying them to the target database. This creates an audit trail and enables rollback.

4. **Test stored procedure conversion manually.** No tool achieves 100% procedure conversion automatically. Plan for manual review of every converted procedure before deploying to production.

5. **Use PARALLEL and DIRECT PATH options for data loads.** When loading large datasets with SQL\*Loader, always use `DIRECT=TRUE` and `PARALLEL=TRUE` for maximum throughput.

6. **Validate after every load.** Run row count and hash-based validation queries after each table migration. See `migration-data-validation.md` for full validation patterns.

---

## Oracle Version Notes (19c vs 26ai)

- Baseline guidance in this file is valid for Oracle Database 19c unless a newer minimum version is explicitly called out.
- Features marked as 21c, 23c, or 23ai should be treated as Oracle Database 26ai-capable features; keep 19c-compatible alternatives for mixed-version estates.
- For dual-support environments, test syntax and package behavior in both 19c and 26ai because defaults and deprecations can differ by release update.

## Sources

- [Oracle SQL Developer Migration Workbench documentation](https://docs.oracle.com/en/database/oracle/sql-developer/23.1/rptug/migration-workbench.html)
- [Oracle Zero Downtime Migration (ZDM) documentation](https://docs.oracle.com/en/database/oracle/zero-downtime-migration/index.html)
- [AWS Schema Conversion Tool User Guide](https://docs.aws.amazon.com/SchemaConversionTool/latest/userguide/CHAP_Welcome.html)
- [Oracle Database 19c Utilities — SQL\*Loader](https://docs.oracle.com/en/database/oracle/oracle-database/19/sutil/oracle-sql-loader.html)
- [Oracle Database 19c Utilities — Data Pump Export/Import](https://docs.oracle.com/en/database/oracle/oracle-database/19/sutil/datapump-overview.html)
