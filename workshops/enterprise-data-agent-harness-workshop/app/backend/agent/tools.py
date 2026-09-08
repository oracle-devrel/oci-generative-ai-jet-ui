"""Tool registry. Mirrors §10/§11.5/§14 of the notebook.

Each tool is a Python callable; the @register decorator introspects the signature
and embeds the description into the in-DB `toolbox` table for vector retrieval.

Per-turn identity is stashed in `_REQUEST_IDENTITY` (a thread/greenlet local).
`tool_run_sql` reads it before executing so SQL the model constructs is gated
the same way the Data Explorer's REST endpoints are: forbidden tables refuse,
masked columns get [REDACTED], rows outside the identity's regions are dropped.
"""

from __future__ import annotations

import inspect
import json
import re
import threading
import types
import typing

from api.identities import (
    Identity,
    forbid_check_for_sql,
    mask_indices_for,
    region_drop_predicate,
)
from config import (
    AGENT_ID, USER_ID,
    DEMO_USER,
    ONNX_EMBED_DIM, ONNX_EMBED_MODEL,
    TAVILY_API_KEY,
)
from retrieval.scanner import Fact, run_scan, write_facts


# Module-level state — populated on first call to `init_tools()`.
_AGENT_CONN = None
_MEMORY_CLIENT = None
_RERANK = None  # callable(query, candidates, top_k, content_key) -> list[dict]
_SCRATCH = None  # DBFS instance for scratch_write/scratch_read

# Per-turn identity. Set by harness.agent_turn at the start of each user turn,
# cleared in a finally block. threading.local works under eventlet's greenlets
# because each greenlet has its own thread-local namespace.
_REQUEST_IDENTITY = threading.local()


def set_request_identity(identity: "Identity | None") -> None:
    _REQUEST_IDENTITY.value = identity


def get_request_identity() -> "Identity | None":
    return getattr(_REQUEST_IDENTITY, "value", None)


# Per-turn thread id. Used by scratch tools so each thread's working files live
# under /scratch/threads/<thread_id>/<path> and don't bleed across threads.
_REQUEST_THREAD_ID = threading.local()


def set_request_thread_id(thread_id: str | None) -> None:
    _REQUEST_THREAD_ID.value = thread_id


def get_request_thread_id() -> str | None:
    return getattr(_REQUEST_THREAD_ID, "value", None)


# Per-turn socketio reference + sid, so tools can emit ad-hoc events back to
# the originating browser session without us threading them through every
# tool signature.
_REQUEST_SOCKETIO = threading.local()


def set_request_socket(socketio, sid: str | None) -> None:
    _REQUEST_SOCKETIO.value = (socketio, sid)


def get_request_socket() -> tuple:
    return getattr(_REQUEST_SOCKETIO, "value", (None, None))


def _scoped_scratch_path(path: str) -> str:
    """Prepend /threads/<thread_id>/ to a caller-supplied scratch path so
    every thread has its own private scratchpad namespace.

    The DBFS wrapper itself takes care of mounting the path under /scratch.
    """
    tid = get_request_thread_id() or "shared"
    # Strip leading slashes so we don't double-up; treat both 'foo.sql' and
    # '/foo.sql' as relative to this thread's dir.
    rel = path.lstrip("/")
    # If the model accidentally passes a path that already starts with
    # 'threads/<tid>/', leave it alone.
    if rel.startswith(f"threads/{tid}/"):
        return f"/{rel}"
    return f"/threads/{tid}/{rel}"


TOOLS: dict[str, tuple] = {}
ALWAYS_ON_TOOLS = {
    "search_knowledge", "run_sql", "remember", "exec_js", "load_skill",
    "scratch_write", "scratch_append", "scratch_read",
    "search_tavily", "focus_world",
    "fetch_tool_output",
}


# ---- Tavily client (lazy-built so the import doesn't fail when key missing) ---
_TAVILY_CLIENT = None

def _tavily():
    global _TAVILY_CLIENT
    if _TAVILY_CLIENT is None:
        if not TAVILY_API_KEY:
            return None
        try:
            from tavily import TavilyClient
            _TAVILY_CLIENT = TavilyClient(api_key=TAVILY_API_KEY)
        except Exception as e:
            print(f"[tavily] client init failed: {type(e).__name__}: {e}")
            _TAVILY_CLIENT = None
    return _TAVILY_CLIENT


_PRIMS = {int: "integer", float: "number", bool: "boolean", str: "string"}


