"""All authorization happens in Oracle. No application-side row/memory filtering.

Three identities, three routes:
- desk end users (hf_credit / hf_markets): entitled reads on the primary under Deep Data Security. DDS end-user
  sessions cannot open on True Cache in this release (logon fails with ORA-16000 on the read-only instance).
- desk memory schemas (HF_*_MEM): writes on the primary; cache-tier reads through True Cache, primary fallback.
- reference reader (HF_REFERENCE): ontology and metric-catalog reads through True Cache, primary fallback. It holds
  no desk data: desk-scoped graph vertices come from views that return nothing for this identity.
"""
import array
import json
import threading
import time
from datetime import date, datetime
from decimal import Decimal

import oracledb

from .config import DSN, EMBED, PERSONAS, RERANK, env
oracledb.defaults.program = "devrel-developerhub-hedge-fund-analyst"

oracledb.defaults.fetch_lobs = False
POOLS = {}
LOCK = threading.Lock()
TRUE_CACHE_DSN = env("HF_TRUE_CACHE_DSN")
REFERENCE = {"user": "HF_REFERENCE", "password": env("HF_REFERENCE_PASSWORD")}


def pool(persona, memory=False, cache=False, reference=False):
    if not reference and persona not in PERSONAS:
        raise ValueError("Unknown persona")
    key = ("reference" if reference else persona, memory, cache)
    with LOCK:
        if key not in POOLS:
            p = PERSONAS.get(persona, {})
            user, password = (
                (REFERENCE["user"], REFERENCE["password"])
                if reference
                else (p["memory_user"], p["password"])
                if memory
                else ('"' + p["user"] + '"', p["password"])
            )
            # Acquisition waits at most 30 s: a pool that is exhausted fails loudly instead of hanging a turn.
            # Desk end-user pools keep one warm session; memory and reference pools open on demand and idle out after 10 min.
            # Each session with an ONNX model loaded holds ~185-500 MB of PGA and Free caps PGA at 2 GB.
            POOLS[key] = oracledb.create_pool(
                user=user,
                password=password,
                dsn=TRUE_CACHE_DSN if cache else DSN,
                min=0 if (memory or reference) else 1,
                max=1 if (memory or reference) else 2,
                increment=1,
                ping_interval=60,
                timeout=300,
                max_lifetime_session=3600,
                getmode=oracledb.POOL_GETMODE_TIMEDWAIT,
                wait_timeout=30000,
            )
    return POOLS[key]


def clean(v):
    if isinstance(v, date | datetime):
        return v.isoformat()
    if isinstance(v, Decimal):
        return float(v)
    if isinstance(v, oracledb.LOB):
        return v.read()
    return v


def vector(values):
    return array.array("f", values)


def cache_status():
    # Health view of the True Cache route: role and service of a reference session on the cache DSN.
    if not TRUE_CACHE_DSN:
        return {"state": "not running", "detail": "HF_TRUE_CACHE_DSN not configured"}
    db = DB("Credit", reference=True)
    try:
        return {"state": "running" if db.r else "not running", "detail": db.cache_note}
    finally:
        db.close()


