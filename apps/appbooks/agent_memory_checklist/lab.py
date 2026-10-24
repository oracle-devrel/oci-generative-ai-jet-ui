"""Database layer: configuration, the one-time admin setup, building the lab, and small query helpers.

One rule shapes this file: only the owner session runs the ONNX models. Models load into the memory of the
session that calls them, and a small database (Oracle AI Database Free caps PGA at 2 GB) cannot afford a copy
per session. Every other session (end users, a second agent) gets vectors bound in, never model calls.
"""
from __future__ import annotations

import array
import json
import os
import subprocess
import threading
import urllib.request
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import oracledb
from corpus import ENTITIES, LINKS, MEMORIES

HERE = Path(__file__).resolve().parent
DSN = os.getenv("ORACLE_DSN", "localhost:1521/FREEPDB1")
USER = os.getenv("APPBOOK_DB_USER", "MEMORY_APPBOOK")
PASSWORD = os.getenv("APPBOOK_DB_PASSWORD", "MemoryAppbook_12345")
SCHEMA = USER.lower()
END_USERS = {
    "user_ada": os.getenv("END_USER_ADA_PASSWORD", "Ada_12345"),
    "user_bob": os.getenv("END_USER_BOB_PASSWORD", "Bob_12345"),
    "user_cy": os.getenv("END_USER_CY_PASSWORD", "Cy_123456"),
}
MODEL, RERANKER = "ALL_MINILM_L12_V2", "RERANK_MINILM"
MODEL_DIR = Path(os.path.expanduser(os.getenv("ONNX_MODEL_DIR", "~/oracle-models")))
EMBED_ONNX = Path(os.getenv("EMBED_ONNX_PATH", MODEL_DIR / "all_MiniLM_L12_v2.onnx"))
RERANK_ONNX = Path(
    os.getenv("RERANK_ONNX_PATH", MODEL_DIR / "ms_marco_minilm_l6_pair_reranker.onnx")
)
EMBED_ONNX_URL = "https://objectstorage.us-ashburn-1.oraclecloud.com/n/adwc4pm/b/OML-Resources/o/all_MiniLM_L12_v2.onnx"
AUDIT_POLICY = "appbook_memory_reads"

oracledb.defaults.fetch_lobs = False
oracledb.defaults.program = os.getenv(
    "ORACLE_PROGRAM", "devrel-developerhub-agent-memory-appbook-claude"
)

LOCK = threading.RLock()  # one owner session, used by one request at a time
STATE = {
    "scn_before": None,
    "results": {},
    "index_kind": None,
    "build": {"running": False, "log": [], "error": None},
}
_owner = None


# ----------------------------------------------------------------------------------------------- sessions
def owner():
    """The table owner's session: the only one that runs VECTOR_EMBEDDING and PREDICTION."""
    global _owner
    if _owner is None or not _owner.is_healthy():
        _owner = oracledb.connect(user=USER, password=PASSWORD, dsn=DSN)
    return _owner


def session(end_user=None):
    """A separate session: the owner account again, or a Deep Data Security end user. Never runs models."""
    if end_user:
        return oracledb.connect(user=f'"{end_user}"', password=END_USERS[end_user], dsn=DSN)
    return oracledb.connect(user=USER, password=PASSWORD, dsn=DSN)


def q(sql, binds=None, conn=None):
    """Run a query and return a list of dicts with lowercase keys."""
    with (conn or owner()).cursor() as cur:
        cur.execute(sql, binds or {})
        cols = [d[0].lower() for d in cur.description]
        return [dict(zip(cols, row, strict=False)) for row in cur.fetchall()]


def x(sql, binds=None, conn=None, ignore=False):
    try:
        with (conn or owner()).cursor() as cur:
            cur.execute(sql, binds or {})
    except oracledb.DatabaseError:
        if not ignore:
            raise


def embed(text):
    """Embed text in the owner session and return the vector, ready to bind into any other session."""
    return q(f"SELECT VECTOR_EMBEDDING({MODEL} USING :t AS data) AS v FROM dual", {"t": text})[0][
        "v"
    ]


def first_line(error):
    return str(error).splitlines()[0]


