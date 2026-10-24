"""Local-only appbook server. Run: python server.py --port 8890"""
from __future__ import annotations

import argparse
import json
import os
import re
import threading
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv

HERE = Path(__file__).resolve().parent
load_dotenv(os.getenv("APPBOOK_ENV_FILE", str(HERE / ".env")))

import claude  # noqa: E402
import lab  # noqa: E402
import oracledb  # noqa: E402
import sections  # noqa: E402
from fastapi import FastAPI, HTTPException, Request  # noqa: E402
from fastapi.responses import FileResponse, JSONResponse, Response  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402
from pydantic import BaseModel, Field  # noqa: E402


@asynccontextmanager
async def lifespan(_app):
    status = lab.status()  # build the lab on first start, in the background
    if not status["built"] and (status["connected"] or lab.admin_route()):
        start_build()
    yield


app = FastAPI(title="Agent Memory Checklist · Appbook", docs_url="/api/docs", lifespan=lifespan)


@app.middleware("http")
async def local_origin(request: Request, call_next):
    origin = request.headers.get("origin")
    if request.method not in {"GET", "HEAD", "OPTIONS"} and origin:
        if origin != f"{request.url.scheme}://{request.headers.get('host')}":
            return JSONResponse(
                {"detail": "Use this app from its own localhost page."}, status_code=403
            )
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "same-origin"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; "
        "connect-src 'self'; frame-ancestors 'none'; base-uri 'self'"
    )
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    return response


def safe_error(error):
    """Never send keys, passwords or tracebacks to the browser."""
    text = re.sub(r"sk-ant-[A-Za-z0-9_\-]+|hf_[A-Za-z0-9]+", "[redacted]", str(error))
    for secret in [lab.PASSWORD, *lab.END_USERS.values()]:
        text = text.replace(secret, "[redacted]")
    return text.strip().splitlines()[0][:400] if text.strip() else type(error).__name__


# ----------------------------------------------------------------------------------------------- the lab
def build_job():
    state = lab.STATE["build"]
    state.update(running=True, log=[], error=None)
    try:
        if not lab.status()["connected"]:
            state["log"].append(
                f"creating schema {lab.USER} and the end users ({lab.admin_route() or 'no admin route'})"
            )
            lab.run_setup()
        lab.build(state["log"])
        state["log"].append("ready")
    except Exception as e:  # shown in the UI; the server keeps running
        state["error"] = safe_error(e)
    finally:
        state["running"] = False


def start_build():
    if not lab.STATE["build"]["running"]:
        threading.Thread(target=build_job, daemon=True).start()


def hf_ready():
    try:
        from huggingface_hub import get_token

        return bool(get_token())
    except ImportError:
        return False


@app.get("/api/status")
def status():
    return lab.plain(
        {
            **lab.status(),
            "claude": bool(claude.client),
            "claude_model": claude.MODEL,
            "hf": hf_ready(),
            "reranker": bool(lab.STATE.get("reranker")),
            "build": lab.STATE["build"],
            "results": lab.STATE["results"],
            "admin_route": lab.admin_route(),
            "schema": lab.USER,
        }
    )


@app.post("/api/lab/build")
def rebuild():
    start_build()
    return {"started": True}


# ----------------------------------------------------------------------------------------------- sections
@app.post("/api/run/{sid}/{action}")
def run(sid: str, action: str, params: dict | None = None):
    if action not in sections.RUNS.get(sid, {}):
        raise HTTPException(404, "No such section or run.")
    if lab.STATE["build"]["running"]:
        raise HTTPException(409, "The lab is still building. Try again in a moment.")
    try:
        return lab.plain(sections.run(sid, action, params))
    except oracledb.DatabaseError as e:
        return {"status": "error", "verdict": "bad", "summary": safe_error(e)}
    except Exception as e:  # Claude errors, refusals, network failures
        return {"status": "error", "verdict": "bad", "summary": safe_error(e)}


