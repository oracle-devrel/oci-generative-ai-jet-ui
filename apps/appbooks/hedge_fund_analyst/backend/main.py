import asyncio
import json
import logging
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Literal

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .agent import embed_fresh, resolve_entities, run_agent
from .config import PERSONAS, ROOT, env
from .db import DB, cache_status
from .memory import inventory, recall, reset_memories
from .models import available
from .simulate import MIXES, generate

app = FastAPI(title="Hedge Fund Analyst · The Intelligence Plane")
LAST_PERSONA = {"name": "Credit"}


def warm():
    # Warm only the desk in use: each desk's memory session alone holds ~330-500 MB of Free's 2 GB PGA.
    persona = LAST_PERSONA["name"]
    try:
        # Both agents run at once, so both desk sessions in the pool must have the ONNX models loaded.
        sessions = [DB(persona, "hf-warmup"), DB(persona, "hf-warmup")]
        try:
            # Desk sessions only score with the reranker; embeddings now run on True Cache.
            for db in sessions:
                db.rerank("warm up", [{"passage": "warm up"}])
        finally:
            for db in sessions:
                db.close()
        recall(persona, "warm up", "hf-warmup")
        mem = DB(persona, "hf-warmup", memory=True)
        try:
            mem.query(
                "SELECT VECTOR_EMBEDDING(HF_OWNER.HF_EMBED USING 'warm up' AS DATA) v FROM dual",
                route="cache",
            )
        finally:
            mem.close()
    except Exception:
        logging.getLogger("hf").exception("Warm-up failed for %s", persona)


def keep_warm():
    while True:
        # Never compete with a running turn for Free's 2 CPUs and 2 GB PGA.
        if RUN_GATE.acquire(blocking=False):
            try:
                warm()
            finally:
                RUN_GATE.release()
        time.sleep(240)


@app.on_event("startup")
def startup():
    threading.Thread(target=keep_warm, daemon=True).start()


LOCKS = {}
LOCK = threading.Lock()
RUN_GATE = threading.Semaphore(1)
TABLES = {
    name.lower(): name
    for name in [
        "HF_ISSUERS",
        "HF_ENTITIES",
        "HF_RELATIONSHIPS",
        "HF_INSTRUMENTS",
        "HF_POSITIONS",
        "HF_PORTFOLIOS",
        "HF_DESKS",
        "HF_COLLATERAL",
        "HF_PRICES",
        "HF_NOTES",
        "HF_CHUNKS",
        "HF_SEMANTICS",
        "HF_GOLDEN",
        "HF_CAPABILITIES",
    ]
}


class Turn(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    persona: Literal["Credit", "Markets"] = "Credit"
    model_id: str = Field(default_factory=lambda: env("HF_DEFAULT_MODEL", "ollama"))
    thread_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()), pattern=r"^[A-Za-z0-9_-]{1,80}$"
    )


def read(persona, sql, binds=None, request_id=None, memory=False):
    db = DB(persona, request_id, memory)
    try:
        return db.query(sql, binds)
    finally:
        db.close()


def isolation(persona):
    # Live control check: the definer-rights graph must return only this identity's desk.
    desks = [
        r["desk"]
        for r in read(
            persona,
            "/* HF:isolation */ SELECT DISTINCT desk FROM GRAPH_TABLE(HF_OWNER.HF_GRAPH MATCH (p IS Position) COLUMNS(p.desk AS desk))",
        )
    ]
    return {"persona": persona, "graph_desks": desks, "isolated": desks == [persona]}


def entitlement(persona):
    # Live Deep Data Security check: an unfiltered, injection-style query must still return only this desk's rows.
    r = read(
        persona,
        "/* HF:dds_check */ SELECT COUNT(*) n,COUNT(DISTINCT desk) desks,MIN(desk) desk,ORA_END_USER_CONTEXT.username end_user FROM HF_OWNER.HF_POSITIONS WHERE desk<>'nobody' OR 1=1 GROUP BY ORA_END_USER_CONTEXT.username",
    )[0]
    return {"persona": persona, **r, "entitled": r["desks"] == 1 and r["desk"] == persona}