def _hint_to_json(hint) -> dict:
    origin = typing.get_origin(hint)
    if hint in _PRIMS:
        return {"type": _PRIMS[hint]}
    if origin in (list, typing.List):
        args = typing.get_args(hint) or (str,)
        return {"type": "array", "items": _hint_to_json(args[0])}
    if origin in (dict, typing.Dict):
        return {"type": "object"}
    # typing.Union (typing.Optional[X]) AND PEP-604 X | None (types.UnionType).
    # Both need the same treatment — strip None and recurse if there's exactly
    # one remaining arm.
    if origin is typing.Union or origin is types.UnionType:
        non_none = [a for a in typing.get_args(hint) if a is not type(None)]
        if len(non_none) == 1:
            return _hint_to_json(non_none[0])
    return {"type": "string"}


def _build_schema(fn):
    raw_name = fn.__name__
    name = raw_name[5:] if raw_name.startswith("tool_") else raw_name
    description = (inspect.getdoc(fn) or "").strip()
    if not description:
        raise ValueError(f"tool {name!r} has no docstring; @register needs one for retrieval")
    sig = inspect.signature(fn)
    hints = typing.get_type_hints(fn)
    properties, required = {}, []
    for pname, param in sig.parameters.items():
        prop = _hint_to_json(hints.get(pname, str))
        if param.default is not inspect.Parameter.empty and param.default is not None:
            prop["default"] = param.default
        else:
            required.append(pname)
        properties[pname] = prop
    parameters = {"type": "object", "properties": properties, "required": required}
    openai_schema = {
        "type": "function",
        "function": {"name": name, "description": description, "parameters": parameters},
    }
    return name, description, parameters, openai_schema


def register(fn):
    """Add a tool to the registry and the in-DB `toolbox` table for retrieval."""
    name, description, parameters, openai_schema = _build_schema(fn)
    TOOLS[name] = (fn, openai_schema)
    arg_text = " ".join(parameters["properties"].keys())
    embed_text = f"{name}: {description}\nargs: {arg_text}"

    with _AGENT_CONN.cursor() as cur:
        cur.execute(
            "MERGE INTO toolbox t USING (SELECT :tn AS n FROM dual) s ON (t.name = s.n) "
            "WHEN MATCHED THEN UPDATE SET description = :td, parameters = :tp, "
            f"                              embedding = VECTOR_EMBEDDING({ONNX_EMBED_MODEL} USING :etext AS DATA), "
            "                              updated_at = CURRENT_TIMESTAMP "
            "WHEN NOT MATCHED THEN INSERT (name, description, parameters, embedding) "
            f"                       VALUES (:tn, :td, :tp, VECTOR_EMBEDDING({ONNX_EMBED_MODEL} USING :etext AS DATA))",
            tn=name, td=description, tp=json.dumps(parameters), etext=embed_text,
        )
    _AGENT_CONN.commit()
    return fn


# ============================================================
# DDL: toolbox + skillbox tables (idempotent)
# ============================================================
_TOOLBOX_DDL = [
    (
        "CREATE TABLE toolbox ("
        "  name        VARCHAR2(128) PRIMARY KEY,"
        "  description CLOB NOT NULL,"
        "  parameters  JSON,"
        f" embedding   VECTOR({ONNX_EMBED_DIM}, FLOAT32),"
        "  updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
        ")"
    ),
    (
        "CREATE VECTOR INDEX toolbox_emb_v ON toolbox(embedding) "
        "ORGANIZATION INMEMORY NEIGHBOR GRAPH DISTANCE COSINE"
    ),
]


def ensure_toolbox(agent_conn):
    import oracledb
    with agent_conn.cursor() as cur:
        for stmt in _TOOLBOX_DDL:
            try:
                cur.execute(stmt)
            except oracledb.DatabaseError as e:
                if e.args[0].code in (955, 1408):
                    continue
                if e.args[0].code == 51962:
                    print("WARN: vector_memory_size = 0 — HNSW on toolbox not created.")
                    continue
                raise
    agent_conn.commit()


# ============================================================
# Tool implementations
# ============================================================
_READ_ONLY = re.compile(r"^\s*(select|with)\b", re.IGNORECASE)


def _retrieve_knowledge(query: str, k: int = 5, kinds=None) -> list[dict]:
    """Cosine + rerank over OAMP memories. Filters out tool-output kind.

    OAM.search returns SearchResult wrappers — `.content` is the body, `.record`
    is the underlying MemoryRecord which carries `.metadata`. The keyword is
    `max_results`, NOT `limit`.

    `kinds` is documented as list[str] | None, but LLMs sometimes pass a
    comma-separated string instead. Coerce defensively.
    """
    # Coerce string -> list[str] (the LLM occasionally hands us "table,column").
    if isinstance(kinds, str):
        kinds = [s.strip() for s in kinds.split(",") if s.strip()]
    if kinds is not None and not isinstance(kinds, list):
        kinds = None
    if kinds == []:
        kinds = None

    raw_results = _MEMORY_CLIENT.search(
        query=query,
        user_id=USER_ID, agent_id=AGENT_ID,
        max_results=k * 4,
    )
    candidates = []
    for r in raw_results or []:
        rec = getattr(r, "record", None)
        meta = (getattr(rec, "metadata", None) if rec else None) or {}
        kind_value = meta.get("kind")
        if kind_value == "tool_output":
            continue
        # Only filter when kinds is set AND the candidate has a 'kind' to match.
        if kinds is not None:
            if kind_value is None or kind_value not in kinds:
                continue
        body = getattr(r, "content", "") or ""
        if hasattr(body, "read"):
            body = body.read()
        candidates.append({
            "kind": kind_value or "memory",
            "subject": meta.get("subject", ""),
            "body": str(body),
            "metadata": meta,
        })
    if _RERANK:
        return _RERANK(query, candidates, top_k=k, content_key="body")
    return candidates[:k]