class DB:
    def __init__(self, persona, request_id=None, memory=False, reference=False):
        started = time.perf_counter()
        self.persona = persona
        self.request_id = request_id or "hf-explorer"
        self.kind = "reference" if reference else "memory" if memory else "end user"
        self.c = pool(persona, memory, reference=reference).acquire()
        self.trace = []
        self.wait_ms = round((time.perf_counter() - started) * 1000, 1)
        self.c.client_identifier = request_id or "hf-explorer"
        self.c.module = "HF_ANALYST"
        self.c.action = self.kind
        # A cold session loads the ONNX models (seconds on Free's 2 CPUs); allow it rather than fail the turn.
        self.c.call_timeout = 60000
        self.r = None
        self.served_by = "primary"
        self.cache_note = (
            "True Cache not configured"
            if not TRUE_CACHE_DSN
            else "desk entitlements are enforced on the primary (DDS end users cannot log in to True Cache)"
            if self.kind == "end user"
            else None
        )
        if TRUE_CACHE_DSN and self.kind != "end user":
            try:
                r = pool(persona, memory, cache=True, reference=reference).acquire()
                r.client_identifier = request_id or "hf-explorer"
                r.module = "HF_ANALYST"
                r.action = self.kind + "-tc"
                r.call_timeout = 15000
                with r.cursor() as cur:
                    role, service = cur.execute(
                        "SELECT SYS_CONTEXT('USERENV','DATABASE_ROLE'),SYS_CONTEXT('USERENV','SERVICE_NAME') FROM dual"
                    ).fetchone()
                # A True Cache session reports PHYSICAL STANDBY (redo-apply machinery); the service name confirms the route.
                if (
                    role in ("TRUE CACHE", "PHYSICAL STANDBY")
                    and service.upper() == TRUE_CACHE_DSN.rsplit("/", 1)[-1].upper()
                ):
                    self.r = r
                    self.served_by = "true cache"
                    self.cache_note = f"verified: role {role}, service {service}"
                else:
                    r.close()
                    self.cache_note = f"cache DSN answered with role {role}; using primary"
            except Exception as e:
                self.cache_note = "True Cache unavailable: " + str(e).split(chr(10))[0][:160]

    def reconnect(self):
        # A call timeout closes the connection; continue the turn on a fresh session with the same request ID.
        try:
            self.c.close()
        except Exception:
            pass
        self.c = pool(
            self.persona, self.kind == "memory", reference=self.kind == "reference"
        ).acquire()
        self.c.client_identifier = self.request_id
        self.c.module = "HF_ANALYST"
        self.c.action = self.kind
        self.c.call_timeout = 60000

    def close(self):
        if self.r:
            self.r.close()
        self.c.close()

    def query(self, sql, binds=None, route=None):
        # Reference reads default to True Cache; memory and end-user reads default to the primary.
        route = route or ("cache" if self.kind == "reference" else "primary")
        conn = self.r if route == "cache" and self.r else self.c
        started = time.perf_counter()
        try:
            with conn.cursor() as cur:
                cur.execute(sql, binds or {})
                names = [d[0].lower() for d in cur.description]
                rows = [
                    {k: clean(v) for k, v in zip(names, r, strict=False)}
                    for r in cur.fetchmany(500)
                ]
        except oracledb.Error:
            if conn is self.c:
                raise
            # True Cache read failed: fall back to the primary, the table of record.
            conn = self.c
            with conn.cursor() as cur:
                cur.execute(sql, binds or {})
                names = [d[0].lower() for d in cur.description]
                rows = [
                    {k: clean(v) for k, v in zip(names, r, strict=False)}
                    for r in cur.fetchmany(500)
                ]
        self.trace.append(
            {
                "sql": sql,
                "binds": {
                    k: (f"<vector {len(v)}>" if isinstance(v, array.array) else v)
                    for k, v in (binds or {}).items()
                },
                "rows": len(rows),
                "ms": round((time.perf_counter() - started) * 1000, 1),
                "served_by": "true cache" if conn is self.r else "primary",
                "identity": self.kind,
                "cache": self.cache_note,
            }
        )
        return rows

    def execute(self, sql, binds=None):
        with self.c.cursor() as cur:
            cur.execute(sql, binds or {})
        self.c.commit()

    def audit(self):
        return json.loads(
            self.query("SELECT HF_OWNER.HF_READ_AUDIT() payload FROM dual")[0]["payload"]
        )

    def nearest(self, text, k=8, embedding=None):
        # A cached question embedding is bound directly; otherwise the database embeds the text in SQL.
        target = ":v" if embedding is not None else f"VECTOR_EMBEDDING({EMBED} USING :q AS DATA)"
        return self.query(
            f"""/* HF:vector */ SELECT chunk_id,note_id,instrument_id,desk,passage,
        VECTOR_DISTANCE(embedding,{target},COSINE) distance
        FROM HF_OWNER.HF_CHUNKS ORDER BY distance FETCH FIRST {int(k)} ROWS ONLY""",
            {"v": vector(embedding)} if embedding is not None else {"q": text},
        )

    def rerank(self, text, passages, keep=5):
        if not RERANK:
            return passages[:keep], {
                "state": "not configured",
                "method": "vector distance order",
                "model": None,
            }
        if not passages:
            return [], {"state": "running", "method": "in-database ONNX", "model": RERANK}
        # The installed ONNX model has DATA input. Its exported tokenizer accepts [SEP].
        rows = self.query(
            f"""/* HF:rerank */ SELECT j.idx,
        PREDICTION({RERANK} USING (:q || ' [SEP] ' || j.doc) AS DATA) AS score
        FROM JSON_TABLE(:docs,'$[*]' COLUMNS(idx FOR ORDINALITY,doc VARCHAR2(4000) PATH '$')) j ORDER BY score DESC""",
            {"q": text, "docs": json.dumps([p["passage"] for p in passages])},
        )
        return [dict(passages[int(r["idx"]) - 1], rerank_score=r["score"]) for r in rows[:keep]], {
            "state": "running",
            "method": "in-database ONNX PREDICTION",
            "model": RERANK,
        }