def plain(value):
    """Make database values JSON-friendly for the browser."""
    if isinstance(value, datetime):
        return value.isoformat(sep=" ", timespec="seconds")
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, bytes | bytearray):
        return f"<{len(value):,} bytes>"
    if isinstance(value, array.array):
        return [round(v, 4) for v in value[:8]] + (
            [f"… {len(value)} dims"] if len(value) > 8 else []
        )
    if isinstance(value, dict):
        return {k: plain(v) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [plain(v) for v in value]
    return value


# ----------------------------------------------------------------------------------------------- admin setup
SETUP_SQL = (
    [
        f'CREATE USER IF NOT EXISTS {USER} IDENTIFIED BY "{PASSWORD}" DEFAULT TABLESPACE users QUOTA UNLIMITED ON users',
        f"GRANT DB_DEVELOPER_ROLE, CTXAPP, DBFS_ROLE TO {USER}",
        f"GRANT CREATE MINING MODEL, CREATE PROPERTY GRAPH TO {USER}",
        f"GRANT EXECUTE ON CTXSYS.CTX_DDL TO {USER}",
        f"GRANT EXECUTE ON DBMS_FLASHBACK TO {USER}",
        f"GRANT AUDIT_ADMIN, AUDIT_VIEWER TO {USER}",
        f"GRANT CREATE DATA GRANT, SET USE DATA GRANTS ONLY TO {USER}",
        f"GRANT ADMINISTER ANY DATA GRANT ON SCHEMA {USER} TO {USER}",
        "CREATE ROLE memory_lab_connect",
        "GRANT CREATE SESSION TO memory_lab_connect",
        "CREATE OR REPLACE DATA ROLE memory_reader_role",
        "GRANT memory_lab_connect TO memory_reader_role",
    ]
    + [f'CREATE END USER "{u}" IDENTIFIED BY "{p}"' for u, p in END_USERS.items()]
    + [f'GRANT DATA ROLE memory_reader_role TO "{u}"' for u in END_USERS]
)
ALREADY_EXISTS = ("ORA-01920", "ORA-01921", "ORA-52514")


def admin_route():
    return (
        "password"
        if os.getenv("ORACLE_ADMIN_PASSWORD")
        else "container"
        if os.getenv("ORACLE_CONTAINER")
        else None
    )


def run_setup():
    """Create the schema, its privileges and the end users, as SYSDBA (password) or through `docker exec`."""
    if admin_route() == "password":
        errors = []
        with oracledb.connect(
            user="SYS",
            password=os.environ["ORACLE_ADMIN_PASSWORD"],
            dsn=DSN,
            mode=oracledb.AUTH_MODE_SYSDBA,
        ) as admin:
            for stmt in SETUP_SQL:
                try:
                    admin.cursor().execute(stmt)
                except oracledb.DatabaseError as e:
                    errors.append(first_line(e))
    elif admin_route() == "container":
        script = (
            f"ALTER SESSION SET CONTAINER = {DSN.rsplit('/', 1)[-1]};\n"
            + "".join(f"{s};\n" for s in SETUP_SQL)
            + "EXIT\n"
        )
        out = subprocess.run(
            [
                "docker",
                "exec",
                "-i",
                os.environ["ORACLE_CONTAINER"],
                "sqlplus",
                "-s",
                "/",
                "as",
                "sysdba",
            ],
            input=script,
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        errors = [line for line in out.splitlines() if line.startswith("ORA-")]
    else:
        raise RuntimeError(
            "Set ORACLE_ADMIN_PASSWORD or ORACLE_CONTAINER so the appbook can create its schema."
        )
    problems = [e for e in errors if not e.startswith(ALREADY_EXISTS)]
    if problems:
        raise RuntimeError("Setup problems: " + "; ".join(problems))


# ----------------------------------------------------------------------------------------------- the lab
INSERT_MEMORY = f"""
    INSERT INTO memories (memory_id, user_id, agent_id, memory_type, importance, created_at, valid_from,
                          source_thread_id, content, metadata, embedding)
    VALUES (:memory_id, :user_id, :agent_id, :memory_type, :importance, :created_at, :created_at,
            :thread, :content, :metadata, VECTOR_EMBEDDING({MODEL} USING :content AS data))"""


def memory_binds(
    memory_id,
    user_id,
    agent_id,
    memory_type,
    importance,
    created_at,
    project,
    channel,
    content,
    thread=None,
):
    return {
        "memory_id": memory_id,
        "user_id": user_id,
        "agent_id": agent_id,
        "memory_type": memory_type,
        "importance": importance,
        "created_at": created_at,
        "thread": thread or f"thr_{memory_id[4:]}",
        "content": content,
        "metadata": {"project": project, "channel": channel, "tags": [memory_type, project]},
    }


def corpus_binds():
    for m_id, user, agent, mtype, imp, day, project, channel, content, _ in MEMORIES:
        created = datetime.fromisoformat(day).replace(hour=9, tzinfo=UTC)
        yield memory_binds(m_id, user, agent, mtype, imp, created, project, channel, content)


CLEANUP = [
    f"NOAUDIT POLICY {AUDIT_POLICY}",
    f"DROP AUDIT POLICY {AUDIT_POLICY}",
    "DROP DATA GRANT IF EXISTS own_memories",
    "SET USE DATA GRANTS ONLY ON memories DISABLED",
    "DROP PROPERTY GRAPH memory_graph",
    "DROP VIEW memory_dv",
    "DROP TABLE memory_artifacts PURGE",
    "DROP TABLE memory_relations PURGE",
    "DROP TABLE memory_mentions PURGE",
    "DROP TABLE memory_entities PURGE",
    "DROP INDEX memories_hybrid_idx FORCE",
    "DROP TABLE memories PURGE",
]

DDL_MEMORIES = """
CREATE TABLE memories (
    memory_id        VARCHAR2(40) PRIMARY KEY,
    user_id          VARCHAR2(40) NOT NULL,
    agent_id         VARCHAR2(40) NOT NULL,
    memory_type      VARCHAR2(12) NOT NULL
                     CONSTRAINT memories_type_ck CHECK (memory_type IN ('semantic','episodic','procedural')),
    importance       NUMBER(3,2),
    created_at       TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    valid_from       TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    valid_to         TIMESTAMP WITH TIME ZONE,
    source_thread_id VARCHAR2(40),
    content          CLOB NOT NULL,
    metadata         JSON,
    embedding        VECTOR(384, FLOAT32))"""

DDL_GRAPH = [
    "CREATE TABLE memory_entities (entity_id VARCHAR2(40) PRIMARY KEY, name VARCHAR2(200) NOT NULL, kind VARCHAR2(40) NOT NULL)",
    """CREATE TABLE memory_mentions (
         memory_id VARCHAR2(40) NOT NULL REFERENCES memories (memory_id),
         entity_id VARCHAR2(40) NOT NULL REFERENCES memory_entities (entity_id),
         PRIMARY KEY (memory_id, entity_id))""",
    """CREATE TABLE memory_relations (
         src_id    VARCHAR2(40) NOT NULL REFERENCES memories (memory_id),
         dst_id    VARCHAR2(40) NOT NULL REFERENCES memories (memory_id),
         link_type VARCHAR2(20) NOT NULL,
         PRIMARY KEY (src_id, dst_id, link_type))""",
]

DDL_PROPERTY_GRAPH = """
CREATE PROPERTY GRAPH memory_graph
  VERTEX TABLES (
    memories        KEY (memory_id) LABEL memory PROPERTIES (memory_id, user_id, memory_type),
    memory_entities KEY (entity_id) LABEL entity PROPERTIES (entity_id, name, kind))
  EDGE TABLES (
    memory_mentions KEY (memory_id, entity_id)
      SOURCE KEY (memory_id) REFERENCES memories (memory_id)
      DESTINATION KEY (entity_id) REFERENCES memory_entities (entity_id)
      LABEL mentions NO PROPERTIES,
    memory_relations KEY (src_id, dst_id, link_type)
      SOURCE KEY (src_id) REFERENCES memories (memory_id)
      DESTINATION KEY (dst_id) REFERENCES memories (memory_id)
      LABEL linked PROPERTIES (link_type))"""

DDL_DUALITY = """
CREATE OR REPLACE JSON RELATIONAL DUALITY VIEW memory_dv AS
  SELECT JSON {'_id' : m.memory_id, 'userId' : m.user_id, 'agentId' : m.agent_id, 'type' : m.memory_type,
               'importance' : m.importance, 'validTo' : m.valid_to, 'content' : m.content, 'metadata' : m.metadata}
  FROM memories m WITH INSERT UPDATE DELETE"""

DDL_ARTIFACTS = """
CREATE TABLE memory_artifacts (
    artifact_id VARCHAR2(40) PRIMARY KEY,
    memory_id   VARCHAR2(40) NOT NULL REFERENCES memories (memory_id) ON DELETE CASCADE,
    mime_type   VARCHAR2(80) NOT NULL,
    file_name   VARCHAR2(200),
    text_body   CLOB,
    binary_body BLOB)"""

DATA_GRANT = """
CREATE OR REPLACE DATA GRANT own_memories AS SELECT ON memories
  WHERE user_id = LOWER(ORA_END_USER_CONTEXT.username) OR user_id = 'global'
  TO memory_reader_role"""

REPORT_MD = """# Weekly memory report

- 68 memories across Cairn, Beacon and Comet
- 3 corrections this week, each written as a supersedes link
- The architecture screenshot is attached to the same memory
"""


def load_onnx(name, path, metadata, log):
    if q("SELECT 1 FROM user_mining_models WHERE model_name = :m", {"m": name}):
        return True
    if not path.exists():
        if name != MODEL:
            log.append(
                f"{name}: {path.name} not found; §7 will skip until the notebook's §7 exports it"
            )
            return False
        log.append(f"downloading {path.name} (about 130 MB, once)")
        path.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(EMBED_ONNX_URL, path)
    lob = owner().createlob(oracledb.DB_TYPE_BLOB)
    lob.write(path.read_bytes())
    x(
        "BEGIN DBMS_VECTOR.LOAD_ONNX_MODEL(:n, :d, JSON(:m)); END;",
        {"n": name, "d": lob, "m": json.dumps(metadata)},
    )
    log.append(f"loaded {name} into the database from {path.name}")
    return True


def mount_scratchpad():
    """A DBFS file system in this schema, mounted at /scratch, with a directory for the agent."""
    if not q("SELECT 1 FROM TABLE(DBMS_DBFS_CONTENT.listMounts) WHERE store_mount = 'scratch'"):
        x(
            """BEGIN
               DBMS_DBFS_SFS.createFilesystem(store_name => 'SCRATCH_FS', tbl_name => 'SCRATCH_FS_T', do_partition => FALSE);
               DBMS_DBFS_CONTENT.registerStore('SCRATCH_FS', 'posix', 'DBMS_DBFS_SFS');
               DBMS_DBFS_CONTENT.mountStore(store_name => 'SCRATCH_FS', store_mount => 'scratch');
             END;"""
        )
    if not q("SELECT 1 FROM dbfs_content WHERE pathname = '/scratch/agent'"):
        x(
            """DECLARE props DBMS_DBFS_CONTENT_PROPERTIES_T := DBMS_DBFS_CONTENT_PROPERTIES_T();
             BEGIN DBMS_DBFS_CONTENT.createDirectory('/scratch/agent', props); END;"""
        )
    for row in q(
        "SELECT pathname FROM dbfs_content WHERE pathname LIKE '/scratch/agent/%' AND pathtype = 'file'"
    ):
        x("BEGIN DBMS_DBFS_CONTENT.deleteFile(:p); END;", {"p": row["pathname"]})
    owner().commit()


def build(log):
    """(Re)build every lab object from the corpus. Safe to run again: it drops what it created first."""
    with LOCK:
        for stmt in CLEANUP:
            x(stmt, ignore=True)
        x(DDL_MEMORIES)
        with owner().cursor() as cur:
            cur.setinputsizes(content=oracledb.DB_TYPE_CLOB, metadata=oracledb.DB_TYPE_JSON)
            cur.executemany(
                INSERT_MEMORY.replace(f"VECTOR_EMBEDDING({MODEL} USING :content AS data)", "NULL"),
                list(corpus_binds()),
            )
        owner().commit()
        log.append(f"memories: {len(MEMORIES)} rows (relational, CLOB, JSON, VECTOR columns)")

        load_onnx(
            MODEL,
            EMBED_ONNX,
            {"function": "embedding", "embeddingOutput": "embedding", "input": {"input": ["DATA"]}},
            log,
        )
        STATE["reranker"] = load_onnx(
            RERANKER,
            RERANK_ONNX,
            {
                "function": "regression",
                "regressionOutput": "score",
                "input": {"pre_text": ["DATA"]},
            },
            log,
        )
        x(f"UPDATE memories SET embedding = VECTOR_EMBEDDING({MODEL} USING content AS data)")
        owner().commit()
        log.append("embedded every memory in the database with VECTOR_EMBEDDING")

        try:
            x(
                """CREATE VECTOR INDEX memories_hnsw_idx ON memories (embedding)
                 ORGANIZATION INMEMORY NEIGHBOR GRAPH DISTANCE COSINE WITH TARGET ACCURACY 95"""
            )
            STATE["index_kind"] = "HNSW"
        except oracledb.DatabaseError:
            x(
                """CREATE VECTOR INDEX memories_hnsw_idx ON memories (embedding)
                 ORGANIZATION NEIGHBOR PARTITIONS DISTANCE COSINE WITH TARGET ACCURACY 95"""
            )
            STATE["index_kind"] = "IVF"
        # SYNC (MANUAL): no background job loading the model elsewhere; the owner session syncs before keyword recall.
        x(
            f"CREATE HYBRID VECTOR INDEX memories_hybrid_idx ON memories (content) "
            f"PARAMETERS ('MODEL {MODEL} VECTOR_IDXTYPE {STATE['index_kind']} SYNC (MANUAL)')"
        )
        log.append(
            f"{STATE['index_kind']} vector index and a hybrid vector index (Oracle Text + vectors)"
        )

        for ddl in DDL_GRAPH:
            x(ddl)
        with owner().cursor() as cur:
            cur.executemany("INSERT INTO memory_entities VALUES (:1, :2, :3)", ENTITIES)
            cur.executemany(
                "INSERT INTO memory_mentions VALUES (:1, :2)",
                [(m[0], e) for m in MEMORIES for e in m[9]],
            )
            cur.executemany("INSERT INTO memory_relations VALUES (:1, :2, :3)", LINKS)
        x(DDL_PROPERTY_GRAPH)
        x(DDL_DUALITY)
        log.append(
            "entities, mentions and links, the memory_graph property graph and the memory_dv duality view"
        )

        x(DDL_ARTIFACTS)
        png = (HERE / "static" / "img" / "checklist_02_polyglot_vs_converged.png").read_bytes()
        with owner().cursor() as cur:
            cur.setinputsizes(None, None, None, None, oracledb.DB_TYPE_CLOB, oracledb.DB_TYPE_BLOB)
            cur.executemany(
                "INSERT INTO memory_artifacts VALUES (:1, :2, :3, :4, :5, :6)",
                [
                    ("art_md_051", "mem_051", "text/markdown", "weekly_report.md", REPORT_MD, None),
                    ("art_png_051", "mem_051", "image/png", "architecture.png", None, png),
                ],
            )
        owner().commit()
        log.append("memory_artifacts: a markdown report and a PNG attached to mem_051")

        x(DATA_GRANT)
        x("SET USE DATA GRANTS ONLY ON memories ENABLED")
        x(f"CREATE AUDIT POLICY {AUDIT_POLICY} ACTIONS SELECT ON {SCHEMA}.memories")
        x(f"AUDIT POLICY {AUDIT_POLICY}")
        log.append("data grant own_memories (USE DATA GRANTS ONLY) and the audit policy on reads")

        mount_scratchpad()
        log.append("DBFS scratchpad mounted at /scratch")
        STATE.update(scn_before=None, results={})


def status():
    """What exists, so the UI can say what is missing."""
    try:
        with LOCK:
            tables = {r["table_name"].lower() for r in q("SELECT table_name FROM user_tables")}
            models = [r["model_name"] for r in q("SELECT model_name FROM user_mining_models")]
            counts = (
                q(
                    """SELECT COUNT(*) AS n, COUNT(CASE WHEN embedding IS NOT NULL THEN 1 END) AS embedded
                          FROM memories"""
                )[0]
                if "memories" in tables
                else {}
            )
            if "memories" in tables and not STATE["index_kind"]:
                try:
                    kind = q(
                        "SELECT index_subtype FROM user_indexes WHERE index_name = 'MEMORIES_HNSW_IDX'"
                    )
                    STATE["index_kind"] = (
                        "IVF"
                        if kind and "PARTITION" in (kind[0]["index_subtype"] or "")
                        else "HNSW"
                    )
                except oracledb.DatabaseError:
                    STATE["index_kind"] = "HNSW"
            STATE["reranker"] = RERANKER in models
        built = {"memories", "memory_artifacts", "memory_entities"} <= tables and MODEL in models
        return {
            "connected": True,
            "built": built,
            "models": models,
            "counts": plain(counts),
            "index_kind": STATE["index_kind"],
        }
    except oracledb.DatabaseError as e:
        return {
            "connected": False,
            "built": False,
            "error": first_line(e),
            "admin_route": admin_route(),
        }
