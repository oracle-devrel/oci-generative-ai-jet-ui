"""Read-path layers: health, foundation (in-DB embeddings), substrate (scratch FS),
retrieval ladder, and the semantic catalog."""
from __future__ import annotations

from fastapi import APIRouter
from fastapi.concurrency import run_in_threadpool

from backend.config import settings
from backend.core import db, scratch
from backend.schemas import EmbedReq, SearchReq, WriteReq

router = APIRouter(prefix="/api", tags=["layers"])


# ── meta ────────────────────────────────────────────────────────────────────
@router.get("/health")
def health() -> dict:
    return {
        "model": settings.model,
        "api_key_set": bool(settings.anthropic_api_key),
        "oracle_enabled": settings.oracle_enabled,
        "harness": db.status(),
    }


# ── Layer 1 — Foundation: in-database embeddings ─────────────────────────────
@router.post("/foundation/embed")
async def embed(req: EmbedReq) -> dict:
    prev = await run_in_threadpool(db.embedding_preview, req.text)
    return {"model": settings.embed_model, **prev}


@router.get("/foundation/models")
async def models() -> dict:
    rows = await run_in_threadpool(
        db.q, "SELECT model_name, mining_function FROM user_mining_models ORDER BY 1"
    )
    return {"models": rows}


# ── Layer 2 — Memory substrate: the in-database scratch filesystem ───────────
@router.post("/substrate/write")
async def fs_write(req: WriteReq) -> dict:
    await run_in_threadpool(scratch.write, req.path, req.content)
    return {"ok": True, "path": scratch._abs(req.path)}


@router.get("/substrate/read")
async def fs_read(path: str, mode: str = "full", n: int = 10, pattern: str = "") -> dict:
    def _do():
        if mode == "tail":
            return {"text": scratch.tail(path, n)}
        if mode == "grep":
            return {"hits": scratch.grep(pattern, path if path.endswith("/") else "/")}
        return {"text": scratch.read(path)}

    try:
        return await run_in_threadpool(_do)
    except Exception as e:
        return {"error": str(e)}


@router.get("/substrate/list")
async def fs_list(root: str = "/") -> dict:
    return {"files": await run_in_threadpool(scratch.listing, root)}


@router.get("/substrate/acid")
async def acid_demo() -> dict:
    """Lost-update race: an OS file with no lock vs. an atomic DB UPDATE."""

    def _do():
        import os
        import tempfile
        import threading
        import time

        cf = os.path.join(tempfile.gettempdir(), "tr_appbook_counter.txt")
        open(cf, "w").write("0")

        def os_inc():
            for _ in range(300):
                v = int(open(cf).read() or 0)
                time.sleep(0.0002)
                open(cf, "w").write(str(v + 1))

        ts = [threading.Thread(target=os_inc) for _ in range(2)]
        [t.start() for t in ts]
        [t.join() for t in ts]
        os_final = int(open(cf).read())
        db.ddl("CREATE TABLE race_counter (id NUMBER PRIMARY KEY, n NUMBER)")
        db.x(
            "MERGE INTO race_counter d USING (SELECT 1 id FROM dual) s ON (d.id=s.id) "
            "WHEN MATCHED THEN UPDATE SET n=0 WHEN NOT MATCHED THEN INSERT (id,n) VALUES (1,0)"
        )

        def db_inc():
            for _ in range(300):
                db.x("UPDATE race_counter SET n=n+1 WHERE id=1")

        ts = [threading.Thread(target=db_inc) for _ in range(2)]
        [t.start() for t in ts]
        [t.join() for t in ts]
        db_final = db.q("SELECT n FROM race_counter WHERE id=1")[0]["N"]
        return {"target": 600, "os_file": os_final, "database": db_final}

    return await run_in_threadpool(_do)


# ── Layer 3 — Retrieval ladder ───────────────────────────────────────────────
@router.post("/retrieval/search")
async def retrieval(req: SearchReq) -> dict:
    hits = await run_in_threadpool(db.retrieve, req.query, req.technique, "knowledge", req.k)
    out = [
        {
            "content": str(h["CONTENT"]),
            "dist": h.get("DIST"),
            "score": h.get("SCORE"),
            "rrf": h.get("rrf"),
            "rerank_score": h.get("rerank_score"),
        }
        for h in hits
    ]
    return {"technique": req.technique, "rerank_available": db.status()["rerank"], "hits": out}


# ── Layer 5 — Semantic catalog ───────────────────────────────────────────────
@router.post("/semantic/search")
async def semantic(req: SearchReq) -> dict:
    hits = await run_in_threadpool(db.semantic_search, req.query, req.k or 6)
    return {"hits": [{"content": str(h["CONTENT"]), "dist": h.get("DIST")} for h in hits]}
