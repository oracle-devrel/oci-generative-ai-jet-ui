"""FastAPI control plane for the migration agent demo."""

import asyncio
import json
import os
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse

from data_migration_harness import schema_discovery, source_config
from data_migration_harness.memory import chat_history
from data_migration_harness.orchestrator import run_migration
from data_migration_harness.tools import duality, generic_oracle

CACHE_PATH = Path(os.environ.get("DEMO_CACHE_PATH", ".cache/demo_cache.json"))

app = FastAPI(title="Oracle Data Migration Harness")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_state = {"running": False, "completed": False, "events": []}


def _load_cache() -> dict:
    if not CACHE_PATH.exists():
        return {}
    return json.loads(CACHE_PATH.read_text() or "{}")


def _save_cache(c: dict):
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(json.dumps(c, indent=2))


def _json_safe(value):
    """Make Mongo/Oracle values safe for JSON responses shown in inspectors."""
    from datetime import date, datetime

    if isinstance(value, dict):
        return {k: _json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_safe(v) for v in value]
    if isinstance(value, datetime | date):
        return value.isoformat()
    return value


def demo_cache_lookup(side: str, question: str) -> dict | None:
    return _load_cache().get(side, {}).get(question.strip().lower())


def save_demo_cache(side: str, question: str, payload: dict):
    cache = _load_cache()
    cache.setdefault(side, {})[question.strip().lower()] = payload
    _save_cache(cache)


# Lazy embedding model loader so app only downloads the model when semantic search runs.
_embedding_model = None