# Duality views are JSON projections over multiple base tables. Forbidding any
# of those base tables for the active identity means the view itself shouldn't
# be readable, since it'd otherwise leak the forbidden child rows.
_DUALITY_VIEW_TABLES = {
    "voyage_dv":  {"SUPPLYCHAIN.VOYAGES", "SUPPLYCHAIN.CONTAINERS",
                   "SUPPLYCHAIN.CARGO_ITEMS", "SUPPLYCHAIN.VESSELS",
                   "SUPPLYCHAIN.PORTS", "SUPPLYCHAIN.CARRIERS"},
    "vessel_dv":  {"SUPPLYCHAIN.VESSELS", "SUPPLYCHAIN.CARRIERS",
                   "SUPPLYCHAIN.VESSEL_POSITIONS"},
}


# Hard-coded centroids for ocean regions — used by tool_focus_world when the
# user asks for a region like 'MEDITERRANEAN' (no row in SUPPLYCHAIN.ports
# we can lat/lng).
_REGION_CENTROIDS = {
    "PACIFIC":       (10.0, -160.0, 2.6),
    "ATLANTIC":      (20.0,  -40.0, 2.6),
    "INDIAN":        (-10.0,  80.0, 2.6),
    "MEDITERRANEAN": ( 38.0,  17.0, 2.0),
}


def _resolve_world_target(kind: str, target: str):
    """Look up a world-view target (vessel name, container_no, port code,
    carrier name, or ocean region) and return {lat, lng, label, ...} for the
    front-end globe camera. Returns None when nothing matches.
    """
    target = target.strip()
    needle = f"%{target.lower()}%"

    if kind == "region":
        c = _REGION_CENTROIDS.get(target.upper())
        if not c:
            return None
        return {"lat": c[0], "lng": c[1], "label": target.upper(),
                "ocean_region": target.upper(),
                "metadata": {"altitude_hint": c[2]}}

    if kind == "port":
        with _AGENT_CONN.cursor() as cur:
            cur.execute(
                f"SELECT port_code, name, country, ocean_region, latitude, longitude "
                f"  FROM {DEMO_USER}.ports "
                f" WHERE LOWER(port_code) = :exact OR LOWER(name) LIKE :needle "
                f"    OR LOWER(country) LIKE :needle "
                f" ORDER BY CASE WHEN LOWER(port_code) = :exact THEN 0 ELSE 1 END "
                f" FETCH FIRST 1 ROWS ONLY",
                exact=target.lower(), needle=needle,
            )
            row = cur.fetchone()
        if not row:
            return None
        code, name, country, region, lat, lng = row
        return {"lat": float(lat), "lng": float(lng),
                "label": f"{name} ({code})", "ocean_region": region,
                "metadata": {"port_code": code, "country": country}}

    if kind == "vessel":
        with _AGENT_CONN.cursor() as cur:
            cur.execute(
                f"SELECT ve.vessel_id, ve.name, ca.name, p.latitude, p.longitude "
                f"  FROM {DEMO_USER}.vessels ve "
                f"  JOIN {DEMO_USER}.carriers ca ON ca.carrier_id = ve.carrier_id "
                f"  JOIN {DEMO_USER}.vessel_positions p ON p.vessel_id = ve.vessel_id "
                f" WHERE LOWER(ve.name) LIKE :needle "
                f"    OR LOWER(ve.imo_number) LIKE :needle "
                f" FETCH FIRST 1 ROWS ONLY",
                needle=needle,
            )
            row = cur.fetchone()
        if not row:
            return None
        vid, name, carrier, lat, lng = row
        return {"lat": float(lat), "lng": float(lng),
                "label": f"{name} (vessel)",
                "metadata": {"vessel_id": int(vid), "carrier": carrier}}

    if kind == "container":
        with _AGENT_CONN.cursor() as cur:
            cur.execute(
                f"SELECT c.container_id, c.container_no, ve.name, "
                f"       v.ocean_region, p.latitude, p.longitude "
                f"  FROM {DEMO_USER}.containers c "
                f"  JOIN {DEMO_USER}.voyages v ON v.voyage_id = c.voyage_id "
                f"  JOIN {DEMO_USER}.vessels ve ON ve.vessel_id = v.vessel_id "
                f"  LEFT JOIN {DEMO_USER}.vessel_positions p ON p.vessel_id = v.vessel_id "
                f" WHERE LOWER(c.container_no) LIKE :needle "
                f"   AND p.latitude IS NOT NULL "
                f" FETCH FIRST 1 ROWS ONLY",
                needle=needle,
            )
            row = cur.fetchone()
        if not row:
            return None
        cid, cno, vessel, region, lat, lng = row
        return {"lat": float(lat), "lng": float(lng),
                "label": f"{cno} on {vessel}", "ocean_region": region,
                "metadata": {"container_id": int(cid), "vessel": vessel}}

    if kind == "carrier":
        # Carriers don't have a sensible single lat/lng (HQ country), so we
        # pick the most recent vessel position belonging to this carrier.
        with _AGENT_CONN.cursor() as cur:
            cur.execute(
                f"SELECT ca.name, ve.name, p.latitude, p.longitude "
                f"  FROM {DEMO_USER}.carriers ca "
                f"  JOIN {DEMO_USER}.vessels ve ON ve.carrier_id = ca.carrier_id "
                f"  JOIN {DEMO_USER}.vessel_positions p ON p.vessel_id = ve.vessel_id "
                f" WHERE LOWER(ca.name) LIKE :needle "
                f"   AND p.latitude IS NOT NULL "
                f" ORDER BY p.position_ts DESC NULLS LAST "
                f" FETCH FIRST 1 ROWS ONLY",
                needle=needle,
            )
            row = cur.fetchone()
        if not row:
            return None
        carrier, vessel, lat, lng = row
        return {"lat": float(lat), "lng": float(lng),
                "label": f"{carrier} → {vessel}",
                "metadata": {"carrier": carrier, "anchor_vessel": vessel}}

    return None