@app.get("/api/health")
def health():
    try:
        identities = read("Credit", "SELECT ORA_END_USER_CONTEXT.username AS identity FROM dual")
        capabilities = read("Credit", "/* HF:health */ SELECT * FROM HF_OWNER.HF_CAPABILITIES")
        checks = [isolation(p) for p in PERSONAS]
        dds = [entitlement(p) for p in PERSONAS]
        ok = all(c["entitled"] for c in dds)
        capabilities = [
            dict(
                c,
                component="deep_data_security",
                state="verified" if ok else "failed",
                detail=(
                    "Live check: an OR 1=1 query with no desk filter returns "
                    if ok
                    else "ENTITLEMENT CHECK FAILED: "
                )
                + "; ".join(f"{c['end_user']} → {c['n']} rows, desk {c['desk']}" for c in dds)
                + ". End users, data roles and desk data grants enforced by Oracle.",
            )
            if c["component"] == "governance"
            else c
            for c in capabilities
        ]
        # True Cache state comes from a live session check, never from configuration alone.
        tc = cache_status()
        capabilities = [
            dict(
                c,
                state=tc["state"],
                detail=(
                    "Serving the cache tier and ontology/catalog reads; "
                    if tc["state"] == "running"
                    else ""
                )
                + tc["detail"]
                + (
                    ". Desk-entitled reads stay on the primary: DDS end users cannot log in to True Cache (ORA-16000)."
                    if tc["state"] == "running"
                    else ""
                ),
            )
            if c["component"] == "true_cache"
            else c
            for c in capabilities
        ]
        if not all(c["isolated"] for c in checks):
            capabilities = [
                dict(c, state="failed", detail="Graph returned another desk: " + json.dumps(checks))
                if c["component"] == "governance"
                else c
                for c in capabilities
            ]
        models = available()
        return {
            "title": "Hedge Fund Analyst",
            "mode": "live",
            "ready": all(c["isolated"] for c in checks) and ok,
            "entitlements": dds,
            "identity": identities,
            "components": capabilities,
            "isolation": checks,
            "models": models,
            "default_model": env("HF_DEFAULT_MODEL", "ollama"),
            "configuration": {
                "oracle_enabled": True,
                "model_live": True,
                "model_configured": any(m["enabled"] for m in models),
                "model_provider": env("HF_DEFAULT_MODEL", "ollama"),
                "model": env("HF_DEFAULT_MODEL", "ollama"),
            },
            "limits": [
                "Demo persona selector represents trusted local identity selection, not production authentication.",
                "Companies, legal-entity trees, portfolios and research are fictional; trees follow the GLEIF Level 2 structure with synthetic LEIs.",
            ],
        }
    except Exception as e:
        return {
            "title": "Hedge Fund Analyst",
            "mode": "live",
            "ready": False,
            "error": str(e)[:1000],
            "models": available(),
        }


@app.get("/api/models")
def models():
    return {"models": available()}


@app.post("/api/session")
def session():
    return {"thread_id": str(uuid.uuid4())}


class Simulation(BaseModel):
    turns: int = Field(10, ge=1, le=50)
    persona: Literal["Credit", "Markets"] = "Credit"
    model_id: str = Field(default_factory=lambda: env("HF_DEFAULT_MODEL", "ollama"))
    mix: Literal["golden", "repeat", "numeric"] = "golden"
    thread_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()), pattern=r"^[A-Za-z0-9_-]{1,80}$"
    )
    seed: int = Field(default_factory=lambda: int(time.time()))


def sse(kind, payload):
    return "event: " + kind + "\ndata: " + json.dumps(payload, default=str) + "\n\n"


async def pair(persona, thread_id, question, model_id, golden_id=None):
    # Both agents run the same question concurrently; events stream as each finishes.
    run = str(uuid.uuid4())
    loop = asyncio.get_running_loop()
    queue = asyncio.Queue()
    executor = ThreadPoolExecutor(max_workers=2)

    def emit(kind, payload):
        loop.call_soon_threadsafe(queue.put_nowait, (kind, payload))

    def work(agent):
        try:
            emit("answer", run_agent(agent, persona, thread_id, question, model_id, run, golden_id))
        except Exception as e:
            logging.getLogger("hf").exception("Agent turn failed: %s", agent)
            emit("agent_error", {"agent": agent, "error": str(e)[:1200], "run_id": run})
        finally:
            emit("agent_done", {"agent": agent})

    try:
        yield sse(
            "start",
            {
                "run_id": run,
                "thread_id": thread_id,
                "persona": persona,
                "model_id": model_id,
                "question": question,
            },
        )
        for agent in ["plane", "naive"]:
            executor.submit(work, agent)
        done = 0
        while done < 2:
            try:
                kind, payload = await asyncio.wait_for(queue.get(), timeout=15)
            except asyncio.TimeoutError:
                yield ": heartbeat\n\n"
                continue
            if kind == "agent_done":
                done += 1
                continue
            yield sse(kind, payload)
    finally:
        # A disconnected browser must not release locks while workers still write.
        await asyncio.to_thread(executor.shutdown, wait=True)