def _embed(text: str) -> list[float]:
    global _embedding_model
    if _embedding_model is None:
        from sentence_transformers import SentenceTransformer

        model_name = os.environ.get("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
        _embedding_model = SentenceTransformer(model_name)
    return _embedding_model.encode([text], normalize_embeddings=True)[0].tolist()


async def _stream_text(text: str):
    for word in text.split(" "):
        yield {"event": "token", "data": word + " "}
        await asyncio.sleep(0.03)
    yield {"event": "done", "data": "[DONE]"}


@app.get("/stats/{side}")
async def stats(side: Literal["mongo", "oracle"]):
    if side == "mongo":
        col = source_config.collection()
        products = col.count_documents({})
        reviews = sum(len(d.get("reviews", [])) for d in col.find({}, {"reviews": 1}))
        categories = len(col.distinct("category")) if products else 0
        vectors = col.count_documents(
            {"$or": [{"review_embedding": {"$exists": True}}, {"embedding": {"$exists": True}}]}
        )
        memory_messages = chat_history.count_mongo_messages()
        return {
            "products": products,
            "reviews": reviews,
            "categories": categories,
            "vectors": vectors,
            "memory_messages": memory_messages,
        }
    # oracle side
    from data_migration_harness.environment import oracle_pool

    pool = oracle_pool()
    with pool.acquire() as conn:
        cur = conn.cursor()
        try:
            cur.execute("SELECT COUNT(*) FROM products")
            (products,) = cur.fetchone()
            cur.execute("SELECT COUNT(*) FROM reviews")
            (reviews,) = cur.fetchone()
            cur.execute("SELECT COUNT(*) FROM (SELECT DISTINCT category FROM products)")
            (categories,) = cur.fetchone()
            cur.execute("SELECT COUNT(*) FROM user_views WHERE view_name = 'PRODUCTS_DV'")
            (duality_views,) = cur.fetchone()
            try:
                cur.execute("SELECT COUNT(*) FROM products WHERE review_embedding IS NOT NULL")
                (vectors,) = cur.fetchone()
            except Exception:
                vectors = 0
            try:
                memory_messages = chat_history.count_oracle_messages(source_side="mongo")
            except Exception:
                memory_messages = 0
            return {
                "products": products,
                "reviews": reviews,
                "categories": categories,
                "duality_views": duality_views,
                "vector_dim": 384,
                "vectors": vectors,
                "memory_messages": memory_messages,
            }
        except Exception:
            return {"migrated": False}


@app.get("/source")
async def source():
    return source_config.get_source_dict()


@app.post("/source/test")
async def source_test(payload: dict):
    return source_config.test_source(
        payload.get("uri", ""),
        payload.get("database", ""),
        payload.get("collection", ""),
    )


@app.post("/source/connect")
async def source_connect(payload: dict):
    try:
        source_config.set_source(
            payload.get("uri", ""),
            payload.get("database", ""),
            payload.get("collection", ""),
        )
        return {"ok": True, "source": source_config.get_source_dict()}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {str(e)[:500]}"}


@app.post("/source/disconnect")
async def source_disconnect():
    source_config.disconnect_source()
    return {"ok": True, "source": source_config.get_source_dict()}


@app.get("/assess")
async def assess():
    return schema_discovery.assess_dict()


@app.get("/memory/{side}")
async def memory(side: Literal["mongo", "oracle"]):
    if side == "mongo":
        messages = chat_history.get_mongo_thread(limit=200)
        return {"side": side, "count": len(messages), "messages": messages}
    messages = chat_history.get_oracle_thread(limit=200)
    return {"side": side, "count": len(messages), "messages": messages}


@app.get("/inspect/mongo")
async def inspect_mongo():
    src = source_config.get_source()
    col = source_config.collection()
    products = col.count_documents({})
    reviews = sum(len(d.get("reviews", [])) for d in col.find({}, {"reviews": 1}))
    profile = schema_discovery.assess(sample_size=50)
    vectors = sum(1 for _ in profile.vectors)
    sample = col.find_one({}) or {}
    sample["_id"] = str(sample.get("_id", ""))
    if sample.get("reviews"):
        sample["reviews"] = sample["reviews"][:2]
    for v in profile.vectors:
        field = v["field"]
        if field in sample:
            sample[field] = f"[{v['dim']}-dimensional vector]"
    return {
        "kind": "mongo",
        "connection": src.uri,
        "database": src.database,
        "collection": src.collection,
        "assessment": profile.to_dict(),
        "stats": {
            "products": products,
            "reviews": reviews,
            "vectors": vectors,
            "vector_dim": profile.vectors[0]["dim"] if profile.vectors else None,
            "memory_messages": chat_history.count_mongo_messages(),
        },
        "sample_document": _json_safe(sample),
    }


@app.get("/inspect/oracle")
async def inspect_oracle():
    from data_migration_harness.environment import oracle_pool

    pool = oracle_pool()
    with pool.acquire() as conn:
        cur = conn.cursor()
        # Generic migration path: arbitrary MongoDB collection landed as JSON.
        try:
            generic = generic_oracle.inspect()
            return {
                "kind": "oracle",
                "migrated": True,
                "mode": "generic_json",
                "dsn": os.environ.get("ORACLE_DSN", "localhost:1521/FREEPDB1"),
                "stats": {
                    "products": generic["raw_count"],
                    "reviews": 0,
                    "duality_views": 0,
                    "vectors": 0,
                    "vector_dim": None,
                    "memory_messages": chat_history.count_oracle_messages(source_side="mongo"),
                },
                "tables": {
                    "raw_json": _json_safe(generic.get("sample")),
                    "scalar_projection": _json_safe(generic.get("projection", [])),
                },
                "duality_sample": None,
                "schema": {
                    "raw_ddl": generic_oracle.raw_ddl(),
                    "projection_ddl": "See generated artefact from migration run.",
                },
            }
        except Exception:
            pass

        # Rich product-review path: relational tables + Duality view + vectors.
        try:
            cur.execute("SELECT COUNT(*) FROM products")
            (products,) = cur.fetchone()
            cur.execute("SELECT COUNT(*) FROM reviews")
            (reviews,) = cur.fetchone()
            cur.execute("SELECT COUNT(*) FROM products WHERE review_embedding IS NOT NULL")
            (vectors,) = cur.fetchone()
            cur.execute("SELECT COUNT(*) FROM user_views WHERE view_name = 'PRODUCTS_DV'")
            (duality_views,) = cur.fetchone()
        except Exception:
            return {"kind": "oracle", "migrated": False}

        cur.execute(
            """
            SELECT product_id, name, category, price
            FROM products
            ORDER BY product_id
            FETCH FIRST 5 ROWS ONLY
        """
        )
        product_cols = [c[0].lower() for c in cur.description]
        product_rows = [dict(zip(product_cols, row, strict=False)) for row in cur.fetchall()]

        cur.execute(
            """
            SELECT review_id, product_id, rating, verified_buyer, SUBSTR(text, 1, 140) AS text
            FROM reviews
            ORDER BY review_id
            FETCH FIRST 5 ROWS ONLY
        """
        )
        review_cols = [c[0].lower() for c in cur.description]
        review_rows = [dict(zip(review_cols, row, strict=False)) for row in cur.fetchall()]

        vector_rows = []
        try:
            cur.execute(
                """
                SELECT review_embedding
                FROM products
                WHERE review_embedding IS NOT NULL
                FETCH FIRST 3 ROWS ONLY
            """
            )
            for idx, row in enumerate(cur.fetchall(), start=1):
                raw_vector = row[0]
                if hasattr(raw_vector, "read"):
                    raw_vector = raw_vector.read()
                if hasattr(raw_vector, "tolist"):
                    embedding_values = raw_vector.tolist()
                elif isinstance(raw_vector, list | tuple):
                    embedding_values = list(raw_vector)
                elif isinstance(raw_vector, str):
                    embedding_values = json.loads(raw_vector)
                else:
                    try:
                        embedding_values = list(raw_vector)
                    except Exception:
                        embedding_values = []
                preview = [round(float(v), 5) for v in embedding_values[:12]]
                vector_rows.append(
                    {
                        "row": idx,
                        "values": preview,
                        "truncated": len(embedding_values) > len(preview),
                    }
                )
        except Exception as e:
            vector_rows = [{"row": 1, "error": f"{type(e).__name__}: {str(e)[:200]}"}]

        duality_sample = None
        if product_rows:
            pid = product_rows[0]["product_id"]
            cur.execute(
                """
                SELECT reviewer_id, rating, verified_buyer, SUBSTR(text, 1, 180) AS text
                FROM reviews
                WHERE product_id = :pid
                ORDER BY review_id
                FETCH FIRST 2 ROWS ONLY
            """,
                {"pid": pid},
            )
            cols = [c[0].lower() for c in cur.description]
            duality_sample = dict(product_rows[0])
            duality_sample["reviews"] = [
                dict(zip(cols, row, strict=False)) for row in cur.fetchall()
            ]

        return {
            "kind": "oracle",
            "migrated": True,
            "mode": "rich_product_reviews",
            "dsn": os.environ.get("ORACLE_DSN", "localhost:1521/FREEPDB1"),
            "stats": {
                "products": products,
                "reviews": reviews,
                "duality_views": duality_views,
                "vectors": vectors,
                "vector_dim": 384,
                "memory_messages": chat_history.count_oracle_messages(source_side="mongo"),
            },
            "tables": {"products": _json_safe(product_rows), "reviews": _json_safe(review_rows)},
            "duality_sample": _json_safe(duality_sample),
            "vector_rows": _json_safe(vector_rows),
            "schema": {
                "products_ddl": duality.PRODUCT_DDL.strip(),
                "reviews_ddl": duality.REVIEW_DDL.strip(),
                "duality_view": duality.DUALITY_VIEW.strip(),
                "vector_ddl": "ALTER TABLE products ADD (review_embedding VECTOR(384, FLOAT32))",
            },
        }


@app.post("/reset")
async def reset():
    """Drop Oracle migration artefacts so the migrate button can run again.

    Leaves dbfs_scratch (audit trail) and agent_run_memory (prior runs) so
    the harness retains its history across rehearsal cycles.
    """
    from data_migration_harness.environment import oracle_pool

    pool = oracle_pool()
    with pool.acquire() as conn:
        cur = conn.cursor()
        for stmt in (
            "DROP VIEW products_dv",
            "DROP TABLE reviews",
            "DROP TABLE products",
            "DROP TABLE products_raw",
            "DROP TABLE mongo_scalar_projection",
            "DROP TABLE mongo_raw_docs",
        ):
            try:
                cur.execute(stmt)
            except Exception:
                pass
        conn.commit()
    try:
        chat_history.clear_mongo_thread()
        chat_history.clear_oracle_memory()
    except Exception:
        pass
    _state["running"] = False
    _state["completed"] = False
    _state["events"] = []
    return {"status": "reset"}


@app.get("/chat/{side}")
async def chat(side: Literal["mongo", "oracle"], q: str):
    if side == "mongo":
        chat_history.save_mongo_message("user", q)
    else:
        chat_history.save_oracle_message("user", q)

    q_l = q.lower()
    asks_about_prior_memory = (
        side == "oracle" and "ask" in q_l and "before" in q_l and "migrat" in q_l
    )
    if asks_about_prior_memory:
        return EventSourceResponse(_stream_memory_answer())

    if os.environ.get("DEMO_CACHE_ENABLED", "false").lower() == "true":
        cached = demo_cache_lookup(side, q)
        if cached:
            return EventSourceResponse(_stream_cached(cached, side=side))
    return EventSourceResponse(_stream_live(side, q))


async def _stream_cached(payload: dict, side: str | None = None):
    if "chart" in payload:
        yield {"event": "chart", "data": json.dumps(payload["chart"])}
    if "text" in payload:
        if side == "mongo":
            chat_history.save_mongo_message("assistant", payload["text"])
        elif side == "oracle":
            chat_history.save_oracle_message("assistant", payload["text"])
        async for evt in _stream_text(payload["text"]):
            yield evt
    yield {"event": "done", "data": "[DONE]"}


async def _stream_memory_answer():
    prior = [
        m
        for m in chat_history.get_oracle_thread(limit=20)
        if m.get("source_side") == "mongo" and m.get("role") == "user"
    ]
    if prior:
        text = f'Before the migration, you asked: "{prior[-1]["content"]}". That conversation was copied from MongoDB into Oracle memory during the transfer stage.'
    else:
        text = "I do not see any MongoDB-side conversation memory yet. Ask a question on the Mongo side, then migrate again."
    chat_history.save_oracle_message("assistant", text)
    async for evt in _stream_text(text):
        yield evt


def _format_args(args: dict) -> str:
    """Format a dict of tool arguments as a readable string.

    Example: {"category": "Audio", "min_rating": 4} -> "category='Audio', min_rating=4"
    """
    parts = []
    for k, v in args.items():
        if isinstance(v, str):
            parts.append(f"{k}='{v}'")
        elif v is None:
            continue
        else:
            parts.append(f"{k}={v}")
    return ", ".join(parts)


def _format_result_brief(result: object) -> str:
    """Summarise a tool result in one short phrase for the tool_status event.

    Examples:
        {"count": 80} -> "80 products found"
        [{"name": ...}, ...] -> "5 results returned"
        {"is_chart": True, "rows": [...]} -> "8 groups returned"
        {"error": "..."} -> "error: ..."
    """
    if isinstance(result, dict):
        if "error" in result:
            return f"error: {result['error'][:100]}"
        if "count" in result:
            return f"{result['count']} products found"
        if "rows" in result:
            return f"{len(result['rows'])} groups returned"
    if isinstance(result, list):
        return f"{len(result)} result{'s' if len(result) != 1 else ''} returned"
    return str(result)[:80]


async def _stream_live(side: str, q: str):
    """Multi-tool agent loop. The LLM picks the right tool(s) for each question.

    Replaces the old single-shot vector-search path. The agent can call
    vector_search, count_products, top_products, or group_by (or a sequence
    of them) before producing its final text response.

    Tool calls are surfaced to the frontend as 'tool_status' events so the
    audience sees the agent working inline -- small grey italic lines above
    the assistant response text.

    The 'group_by' tool returns is_chart=True for category/rating/avg queries,
    which causes the orchestrator to emit a 'chart' event so the frontend
    renders the bar chart rather than embedding numbers in prose.
    """
    from data_migration_harness.model import stream_chat_with_tools
    from data_migration_harness.tools.agent_tools import TOOL_SCHEMAS

    db_label = "MongoDB" if side == "mongo" else "Oracle 26ai"
    system_prompt = (
        f"You are a product reviews assistant. The data lives in {db_label}. "
        f"Users will ask you questions about a 500-product catalogue with embedded reviews. "
        f"You have four tools available. Use them to answer correctly:\n"
        f"  - vector_search: for 'what do people say' open-ended questions\n"
        f"  - count_products: for 'how many products / reviews / items' questions\n"
        f"  - top_products: for 'most expensive', 'cheapest', 'highest rated' questions\n"
        f"  - group_by: for 'average X by Y' or 'most popular brand' questions\n"
        f"You may call multiple tools in sequence if a question needs combined info. "
        f"Be conversational and concise (2-4 sentences). Do not invent facts."
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": q},
    ]

    assistant_text = ""
    tool_calls = []
    try:
        for event in stream_chat_with_tools(messages, TOOL_SCHEMAS, side=side, temperature=0.5):
            if event["type"] == "tool_call":
                args_str = _format_args(event["args"])
                status = f"calling {event['name']}({args_str})"
                tool_calls.append({"name": event["name"], "args": event.get("args", {})})
                yield {"event": "tool_status", "data": status}

            elif event["type"] == "tool_result":
                result = event.get("result")
                if isinstance(result, dict) and result.get("is_chart"):
                    rows = result.get("rows", [])
                    chart = {"type": "bar", "x": "group", "y": "value", "data": rows}
                    yield {"event": "chart", "data": json.dumps(chart)}
                    yield {"event": "tool_status", "data": f"-> {len(rows)} groups returned"}
                else:
                    summary = _format_result_brief(result)
                    yield {"event": "tool_status", "data": f"-> {summary}"}

            elif event["type"] == "token":
                assistant_text += event["data"]
                yield {"event": "token", "data": event["data"]}
                await asyncio.sleep(0)

            elif event["type"] == "done":
                if side == "mongo":
                    chat_history.save_mongo_message(
                        "assistant", assistant_text, tool_calls=tool_calls
                    )
                else:
                    chat_history.save_oracle_message(
                        "assistant", assistant_text, tool_calls=tool_calls
                    )
                yield {"event": "done", "data": "[DONE]"}
                return

    except Exception as e:
        async for evt in _stream_text(f"(LLM error: {type(e).__name__}: {str(e)[:200]})"):
            yield evt


@app.post("/migrate")
async def start_migrate():
    _state["running"] = True
    _state["completed"] = False
    _state["events"] = []
    asyncio.create_task(_run_task())
    return {"status": "started"}


async def _run_task():
    async for event in run_migration():
        _state["events"].append(event)
    _state["running"] = False
    _state["completed"] = True


@app.get("/migrate/stream")
async def migrate_stream(request: Request):
    async def gen():
        seen = 0
        while True:
            if await request.is_disconnected():
                return
            while seen < len(_state["events"]):
                yield {"event": "stage", "data": json.dumps(_state["events"][seen])}
                seen += 1
            if _state["completed"] and seen >= len(_state["events"]):
                yield {"event": "done", "data": "[DONE]"}
                return
            await asyncio.sleep(0.1)

    return EventSourceResponse(gen())