class Ask(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    memory_ids: list[str] = Field(default_factory=list, max_length=20)
    user: str | None = None


@app.post("/api/ask")
def ask(request: Ask):
    if not claude.client:
        raise HTTPException(400, "Set ANTHROPIC_API_KEY to ask Claude.")
    with lab.LOCK:
        rows = lab.q(
            """SELECT memory_id, content FROM memories
                        WHERE memory_id IN (SELECT id FROM JSON_TABLE(:ids, '$[*]' COLUMNS (id VARCHAR2(40) PATH '$')))""",
            {"ids": json.dumps(request.memory_ids)},
        )
    order = {m: i for i, m in enumerate(request.memory_ids)}
    rows.sort(key=lambda r: order[r["memory_id"]])
    try:
        return {
            "answer": claude.answer(request.question, rows, request.user),
            "memories": len(rows),
            "model": claude.MODEL,
        }
    except Exception as e:
        raise HTTPException(502, safe_error(e)) from e


@app.get("/api/scorecard")
def scorecard():
    return lab.STATE["results"]


# ----------------------------------------------------------------------------------------------- data explorer
EXPLORER = {
    "memories": """SELECT memory_id, user_id, agent_id, memory_type, importance, created_at, valid_to,
                          JSON_VALUE(metadata, '$.project') AS project, content{score}
                   FROM memories WHERE 1 = 1 {where} ORDER BY {order} FETCH FIRST 200 ROWS ONLY""",
    "memory_entities": """SELECT e.entity_id, e.name, e.kind,
                                 (SELECT COUNT(*) FROM memory_mentions m WHERE m.entity_id = e.entity_id) AS mentioned_by
                          FROM memory_entities e ORDER BY e.entity_id""",
    "memory_mentions": "SELECT memory_id, entity_id FROM memory_mentions ORDER BY memory_id, entity_id",
    "memory_relations": "SELECT src_id, link_type, dst_id FROM memory_relations ORDER BY src_id",
    "memory_artifacts": """SELECT artifact_id, memory_id, mime_type, file_name, DBMS_LOB.GETLENGTH(text_body) AS text_bytes,
                                  DBMS_LOB.GETLENGTH(binary_body) AS binary_bytes FROM memory_artifacts ORDER BY artifact_id""",
    "memory_dv": """SELECT JSON_VALUE(data, '$._id') AS id, JSON_SERIALIZE(data PRETTY) AS document FROM memory_dv
                    ORDER BY 1 FETCH FIRST 100 ROWS ONLY""",
    "scratchpad": """SELECT pathname, pathtype, DBMS_LOB.GETLENGTH(filedata) AS bytes, std_modification_time AS modified
                     FROM dbfs_content WHERE pathname LIKE '/scratch/%' AND pathname NOT LIKE '/scratch/.sfs%' ORDER BY pathname""",
    "audit_trail": """SELECT event_timestamp, end_user_name, REGEXP_SUBSTR(client_identifier, '^[^:]+') AS agent_id,
                             REGEXP_SUBSTR(client_identifier, '[^:]+$') AS request_id, action_name, sql_text
                      FROM unified_audit_trail WHERE unified_audit_policies LIKE '%APPBOOK_MEMORY_READS%'
                      ORDER BY event_timestamp DESC FETCH FIRST 100 ROWS ONLY""",
    "user_data_grants": "SELECT * FROM user_data_grants",
}


@app.get("/api/explorer/{table}")
def explore(
    table: str,
    user: str = "",
    memory_type: str = "",
    project: str = "",
    status: str = "all",
    search: str = "",
):
    if table not in EXPLORER:
        raise HTTPException(404, "Unknown table.")
    sql, binds = EXPLORER[table], {}
    if table == "memories":
        where = []
        for column, value in (("user_id", user), ("memory_type", memory_type)):
            if value:
                where.append(f"AND {column} = :{column}")
                binds[column] = value
        if project:
            where.append("AND JSON_VALUE(metadata, '$.project') = :project")
            binds["project"] = project
        if status in ("current", "closed"):
            where.append(
                "AND valid_to IS NULL" if status == "current" else "AND valid_to IS NOT NULL"
            )
        score, order = "", "memory_id"
        if search.strip():
            score = f", ROUND(1 - VECTOR_DISTANCE(embedding, VECTOR_EMBEDDING({lab.MODEL} USING :search AS data), COSINE), 4) AS score"
            order = f"VECTOR_DISTANCE(embedding, VECTOR_EMBEDDING({lab.MODEL} USING :search AS data), COSINE)"
            binds["search"] = search.strip()
        sql = sql.format(score=score, where=" ".join(where), order=order)
    try:
        with lab.LOCK:
            rows = lab.q(sql, binds)
    except oracledb.DatabaseError as e:
        raise HTTPException(400, safe_error(e)) from e
    return {"table": table, "sql": sql.strip(), "rows": lab.plain(rows)}


@app.get("/api/memory/{memory_id}")
def memory_detail(memory_id: str):
    with lab.LOCK:
        rows = lab.q(
            """SELECT memory_id, user_id, agent_id, memory_type, importance, created_at, valid_from, valid_to,
                               source_thread_id, content, metadata, embedding, VECTOR_NORM(embedding) AS norm
                        FROM memories WHERE memory_id = :m""",
            {"m": memory_id},
        )
        if not rows:
            raise HTTPException(404, "No such memory.")
        detail = {
            "memory": rows[0],
            "entities": lab.q(
                """SELECT e.entity_id, e.name, e.kind FROM memory_mentions m
                                 JOIN memory_entities e ON e.entity_id = m.entity_id WHERE m.memory_id = :m""",
                {"m": memory_id},
            ),
            "links": lab.q(
                """SELECT src_id, link_type, dst_id FROM memory_relations
                              WHERE src_id = :m OR dst_id = :m""",
                {"m": memory_id},
            ),
            "artifacts": lab.q(
                """SELECT artifact_id, mime_type, file_name FROM memory_artifacts WHERE memory_id = :m""",
                {"m": memory_id},
            ),
            "neighbours": lab.q(
                """SELECT memory_id, ROUND(1 - VECTOR_DISTANCE(embedding, (SELECT embedding FROM memories WHERE memory_id = :m), COSINE), 4) AS score, content
                                    FROM memories WHERE memory_id <> :m AND valid_to IS NULL
                                    ORDER BY VECTOR_DISTANCE(embedding, (SELECT embedding FROM memories WHERE memory_id = :m), COSINE)
                                    FETCH FIRST 3 ROWS ONLY""",
                {"m": memory_id},
            ),
        }
    detail["memory"]["embedding_preview"] = [
        round(v, 4) for v in list(detail["memory"].pop("embedding") or [])[:16]
    ]
    detail["memory"]["norm"] = round(detail["memory"]["norm"] or 0, 4)
    return lab.plain(detail)


@app.get("/api/artifact/{artifact_id}")
def artifact(artifact_id: str):
    with lab.LOCK:
        rows = lab.q(
            "SELECT mime_type, text_body, binary_body FROM memory_artifacts WHERE artifact_id = :a",
            {"a": artifact_id},
        )
    if not rows:
        raise HTTPException(404, "No such artifact.")
    r = rows[0]
    return Response(
        r["binary_body"] if r["binary_body"] is not None else (r["text_body"] or "").encode(),
        media_type=r["mime_type"] if r["binary_body"] is not None else "text/plain; charset=utf-8",
    )


@app.get("/api/file")
def scratch_file(path: str):
    if not path.startswith("/scratch/") or ".sfs" in path:
        raise HTTPException(400, "Only files under /scratch/ can be read.")
    with lab.LOCK:
        rows = lab.q(
            "SELECT filedata FROM dbfs_content WHERE pathname = :p AND pathtype = 'file'",
            {"p": path},
        )
    if not rows:
        raise HTTPException(404, "No such file.")
    return Response(rows[0]["filedata"], media_type="text/plain; charset=utf-8")


@app.get("/")
def index():
    return FileResponse(HERE / "static" / "index.html")


app.mount("/static", StaticFiles(directory=HERE / "static"), name="static")


if __name__ == "__main__":
    import uvicorn

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8890)
    uvicorn.run(app, host="127.0.0.1", port=parser.parse_args().port, access_log=False)