def admit(persona, thread_id, model_id):
    LAST_PERSONA["name"] = persona
    models = {m["id"]: m for m in available()}
    if model_id not in models or not models[model_id]["enabled"]:
        raise HTTPException(409, models.get(model_id, {}).get("reason", "Unknown model"))
    with LOCK:
        lock = LOCKS.setdefault((persona, thread_id), threading.Lock())
    if not lock.acquire(blocking=False):
        raise HTTPException(409, "A turn is already running for this persona and session")
    return lock


@app.post("/api/chat")
def chat(turn: Turn):
    lock = admit(turn.persona, turn.thread_id, turn.model_id)

    async def stream():
        await asyncio.to_thread(RUN_GATE.acquire)
        try:
            async for event in pair(turn.persona, turn.thread_id, turn.question, turn.model_id):
                yield event
            yield sse("done", {})
        finally:
            lock.release()
            RUN_GATE.release()

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/api/simulate/mixes")
def mixes():
    return {"mixes": MIXES}


@app.post("/api/simulate")
async def simulate(sim: Simulation, request: Request):
    lock = admit(sim.persona, sim.thread_id, sim.model_id)

    async def stream():
        await asyncio.to_thread(RUN_GATE.acquire)
        try:
            items = await asyncio.to_thread(generate, sim.persona, sim.turns, sim.mix, sim.seed)
            yield sse(
                "sim_start",
                {
                    "turns": len(items),
                    "mix": sim.mix,
                    "seed": sim.seed,
                    "thread_id": sim.thread_id,
                    "persona": sim.persona,
                    "model_id": sim.model_id,
                    "questions": items,
                },
            )
            for i, item in enumerate(items):
                # Stop between turns when the browser goes away (Stop button); never mid-turn.
                if await request.is_disconnected():
                    break
                yield sse("sim_turn", {"index": i + 1, "of": len(items), **item})
                async for event in pair(
                    sim.persona, sim.thread_id, item["question"], sim.model_id, item["golden_id"]
                ):
                    yield event
            yield sse("sim_done", {"completed": i + 1 if items else 0})
        finally:
            lock.release()
            RUN_GATE.release()

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/api/data/tables")
def tables(persona: Literal["Credit", "Markets"] = "Credit"):
    rows = []
    for id, name in TABLES.items():
        count = read(persona, "/* HF:count */ SELECT COUNT(*) n FROM HF_OWNER." + name)[0]["n"]
        rows.append({"id": id, "name": name, "row_count": count, "source": "oracle"})
    return {"database_status": "connected", "persona": persona, "tables": rows}