def _duality_forbid_check(view: str) -> str | None:
    """Return a denial message if any of `view`'s underlying tables is
    forbidden for the active identity. None when the view is allowed.
    """
    identity = get_request_identity()
    if identity is None:
        return None
    forbidden = set(identity.forbid_tables) & _DUALITY_VIEW_TABLES.get(view, set())
    if not forbidden:
        return None
    return (
        f"Authorization denied: identity {identity.id!r} ({identity.label}, "
        f"clearance={identity.clearance}) cannot read JSON Duality view {view!r} "
        f"because it projects from forbidden table(s): {', '.join(sorted(forbidden))}. "
        f"Switch to an identity such as 'cfo' (EXECUTIVE clearance) to read this view."
    )


def init_tools(agent_conn, memory_client, rerank=None, scratch=None):
    """Wire the module-level globals and register every tool."""
    global _AGENT_CONN, _MEMORY_CLIENT, _RERANK, _SCRATCH
    _AGENT_CONN = agent_conn
    _MEMORY_CLIENT = memory_client
    _RERANK = rerank
    _SCRATCH = scratch
    ensure_toolbox(agent_conn)

    # Drop and re-register so re-runs pick up doc changes.
    TOOLS.clear()

    @register
    def tool_search_knowledge(query: str, k: int = 5, kinds: list[str] | None = None) -> str:
        """Search institutional knowledge (what the agent has learned about the target database) by semantic similarity.
        Use this BEFORE running SQL to discover which tables and columns are relevant.
        `kinds` is an optional filter: table, column, relationship, query_pattern, correction.
        """
        hits = _retrieve_knowledge(query, k=k, kinds=kinds)
        for h in hits:
            h["body"] = h["body"][:500]
        return json.dumps(hits)

    @register
    def tool_run_sql(sql: str, max_rows: int = 50) -> str:
        """Execute a READ-ONLY SQL statement (SELECT/WITH only) against the target Oracle AI Database
        and return up to `max_rows` rows as JSON.

        Identity-gated: the active "Use As" persona's authorization rules apply.
        Forbidden tables refuse with a clear error naming the missing role/clearance;
        masked columns return as "[REDACTED]"; rows whose ocean_region falls outside
        the identity's authorized regions are dropped post-fetch. Quote table names
        as SCHEMA.TABLE so the forbid-check can see them.
        """
        if not _READ_ONLY.match(sql.strip()):
            return json.dumps({"error": "only SELECT / WITH statements are allowed"})

        identity = get_request_identity()

        # 1. Pre-execution: refuse SQL that touches a forbidden table.
        if identity is not None:
            denial = forbid_check_for_sql(identity, sql)
            if denial:
                return json.dumps({
                    "error": denial,
                    "identity": {
                        "id": identity.id,
                        "label": identity.label,
                        "clearance": identity.clearance,
                        "forbid_tables": list(identity.forbid_tables),
                    },
                })

        try:
            with _AGENT_CONN.cursor() as cur:
                cur.execute(sql)
                cols = [d[0] for d in cur.description]
                raw_rows = []
                for i, r in enumerate(cur):
                    if i >= max_rows:
                        break
                    raw_rows.append([(v.read() if hasattr(v, "read") else v) for v in r])
        except Exception as e:
            return json.dumps({"error": str(e)})

        notes: list[str] = []
        rows = raw_rows

        if identity is not None:
            # 2. Post-fetch: drop rows whose OCEAN_REGION isn't authorized.
            keep = region_drop_predicate(identity)
            kept = [r for r in rows if keep(r, cols)]
            dropped = len(rows) - len(kept)
            rows = kept
            if dropped:
                notes.append(
                    f"{dropped} row(s) dropped because their ocean_region "
                    f"is outside the {identity.id!r} authorized list "
                    f"({', '.join(identity.regions or [])})."
                )

            # 3. Post-fetch: redact column values flagged in the identity's mask
            #    list. We try the cursor's bare column names AND a SCHEMA.TABLE.COL
            #    prefix matched by simple heuristics — for unqualified queries the
            #    bare name is the best we can do and we'll only catch column names
            #    whose mask is registered without a prefix.
            #
            #    To keep this robust, we ALSO match by suffix: if a mask entry
            #    ends with ".<COL>", a bare column with that exact name is
            #    treated as masked. False positives across schemas are unlikely
            #    in this demo.
            mask_idx = {}
            mask_suffixes = {m.split(".")[-1].upper(): m for m in identity.mask_cols}
            for i, c in enumerate(cols):
                if c.upper() in mask_suffixes:
                    mask_idx[i] = mask_suffixes[c.upper()]
            if mask_idx:
                masked_rows = []
                for r in rows:
                    nr = list(r)
                    for j in mask_idx:
                        nr[j] = "[REDACTED]"
                    masked_rows.append(nr)
                rows = masked_rows
                notes.append(
                    f"Columns redacted by {identity.id!r}: "
                    + ", ".join(sorted(set(mask_idx.values())))
                )

        out = {"columns": cols, "rows": rows, "row_count": len(rows)}
        if identity is not None:
            out["identity"] = {
                "id": identity.id,
                "label": identity.label,
                "clearance": identity.clearance,
                "regions": identity.regions,
            }
        if notes:
            out["authorization_notes"] = notes
        return json.dumps(out, default=str)

    @register
    def tool_remember(subject: str, body: str, kind: str = "correction") -> str:
        """Persist a correction or learning into institutional knowledge so future turns benefit.
        Use when the user corrects you, or when you discover a non-obvious fact that future retrievals should surface.

        Memories written here are globally retrievable (search_knowledge can
        find them from any thread) but they are tagged with the thread_id
        they were first written on, so you can trace provenance.

        `subject` is a short label (e.g. 'SALES.ORDERS.total_cents'); `body` is the fact written as a full sentence.
        """
        tid = get_request_thread_id()
        fact = Fact(
            kind=kind, subject=subject, body=body,
            metadata={"source": "agent_remember"},
        )
        result = write_facts(_MEMORY_CLIENT, [fact], thread_id=tid)
        return json.dumps({"ok": True, "origin_thread_id": tid, **result})

    @register
    def tool_scan_database(owner: str) -> str:
        """Scan the specified schema of the target Oracle AI Database and update institutional knowledge.
        Run this when the user asks about a schema you have never seen.
        `owner` is the schema owner (e.g. 'DEMO').
        """
        return json.dumps(run_scan(_AGENT_CONN, _MEMORY_CLIENT, owner))

    @register
    def tool_exec_js(code: str) -> str:
        """Execute JavaScript inside Oracle MLE (no filesystem, no network).
        Good for arithmetic, string formatting, JSON reshaping, simple aggregations.
        `console.log(...)` output comes back as `stdout`.
        """
        from agent.mle import exec_js
        return json.dumps(exec_js(_AGENT_CONN, code))

    @register
    def tool_scratch_write(path: str, content: str) -> str:
        """OVERWRITE a DBFS scratchpad file with `content` (POSIX-style file
        write — replaces any prior content at that path). Use for SQL drafts,
        evolving plans, or anything where the latest version is the truth.

        For ADDING to a running log without losing prior entries, use
        `scratch_append` instead.

        `path` is RELATIVE to your thread's private scratchpad — e.g.
        'voyages.sql' becomes '/scratch/threads/<this_thread>/voyages.sql' on
        disk. Other threads cannot read or overwrite your files.
        """
        if _SCRATCH is None:
            return json.dumps({"error": "scratchpad not configured on this backend"})
        try:
            scoped = _scoped_scratch_path(path)
            _SCRATCH.write(scoped, content)
            return json.dumps({"ok": True, "path": scoped,
                               "thread_id": get_request_thread_id() or "shared",
                               "bytes": len(content)})
        except Exception as e:
            return json.dumps({"error": f"{type(e).__name__}: {e}"})

    @register
    def tool_scratch_append(path: str, content: str) -> str:
        """Append text to the end of a DBFS scratchpad file (or create it).
        Use this instead of `scratch_write` when you want to ADD to a running
        log without losing previous entries — e.g. findings.md as you discover
        facts across multiple turns, or transcript.md.

        For SQL drafts, plans, or any 'latest version is the truth' content,
        prefer `scratch_write` (overwrite).

        `path` is RELATIVE to your thread's private scratchpad (see
        scratch_write).
        """
        if _SCRATCH is None:
            return json.dumps({"error": "scratchpad not configured on this backend"})
        try:
            scoped = _scoped_scratch_path(path)
            _SCRATCH.append(scoped, content)
            return json.dumps({"ok": True, "path": scoped,
                               "thread_id": get_request_thread_id() or "shared",
                               "appended_bytes": len(content)})
        except Exception as e:
            return json.dumps({"error": f"{type(e).__name__}: {e}"})

    @register
    def tool_scratch_read(path: str) -> str:
        """Read a previously-written file from your thread's scratchpad.
        Returns the content as a string, or an error if the path doesn't exist.
        Resolves to /scratch/threads/<this_thread>/<path>.
        """
        if _SCRATCH is None:
            return json.dumps({"error": "scratchpad not configured on this backend"})
        try:
            scoped = _scoped_scratch_path(path)
            return json.dumps({"content": _SCRATCH.read(scoped),
                               "path": scoped,
                               "thread_id": get_request_thread_id() or "shared"})
        except FileNotFoundError:
            return json.dumps({"error": f"not found: {_scoped_scratch_path(path)}"})
        except Exception as e:
            return json.dumps({"error": f"{type(e).__name__}: {e}"})

    @register
    def tool_load_skill(name: str) -> str:
        """Load the full content of a named skill from the skillbox.
        Use this when the system prompt's "Available skills" manifest lists a skill
        relevant to the current task. The full markdown guide is returned and you
        should follow its instructions for the duration of the task.
        `name` is the full namespace, e.g. "agent/schema-discovery".
        """
        with _AGENT_CONN.cursor() as cur:
            cur.execute(
                "SELECT description, body, source_url, category FROM skillbox WHERE name = :n",
                n=name,
            )
            row = cur.fetchone()
        if not row:
            return json.dumps({"error": f"no skill named {name!r}; call list_skills(query) to find available skills"})
        desc, body, url, category = row
        body_text = body.read() if hasattr(body, "read") else str(body or "")
        return json.dumps({
            "name": name, "category": category,
            "description": desc, "source_url": url,
            "body": body_text,
        })

    @register
    def tool_list_skills(query: str, k: int = 5) -> str:
        """Search the skillbox semantically. Returns top-k skills (name + description).
        Use when the system prompt's manifest didn't surface the right skill.
        """
        with _AGENT_CONN.cursor() as cur:
            cur.execute(
                "SELECT name, category, description FROM skillbox "
                f" ORDER BY VECTOR_DISTANCE(embedding, VECTOR_EMBEDDING({ONNX_EMBED_MODEL} USING :q AS DATA), COSINE) "
                " FETCH FIRST :k ROWS ONLY",
                q=query, k=k,
            )
            hits = [{"name": n, "category": c, "description": d} for n, c, d in cur]
        return json.dumps(hits)

    @register
    def tool_get_document(view: str, key: str) -> str:
        """Read one full document from a JSON Relational Duality View by primary key.
        Use this instead of writing JOINs whenever you need the full shape of an entity
        (a voyage with its vessel/carrier/ports/containers/cargo, or a vessel with its
        carrier/position). Returns a JSON document.

        Identity-gated: if the active "Use As" persona is forbidden from any of the
        underlying tables the view projects, the call refuses with a clear error.

        `view` must be one of: voyage_dv, vessel_dv.
        `key` is the value of the document _id (numeric voyage_id or vessel_id, as a string).
        """
        from config import DEMO_USER
        allowed = {"voyage_dv", "vessel_dv"}
        if view not in allowed:
            return json.dumps({"error": f"unknown view {view!r}; allowed: {sorted(allowed)}"})

        denial = _duality_forbid_check(view)
        if denial:
            return json.dumps({"error": denial})
        try:
            with _AGENT_CONN.cursor() as cur:
                cur.execute(
                    f'SELECT JSON_SERIALIZE(data PRETTY) FROM {DEMO_USER}.{view} '
                    f"WHERE JSON_VALUE(data, '$._id') = :k",
                    k=int(key) if str(key).isdigit() else key,
                )
                row = cur.fetchone()
            if not row:
                return json.dumps({"error": f"no document with _id={key} in {view}"})
            body = row[0].read() if hasattr(row[0], "read") else str(row[0])
            return body
        except Exception as e:
            return json.dumps({"error": f"{type(e).__name__}: {e}"})

    @register
    def tool_query_documents(view: str, where: str = "1=1", max_rows: int = 10) -> str:
        """Filter a JSON Relational Duality View with a SQL predicate.
        Use when you want a list of documents matching some condition without writing
        JOINs by hand. The predicate references underlying-table columns of the view's
        root table (e.g. status, ocean_region for voyage_dv; vessel_type for vessel_dv).

        Identity-gated: same forbid-table check as `get_document`.

        `view` must be one of: voyage_dv, vessel_dv.
        `where` is a SQL boolean expression on the root table's columns (default '1=1').
        `max_rows` caps the result set.
        """
        from config import DEMO_USER
        allowed = {"voyage_dv", "vessel_dv"}
        if view not in allowed:
            return json.dumps({"error": f"unknown view {view!r}; allowed: {sorted(allowed)}"})

        denial = _duality_forbid_check(view)
        if denial:
            return json.dumps({"error": denial})
        sql = (f"SELECT JSON_SERIALIZE(data) FROM {DEMO_USER}.{view} "
               f" WHERE {where} FETCH FIRST :n ROWS ONLY")
        try:
            with _AGENT_CONN.cursor() as cur:
                cur.execute(sql, n=max_rows)
                docs = [(r[0].read() if hasattr(r[0], "read") else str(r[0])) for r in cur]
            return json.dumps({"count": len(docs), "documents": [json.loads(d) for d in docs]},
                              default=str)
        except Exception as e:
            return json.dumps({"error": f"{type(e).__name__}: {e}", "sql": sql})

    @register
    def tool_fetch_tool_output(tool_call_id: str) -> str:
        """Recover the full, untruncated output of a previous tool call.

        Use this when a tool result in your context was inlined as a 600-byte
        preview ending with `...[+N bytes; full: fetch_tool_output(tool_call_id=...)]`
        and you need the missing bytes to answer. The full output was offloaded
        to OAMP at dispatch time and is keyed by `tool_call_id`.
        """
        rows = _MEMORY_CLIENT._store.list(
            "memory",
            user_id=USER_ID, agent_id=AGENT_ID,
            metadata_filter={"kind": "tool_output", "tool_call_id": tool_call_id},
            limit=1,
        )
        if not rows:
            return json.dumps({"error": f"no tool output found for tool_call_id={tool_call_id!r}"})
        rec = rows[0]
        meta = getattr(rec, "metadata", None) or {}
        body = getattr(rec, "content", "") or ""
        if hasattr(body, "read"):
            body = body.read()
        return json.dumps({
            "tool_call_id": tool_call_id,
            "tool_name": meta.get("tool_name"),
            "tool_args": meta.get("tool_args"),
            "tool_output": str(body),
        })

    @register
    def tool_search_tavily(query: str, max_results: int = 5, topic: str = "general") -> str:
        """Search the live web for real-time news, breaking events, weather,
        port closures, geopolitical disruptions, anything time-sensitive that
        the database doesn't carry. Backed by Tavily's AI-optimised search API.

        Use this when the user asks about CURRENT events ("what's happening
        with X right now?", "any disruptions affecting Y?", "news about Z"),
        or when you need to ground a SUPPLYCHAIN answer in something happening
        in the real world right now (e.g. "what vessels are affected by
        current news?" — search the news for events, then cross-reference
        SUPPLYCHAIN.voyages / vessels via run_sql).

        Each result is also persisted to OAMP institutional knowledge tagged
        kind='web_search' so future turns can retrieve it via
        `search_knowledge` without re-searching.

        `query` — free-text search.
        `max_results` — 1 to 10, default 5.
        `topic` — 'general' or 'news' (Tavily's news topic filters to recent
        articles; use it for time-sensitive enterprise questions).
        """
        client = _tavily()
        if client is None:
            return json.dumps({
                "error": "TAVILY_API_KEY not set on this backend; web search disabled.",
            })
        max_results = max(1, min(int(max_results or 5), 10))
        topic = "news" if str(topic).lower() == "news" else "general"
        try:
            response = client.search(query=query, max_results=max_results, topic=topic)
        except Exception as e:
            return json.dumps({"error": f"Tavily search failed: {type(e).__name__}: {e}"})
        results = response.get("results", []) or []
        from datetime import datetime, timezone
        ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
        # Persist each result as a memory tagged kind='web_search' so the
        # agent (or a future turn on a different thread) can pull them back
        # via search_knowledge without re-querying Tavily.
        tid = get_request_thread_id()
        try:
            for r in results:
                title = r.get("title") or ""
                content = r.get("content") or ""
                url = r.get("url") or ""
                text = f"Title: {title}\nContent: {content}\nURL: {url}"
                meta = {
                    "kind": "web_search",
                    "subject": title[:200],
                    "url": url, "score": r.get("score"),
                    "source": "tavily", "topic": topic,
                    "query": query, "fetched_at": ts,
                }
                if tid:
                    meta["origin_thread_id"] = tid
                base = dict(user_id=USER_ID, agent_id=AGENT_ID, metadata=meta)
                try:
                    if tid:
                        _MEMORY_CLIENT.add_memory(text, thread_id=tid, **base)
                    else:
                        _MEMORY_CLIENT.add_memory(text, **base)
                except ValueError:
                    # Thread not registered yet (e.g. first turn fired before
                    # add_messages). Persist globally so the result still
                    # lands in institutional knowledge — search_knowledge can
                    # find it on any future thread.
                    _MEMORY_CLIENT.add_memory(text, **base)
        except Exception as e:
            print(f"[search_tavily] OAMP persist failed: {type(e).__name__}: {e}")

        return json.dumps({
            "query": query, "topic": topic,
            "count": len(results),
            "fetched_at": ts,
            "results": [{
                "title": r.get("title", ""),
                "content": (r.get("content") or "")[:600],
                "url": r.get("url", ""),
                "score": r.get("score"),
            } for r in results],
        }, default=str)

    @register
    def tool_focus_world(target_kind: str, target: str, altitude: float = 1.5) -> str:
        """Drive the World Explorer globe from chat — fly the camera to a
        vessel, container, port, carrier, or ocean region.

        Use this whenever the user says things like:
          - "show me MAERSK EDINBURGH on the globe"
          - "fly to Singapore"
          - "highlight container MSCU6634586"
          - "zoom to the Mediterranean"

        `target_kind` — one of: vessel, container, port, carrier, region.
        `target`      — the entity name / code / region label, e.g.
                        'Maersk Edinburgh', 'MSCU6634586', 'SGSIN',
                        'MEDITERRANEAN'.
        `altitude`    — globe camera altitude (1.0 = close, 2.5 = global view).
        """
        sock, sid = get_request_socket()
        kind = (target_kind or "").strip().lower()
        if kind not in ("vessel", "container", "port", "carrier", "region"):
            return json.dumps({"error": f"unknown target_kind {target_kind!r}; "
                              "must be one of vessel|container|port|carrier|region"})
        target = (target or "").strip()
        if not target:
            return json.dumps({"error": "target is required"})

        # Resolve the target to (lat, lng) using the same SQL the world
        # search endpoint uses. Region targets fall back to a hard-coded
        # centroid table.
        try:
            anchor = _resolve_world_target(kind, target)
        except Exception as e:
            return json.dumps({"error": f"resolve failed: {type(e).__name__}: {e}"})
        if anchor is None:
            return json.dumps({"error": f"no {kind} found matching {target!r}"})

        payload = {
            "kind": kind,
            "target": target,
            "lat": anchor["lat"],
            "lng": anchor["lng"],
            "altitude": max(0.6, min(float(altitude or 1.5), 4.0)),
            "label": anchor.get("label", target),
            "region": anchor.get("ocean_region"),
            "metadata": anchor.get("metadata", {}),
        }
        if sock is not None:
            try:
                if sid:
                    sock.emit("focus_world", payload, room=sid)
                else:
                    sock.emit("focus_world", payload)
            except Exception as e:
                print(f"[focus_world] emit failed: {type(e).__name__}: {e}")
        return json.dumps({"ok": True, **payload})

    return TOOLS


def retrieve_tools(query: str, k: int = 6) -> list[dict]:
    """Top-k tool schemas for `query`, plus the always-on set."""
    cosine_fetch = k * 4
    rows: list[dict] = []
    with _AGENT_CONN.cursor() as cur:
        cur.execute(
            "SELECT name, description FROM toolbox "
            f" ORDER BY VECTOR_DISTANCE(embedding, VECTOR_EMBEDDING({ONNX_EMBED_MODEL} USING :q AS DATA), COSINE) "
            " FETCH FIRST :k ROWS ONLY",
            q=query, k=cosine_fetch,
        )
        for name, desc in cur:
            desc_text = desc.read() if hasattr(desc, "read") else str(desc or "")
            rows.append({"name": name, "content": desc_text})

    if _RERANK:
        ranked = _RERANK(query, rows, top_k=k, content_key="content")
    else:
        ranked = rows[:k]

    schemas: dict[str, dict] = {}
    for r in ranked:
        if r["name"] in TOOLS:
            schemas[r["name"]] = TOOLS[r["name"]][1]
    for name in ALWAYS_ON_TOOLS:
        if name in TOOLS:
            schemas[name] = TOOLS[name][1]
    return list(schemas.values())
