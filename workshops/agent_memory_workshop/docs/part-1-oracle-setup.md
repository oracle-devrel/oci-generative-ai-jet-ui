# Part 1: Oracle AI Database Setup [Memory Core]

## What You Are Working With

Oracle AI Database is not a separate AI product — it is the core Oracle Database engine with native support for:

- **`VECTOR` column type** — stores embeddings as first-class SQL values
- **HNSW indexes** — approximate nearest-neighbour search directly in SQL
- **`VECTOR_DISTANCE()` function** — cosine, dot product, and Euclidean distance in SQL queries

This means your agent memory lives in a single, queryable, ACID-compliant database — not a separate vector store bolted on the side.

## Your Environment

In this Codespace, Oracle AI Database is already running as a Docker service (`gvenzl/oracle-free`). The service starts automatically and passes a healthcheck before your development container boots.

| Setting           | Value                          |
| ----------------- | ------------------------------ |
| Host              | `oracle` (Docker service name) |
| Port              | `1521`                         |
| Service name      | `FREEPDB1`                     |
| SYS password      | `OraclePwd_2025`               |
| App user          | `VECTOR`                       |
| App user password | `VectorPwd_2025`               |

You will connect as the `VECTOR` user for all workshop tasks. This is a dedicated schema for storing embeddings and agent memory — it follows the principle of least privilege rather than connecting as SYS.

## Reference: `connect_to_oracle`

This function is pre-built in the student notebook — just run the cell. The explanation below is for reference.

**Why retry logic?** Docker healthchecks verify the container is running, but Oracle's listener can take a few extra seconds to become fully ready after the healthcheck passes. A retry loop makes the connection resilient to this transient window.

**What `oracledb.connect()` needs:**

```python
oracledb.connect(
    user="VECTOR",
    password="VectorPwd_2025",
    dsn="localhost:1521/FREEPDB1"
)
```

The `dsn` format is `host:port/service_name`. In Codespaces, `oracle` resolves to the Oracle Docker service.

**Complete solution:**

```python
import oracledb
import time

def connect_to_oracle(max_retries=3, retry_delay=5, user="sys", password="OraclePwd_2025",
                      dsn="localhost:1521/FREEPDB1", program="workshop"):
    for attempt in range(1, max_retries + 1):
        try:
            print(f"Connection attempt {attempt}/{max_retries}...")
            conn = oracledb.connect(
                user=user,
                password=password,
                dsn=dsn,
                mode=oracledb.SYSDBA if user == "sys" else oracledb.DEFAULT_AUTH,
            )
            conn.clientinfo = program
            print(f"Connected successfully as {user}")
            return conn
        except Exception as e:
            print(f"Attempt {attempt} failed: {e}")
            if attempt < max_retries:
                print(f"Retrying in {retry_delay}s...")
                time.sleep(retry_delay)
            else:
                raise
```

**What `conn.clientinfo = program` does:** Sets a label visible in Oracle's `V$SESSION` view. Useful for debugging — you can query which sessions belong to which application.

## Connecting as the VECTOR User

After defining the function, the notebook connects as `VECTOR`:

```python
vector_conn = connect_to_oracle(
    user="VECTOR",
    password="VectorPwd_2025",
    dsn="localhost:1521/FREEPDB1",
    program="devrel.hub.memory_engineering",
)
```

All subsequent database operations in this workshop use `vector_conn`. You should see output like:

```
Connection attempt 1/3...
Connected successfully as VECTOR
Using user: VECTOR
```

## Troubleshooting

**"ORA-12541: TNS:no listener"** — The listener is still starting. Wait 30 seconds and retry.

**"ORA-01017: invalid username/password"** — Check you are using `VECTOR` / `VectorPwd_2025` for the VECTOR user cells, not the SYS credentials.

**"Could not reach Oracle after all retries"** — Rebuild the Codespace from the VS Code command palette: `Codespaces: Rebuild Container`.
