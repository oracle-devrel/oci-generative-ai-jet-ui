# Part 1: Oracle AI Database Setup & Connection [Database Core]

## What You Are Working With

Oracle AI Database 23ai (and 26ai) is a **converged database** built for AI developers. It is not a separate AI product — it is the core Oracle Database engine with native support for:

- **`VECTOR` column type** — stores embeddings as first-class SQL values
- **HNSW indexes** — approximate nearest-neighbour search directly in SQL
- **`VECTOR_DISTANCE()` function** — cosine, dot product, and Euclidean distance in SQL queries
- **Oracle Text indexes** — full-text keyword search with `CONTAINS()`
- **SQL Property Graphs** — graph traversal with `GRAPH_TABLE()`

This means your entire retrieval pipeline — keyword, vector, hybrid, and graph — all live in a single, queryable, ACID-compliant database. Not a collection of services bolted together.

## Your Environment

In this Codespace, Oracle AI Database is already running as a Docker service (`gvenzl/oracle-free:23-full`). The service starts automatically and passes a healthcheck before your development container boots.

| Setting           | Value            |
| ----------------- | ---------------- |
| Host              | `localhost`      |
| Port              | `1521`           |
| Service name      | `FREEPDB1`       |
| SYS password      | `OraclePwd_2025` |
| App user          | `VECTOR`         |
| App user password | `VectorPwd_2025` |

You will connect as the `VECTOR` user for all workshop tasks. This is a dedicated schema for storing embeddings and research data — it follows the principle of least privilege rather than connecting as SYS.

## The `connect_to_oracle` Helper (Pre-built)

This section is pre-built in the notebook — just run the cells. The code below is provided for reference.

**Why retry logic?** Docker healthchecks verify the container is running, but Oracle's listener can take a few extra seconds to become fully ready after the healthcheck passes. A retry loop makes the connection resilient to this transient window.

**What `oracledb.connect()` needs:**

```python
oracledb.connect(
    user="VECTOR",
    password="VectorPwd_2025",
    dsn="localhost:1521/FREEPDB1"
)
```

The `dsn` format is `host:port/service_name`.

**Implementation:**

```python
import oracledb
import time

def connect_to_oracle(max_retries=3, retry_delay=5):
    user = "VECTOR"
    password = "VectorPwd_2025"
    dsn = "localhost:1521/FREEPDB1"

    for attempt in range(1, max_retries + 1):
        try:
            print(f"Connection attempt {attempt}/{max_retries}...")
            conn = oracledb.connect(user=user, password=password, dsn=dsn)
            print("Connected successfully!")
            with conn.cursor() as cur:
                cur.execute("SELECT banner FROM v$version WHERE banner LIKE 'Oracle%'")
                print(cur.fetchone()[0])
            return conn
        except oracledb.OperationalError as e:
            print(f"Attempt {attempt} failed: {e}")
            if attempt < max_retries:
                print(f"Retrying in {retry_delay}s...")
                time.sleep(retry_delay)
            else:
                raise
```

**Key concept:** The `SELECT banner FROM v$version` query serves as a health check — if this succeeds, the database is fully operational and ready for subsequent operations. Printing the banner also confirms which Oracle version you are connected to.

## Property Graph Privileges

`CREATE PROPERTY GRAPH` privileges are needed for Part 4 (graph retrieval). These are granted automatically during Codespace setup — no action needed in the notebook.

## Troubleshooting

**"ORA-12541: TNS:no listener"** — The listener is still starting. Wait 30 seconds and retry.

**"DPY-4011" or "Connection reset by peer"** — Database is still starting up. Wait 2-3 minutes.

**"ORA-01017: invalid username/password"** — Check you are using `VECTOR` / `VectorPwd_2025`.

**"Could not reach Oracle after all retries"** — Rebuild the Codespace from the VS Code command palette: `Codespaces: Rebuild Container`.
