# Part 3: Database Table Setup & Data Ingestion [Schema Design]

## What You Are Building

With embeddings ready in the DataFrame, you now create the Oracle schema to hold them. This part covers the full data path from Python to Oracle:

1. Create the `RESEARCH_PAPERS` table with a `VECTOR` column
2. Create vector (HNSW) and full-text (Oracle Text) indexes
3. Ingest the 200 papers into Oracle
4. Create relational tables for graph retrieval (authors, similarities)
5. Build and register a SQL Property Graph

## The Research Papers Table

The main table has:

- `arxiv_id` — primary key
- `title`, `abstract` — metadata for display
- `text` — full document text (CLOB)
- `embedding` — vector column with dimension matching your model (768 for nomic-embed)

**Why a dedicated `VECTOR` column?** Oracle treats vectors as first-class SQL values. This means you can query them with `VECTOR_DISTANCE()`, index them with HNSW, and join them with regular SQL — all in one statement.

## The Indexes

**HNSW Vector Index** — Enables fast approximate nearest-neighbour search:

```sql
CREATE VECTOR INDEX RP_VEC_HNSW
ON research_papers(embedding)
ORGANIZATION INMEMORY NEIGHBOR GRAPH
DISTANCE COSINE
WITH TARGET ACCURACY 90
PARAMETERS (TYPE HNSW, NEIGHBORS 40, EFCONSTRUCTION 500)
```

**Why HNSW?** HNSW (Hierarchical Navigable Small World) is a graph-based approximate nearest-neighbour algorithm. Without it, Oracle scans every vector on every query (exact but slow). With it, queries are approximate but fast — typically milliseconds at millions of vectors. The `TARGET ACCURACY 90` means Oracle guarantees 90% recall against exact search.

**Oracle Text Index** — Enables full-text keyword search:

```sql
CREATE INDEX rp_text_idx
ON research_papers(text)
INDEXTYPE IS CTXSYS.CONTEXT
PARAMETERS ('SYNC (ON COMMIT)')
```

**Why `SYNC (ON COMMIT)`?** This ensures the text index stays synchronised with the data. Without it, you would need to manually sync the index after each insert — easy to forget, hard to debug.

---

## TODO 1: Write the DDL to Create the `research_papers` Table

Write a DDL string assigned to the `ddl` variable that:

1. Drops dependent tables safely (paper_similarities, paper_authors, authors, research_papers)
2. Creates the `research_papers` table with the correct VECTOR dimension
3. Separates statements with `/` (the notebook splits and executes each block)

**Why drop in dependency order?** Oracle enforces foreign key constraints. If `paper_authors` references `research_papers`, you cannot drop `research_papers` first. Dropping in reverse dependency order avoids constraint errors.

**Hint:** Use `BEGIN ... EXCEPTION WHEN OTHERS THEN IF SQLCODE != -942 THEN RAISE; END IF; END;` for safe drops. Error code `-942` means "table does not exist" — catching it makes the drop idempotent. Separate each PL/SQL block and the final CREATE statement with `/`.

**Complete solution:**

```python
ddl = f"""
BEGIN
    EXECUTE IMMEDIATE 'DROP TABLE paper_similarities';
EXCEPTION WHEN OTHERS THEN
    IF SQLCODE != -942 THEN RAISE; END IF;
END;
/
BEGIN
    EXECUTE IMMEDIATE 'DROP TABLE paper_authors';
EXCEPTION WHEN OTHERS THEN
    IF SQLCODE != -942 THEN RAISE; END IF;
END;
/
BEGIN
    EXECUTE IMMEDIATE 'DROP TABLE authors';
EXCEPTION WHEN OTHERS THEN
    IF SQLCODE != -942 THEN RAISE; END IF;
END;
/
BEGIN
    EXECUTE IMMEDIATE 'DROP TABLE research_papers CASCADE CONSTRAINTS PURGE';
EXCEPTION WHEN OTHERS THEN
    IF SQLCODE != -942 THEN RAISE; END IF;
END;
/
CREATE TABLE research_papers (
    arxiv_id    VARCHAR2(255)  PRIMARY KEY,
    title       VARCHAR2(4000),
    abstract    VARCHAR2(4000),
    text        CLOB,
    embedding   VECTOR({dim}, FLOAT32)
)
TABLESPACE USERS
"""
```

The next cell splits on `/` and executes each block, then commits:

```python
with conn.cursor() as cur:
    for stmt in ddl.split("/"):
        if stmt.strip():
            cur.execute(stmt)
conn.commit()
```

**Key concept:** The `VECTOR({dim}, FLOAT32)` column type tells Oracle the exact dimension and precision of your vectors. This enables Oracle to validate vectors on insert and optimise storage. If you insert a vector with the wrong dimension, Oracle will reject it — catching bugs early.

## Data Ingestion

Embeddings are converted to `array.array('f', ...)` for proper Oracle VECTOR binding, then inserted row by row with progress tracking.

**Why `array.array('f', ...)`?** The `oracledb` driver uses Python's `array` module to pass typed arrays to Oracle. The `'f'` format code specifies 32-bit floats, matching the `FLOAT32` declaration in the table DDL.

## Graph Tables & Property Graph

For graph-based retrieval in Part 4, we create:

- `AUTHORS` — normalised author names
- `PAPER_AUTHORS` — author-paper edges (WROTE relationship)
- `PAPER_SIMILARITIES` — top-10 similar papers per paper (SIMILAR_TO relationship)

These are registered as a SQL Property Graph (`RESEARCH_GRAPH`) for use with `GRAPH_TABLE()` queries.

## Troubleshooting

**"ORA-51956: vector memory size"** — The vector memory pool is too small for HNSW. The setup scripts should have configured this automatically. If not, run this in the terminal then restart Oracle:

```bash
python3 -c "
import oracledb
conn = oracledb.connect(user='sys', password='OraclePwd_2025', dsn='localhost:1521/FREE', mode=oracledb.SYSDBA)
conn.cursor().execute('ALTER SYSTEM SET vector_memory_size = 512M SCOPE=SPFILE')
conn.commit(); conn.close()
"
docker restart oracle-free
```

**"ORA-00942: table or view does not exist"** — The drop statements handle this with the `-942` exception guard. If you see this error during CREATE, check for a typo in the table name.

**"ORA-00955: name is already used"** — A table already exists from a prior run. The safe drop logic should prevent this — re-run the cell from the top.