@app.get("/api/data/{table}")
def table(
    table: str,
    persona: Literal["Credit", "Markets"] = "Credit",
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    if table not in TABLES:
        raise HTTPException(404, "Unknown table")
    name = TABLES[table]
    fields = (
        "*"
        if name != "HF_CHUNKS"
        else "chunk_id,note_id,instrument_id,desk,passage,VECTOR_DIMENSION_COUNT(embedding) dimensions"
    )
    return {
        "source": "Oracle / database enforced entitlements",
        "persona": persona,
        "rows": read(
            persona,
            f"/* HF:explorer */ SELECT {fields} FROM HF_OWNER.{name} ORDER BY 1 OFFSET {offset} ROWS FETCH NEXT {limit} ROWS ONLY",
        ),
    }


@app.get("/api/graph")
def graph(persona: Literal["Credit", "Markets"] = "Credit", group: str = "Acme"):
    db = DB(persona)
    try:
        nodes = resolve_entities(db, group)
    finally:
        db.close()
    edges = read(
        persona,
        "/* HF:edges */ SELECT r.* FROM HF_OWNER.HF_RELATIONSHIPS r JOIN HF_OWNER.HF_ENTITIES e ON e.lei=r.parent_lei JOIN HF_OWNER.HF_ISSUERS g ON g.issuer_id=e.issuer_id WHERE g.alias=:g",
        {"g": group},
    )
    paths = read(
        persona,
        """/* HF:graphpaths */ SELECT * FROM GRAPH_TABLE(HF_OWNER.HF_GRAPH MATCH
    (g IS Issuer)-[a IS HasEntity]->(e IS LegalEntity)-[b IS Issues]->(i IS Instrument)-[c IS HeldIn]->(p IS Position)-[d IS BelongsTo]->(f IS Portfolio)-[m IS ManagedBy]->(desk IS Desk)
    WHERE g.alias=:g COLUMNS(g.alias AS issuer,e.lei AS lei,i.ticker AS ticker,p.position_id AS position_id,p.market_value AS market_value,desk.desk AS desk)) FETCH FIRST 100 ROWS ONLY""",
        {"g": group},
    )
    return {
        "nodes": nodes,
        "edges": edges,
        "paths": paths,
        "source": "SQL property graph / SQL-PGQ",
        "scope": "Fictional groups · GLEIF-style parent/child structure",
    }


@app.get("/api/vectors")
def vectors(
    q: str = Query(min_length=1, max_length=2000), persona: Literal["Credit", "Markets"] = "Credit"
):
    db = DB(persona)
    try:
        initial = db.nearest(q, 8, embedding=embed_fresh(persona, q, "hf-explorer"))
        reranked, status = db.rerank(q, initial)
        return {
            "nearest": initial,
            "reranked": reranked,
            "rerank": status,
            "embedding_source": "Oracle VECTOR_EMBEDDING / HF_EMBED",
            "sql": db.trace,
        }
    finally:
        db.close()


@app.get("/api/memory")
def memory(persona: Literal["Credit", "Markets"] = "Credit"):
    return inventory(persona)


@app.post("/api/memory/reset")
def memory_reset(persona: Literal["Credit", "Markets"] = "Credit"):
    # Demo reset: removes this desk's durable facts under its own memory identity.
    return {"persona": persona, "deleted": reset_memories(persona, "hf-reset")}


@app.get("/api/semcache")
def semcache(persona: Literal["Credit", "Markets"] = "Credit"):
    return {
        "rows": read(
            persona,
            "/* HF:semcache_browse */ SELECT cache_id,question,action,metric,group_name,model,hits,created_at,last_hit,CASE WHEN answer IS NULL THEN 'plan' ELSE 'plan + answer' END reuse FROM HF_SEMCACHE ORDER BY created_at DESC FETCH FIRST 100 ROWS ONLY",
            memory=True,
        )
    }


@app.post("/api/semcache/reset")
def semcache_reset(persona: Literal["Credit", "Markets"] = "Credit"):
    db = DB(persona, "hf-reset", memory=True)
    try:
        # Clears this desk's cache tier: exact responses, question embeddings and semantic plans. The delete
        # runs on the primary; True Cache drops the rows through redo apply, with no invalidation code.
        counts = {}
        for table in ["HF_RESPONSE_CACHE", "HF_EMBED_CACHE", "HF_SEMCACHE"]:
            counts[table] = db.query(f"SELECT COUNT(*) n FROM {table}")[0]["n"]
            db.execute(f"DELETE FROM {table}")
        return {"persona": persona, "deleted": sum(counts.values()), "tables": counts}
    finally:
        db.close()


@app.get("/api/sql")
def sql(persona: Literal["Credit", "Markets"] = "Credit"):
    return {
        "rows": json.loads(
            read(persona, "SELECT HF_OWNER.HF_READ_SQL() payload FROM dual")[0]["payload"]
        )
    }


@app.get("/api/audit")
def audit(
    request_id: str = Query(pattern=r"^[A-Za-z0-9_-]+:(plane|naive)$"),
    persona: Literal["Credit", "Markets"] = "Credit",
):
    # The view additionally scopes by CLIENT_IDENTIFIER; returned records are real Unified Audit records.
    return {
        "request_id": request_id,
        "rows": json.loads(
            read(
                persona, "SELECT HF_OWNER.HF_READ_AUDIT() payload FROM dual", request_id=request_id
            )[0]["payload"]
        ),
        "note": "Auditing flushes asynchronously. Refresh if no records are visible yet.",
    }


@app.get("/api/runs")
def runs(
    persona: Literal["Credit", "Markets"] = "Credit",
    thread_id: str = Query(pattern=r"^[A-Za-z0-9_-]{1,80}$"),
):
    return {
        "runs": [
            (json.loads(x["payload"]) if isinstance(x["payload"], str) else x["payload"])
            for x in read(
                persona,
                "SELECT payload FROM HF_RESULTS WHERE thread_id=:t",
                {"t": thread_id},
                memory=True,
            )
        ]
    }


# Deep Data Security primer: fixed, read-only checks run under each desk's real end-user identity.
DDS_CHECKS = [
    (
        "same_sql",
        "Identical SQL, no desk filter",
        "SELECT /* HF:primer */ COUNT(*) positions,COUNT(DISTINCT desk) desks,MIN(desk) desk,ROUND(SUM(market_value)) signed_usd FROM HF_OWNER.HF_POSITIONS",
    ),
    (
        "injection",
        "Injection-style predicate: OR 1=1",
        "SELECT /* HF:primer */ COUNT(*) positions,LISTAGG(DISTINCT desk,',') desks FROM HF_OWNER.HF_POSITIONS WHERE desk<>'nobody' OR 1=1",
    ),
    (
        "other_desk",
        "Explicitly ask for both desks",
        "SELECT /* HF:primer */ COUNT(*) positions,LISTAGG(DISTINCT desk,',') desks FROM HF_OWNER.HF_POSITIONS WHERE desk IN ('Credit','Markets')",
    ),
    (
        "other_tables",
        "Collateral, research notes, research vectors",
        "SELECT /* HF:primer */ (SELECT LISTAGG(DISTINCT desk,',') FROM HF_OWNER.HF_COLLATERAL) collateral,(SELECT LISTAGG(DISTINCT desk,',') FROM HF_OWNER.HF_NOTES) notes,(SELECT LISTAGG(DISTINCT desk,',') FROM HF_OWNER.HF_CHUNKS) research_vectors FROM dual",
    ),
    (
        "graph",
        "Property graph (runs with definer rights)",
        "SELECT /* HF:primer */ COUNT(*) positions,LISTAGG(DISTINCT desk,',') desks FROM GRAPH_TABLE(HF_OWNER.HF_GRAPH MATCH (p IS Position) COLUMNS(p.desk AS desk))",
    ),
    (
        "shared",
        "Shared reference data (granted to both desks)",
        "SELECT /* HF:primer */ COUNT(*) legal_entities FROM HF_OWNER.HF_ENTITIES",
    ),
    (
        "identity",
        "Who Oracle thinks you are",
        "SELECT /* HF:primer */ ORA_END_USER_CONTEXT.username end_user,SYS_CONTEXT('USERENV','AUTHENTICATED_IDENTITY') authenticated_identity FROM dual",
    ),
]


def dds_pass(key, persona, row):
    own = persona
    if key == "same_sql":
        return row["desks"] == 1 and row["desk"] == own
    if key in ("injection", "other_desk", "graph"):
        return row["desks"] == own
    if key == "other_tables":
        return row["collateral"] == own and row["notes"] == own and row["research_vectors"] == own
    if key == "shared":
        return row["legal_entities"] > 0
    return row["end_user"] == "hf_" + own.lower()


@app.get("/api/dds/evidence")
def dds_evidence():
    run = "dds-primer-" + uuid.uuid4().hex[:8]
    results = {}
    for persona in PERSONAS:
        db = DB(persona, run + "-" + persona.lower())
        try:
            results[persona] = {
                key: dict(row := db.query(sql)[0], passed=dds_pass(key, persona, row))
                for key, _, sql in DDS_CHECKS
            }
        finally:
            db.close()
    # Unified Audit can flush asynchronously; read each desk's records for this run after a short pause.
    time.sleep(1.5)
    audit = {}
    for persona in PERSONAS:
        db = DB(persona, run + "-" + persona.lower())
        try:
            audit[persona] = [
                {
                    k: r.get(k)
                    for k in (
                        "event_timestamp",
                        "end_user_name",
                        "dbusername",
                        "action_name",
                        "object_name",
                    )
                }
                for r in db.audit()
            ]
        finally:
            db.close()
    return {
        "run": run,
        "checks": [
            {"key": k, "label": label, "sql": sql.replace("/* HF:primer */ ", "")}
            for k, label, sql in DDS_CHECKS
        ],
        "results": results,
        "audit": audit,
    }


@app.get("/primer")
def primer():
    return FileResponse(ROOT / "frontend/primer.html")


@app.get("/")
def index():
    return FileResponse(ROOT / "frontend/index.html")


app.mount("/static", StaticFiles(directory=ROOT / "frontend"), name="static")
