"""Tool registry. Mirrors §10/§11.5/§14 of the notebook.

Each tool is a Python callable; the @register decorator introspects the signature
and embeds the description into the in-DB `toolbox` table for vector retrieval.

Per-turn identity is stashed in `_REQUEST_IDENTITY` (a thread-local).
`tool_run_sql` reads it before executing so SQL the model constructs is gated
the same way the Data Explorer's REST endpoints are: forbidden tables refuse,
masked columns get [REDACTED], rows outside the identity's regions are dropped.
"""

from __future__ import annotations

import contextlib
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
    normalize_sql,
    region_drop_predicate,
)
from config import (
    AGENT_ID, USER_ID,
    DEMO_USER,
    ONNX_EMBED_DIM, ONNX_EMBED_MODEL,
    TAVILY_API_KEY,
)
from retrieval.scanner import Fact, run_scan, write_facts
from db.deep_security import identity_session
from memory.manager import (
    INVALIDATING_LINK_TYPES,
    LINK_TYPES,
    content_to_text,
    find_memory,
    link_memories,
)


# Module-level state — populated on first call to `init_tools()`.
_AGENT_CONN = None
_MEMORY_CLIENT = None
_RERANK = None  # callable(query, candidates, top_k, content_key) -> list[dict]
_SCRATCH = None  # DBFS instance for scratch_write/scratch_read

# Per-turn identity. Set by harness.agent_turn at the start of each user turn,
# cleared in a finally block. Each turn runs on its own OS thread (Socket.IO
# threading mode), so threading.local isolates concurrent turns.
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
    "search_knowledge", "run_sql", "remember", "link_memories", "exec_js",
    "load_skill",
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

# Things a regex cannot see through: packages that run a SQL string of their
# own (so the table checks never see it) or reach outside the database, and
# inline PL/SQL (`WITH FUNCTION ...`). Refused outright. DML and row locks are
# not on this list — the session is READ ONLY, so the database refuses them.
_UNSAFE_SQL = re.compile(
    r"\b(dbms_xmlgen|dbms_xmlquery|dbms_sql|dbms_scheduler|dbms_job|dbms_pipe|"
    r"dbms_lock|dbms_session|dbms_rls|dbms_mle|dbms_dbfs\w*|dbms_java\w*|"
    r"utl_http|utl_tcp|utl_smtp|utl_file|utl_inaddr|utl_mail)\b"
    r"|\bwith\s+(function|procedure)\b",
    re.IGNORECASE,
)


def _sql_denial(sql: str, identity: "Identity | None") -> str | None:
    """Why this SQL (or SQL fragment) must not run, or None. Shared by run_sql
    and the query_documents predicate so neither is a back door to the other."""
    m = _UNSAFE_SQL.search(normalize_sql(sql)) or _UNSAFE_SQL.search(sql)
    if m:
        return (f"{m.group(0).strip()!r} is not allowed in agent SQL: it can run SQL "
                "that bypasses the table checks. Use plain SELECT/WITH over tables.")
    if identity is not None:
        return forbid_check_for_sql(identity, sql)
    return None


def _retrieve_knowledge(query: str, k: int = 5, kinds=None,
                        follow_links: bool = False) -> list[dict]:
    """Cosine + rerank over OAMP memories. Filters out tool-output kind.

    OAM.search returns SearchResult wrappers — `.content` is the body, `.record`
    is the underlying MemoryRecord which carries `.metadata`. The keyword is
    `max_results`, NOT `limit`.

    `kinds` is documented as list[str] | None, but LLMs sometimes pass a
    comma-separated string instead. Coerce defensively.

    INVALID memories (superseded/refined/duplicated) are excluded from direct
    hits: after a correction, the old fact should not be retrieved as current
    truth. `follow_links=True` asks OAMP for one hop of linked context, which
    *does* include those retired versions — that is how history stays visible.
    """
    # Coerce string -> list[str] (the LLM occasionally hands us "table,column").
    if isinstance(kinds, str):
        kinds = [s.strip() for s in kinds.split(",") if s.strip()]
    if kinds is not None and not isinstance(kinds, list):
        kinds = None
    if kinds == []:
        kinds = None

    link_kwargs = {"num_hops": 1, "max_linked_results": 20} if follow_links else {}
    raw_results = _MEMORY_CLIENT.search(
        query=query,
        user_id=USER_ID, agent_id=AGENT_ID,
        max_results=k * 4,
        include_invalid_results=False,
        **link_kwargs,
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
        body = content_to_text(getattr(r, "content", ""))
        links = []
        if follow_links:
            direct_id = getattr(r, "id", None) or getattr(rec, "id", None)
            for rel, linked in (getattr(r, "linked_results", None) or []):
                lmeta = getattr(linked, "metadata", None) or {}
                lbody = content_to_text(getattr(linked, "content", ""))
                if rel.source_record_id == direct_id:
                    label, direction = rel.relation_type, "out"
                else:
                    label = rel.opposite_relation_type or rel.relation_type
                    direction = "in"
                links.append({
                    "relation": label,
                    "direction": direction,
                    "status": str(getattr(linked, "status", "")).split(".")[-1],
                    "kind": lmeta.get("kind", "memory"),
                    "subject": lmeta.get("subject", ""),
                    "body": lbody,
                })
        candidates.append({
            "kind": kind_value or "memory",
            "subject": meta.get("subject", ""),
            "body": body,
            "metadata": meta,
            "links": links,
        })
    if _RERANK:
        return _RERANK(query, candidates, top_k=k, content_key="body")
    return candidates[:k]


# Duality views are JSON projections over multiple base tables. Forbidding any
# of those base tables for the active identity means the view itself shouldn't
# be readable, since it'd otherwise leak the forbidden child rows.
_DUALITY_VIEW_TABLES = {
    "account_dv": {"FINANCE.ACCOUNTS", "FINANCE.CUSTOMERS",
                    "FINANCE.BRANCHES", "FINANCE.CARDS",
                    "FINANCE.TRANSACTIONS", "FINANCE.MERCHANTS"},
    "customer_dv": {"FINANCE.CUSTOMERS", "FINANCE.ACCOUNTS",
                     "FINANCE.BRANCHES", "FINANCE.LOANS"},
}


# --------------------------------------------------------------------------- #
# Duality-view fallback
# --------------------------------------------------------------------------- #
# Oracle's JSON Relational Duality View engine cannot read a table that carries
# more than one VPD / DBMS_RLS policy. The kernel-enforced identity (docs/reference/deep-data-security.md) puts
# two policies on FINANCE.ACCOUNTS (a region predicate + a balance mask), three
# on FINANCE.CUSTOMERS, etc. The view DDL then *succeeds* but every SELECT fails
# with ORA-40606 ("Table 'ACCOUNTS' does not have a primary or unique key") —
# a misleading message; the table's PK is intact.
#
# So each duality view is mirrored here as a plain SQL/JSON constructor over the
# same base tables. The database still applies VPD to that query (rows filtered,
# masked columns nulled), so the trust boundary is unchanged — only the
# projection mechanism differs. `get_document`/`query_documents` try the duality
# view first and fall back to these on the incompatibility errors.
_DOC_SQL = {
    "account_dv": {
        "root": "accounts a",
        "pk": "a.account_id",
        "doc": """JSON_OBJECT(
            '_id'          VALUE a.account_id,
            'accountType'  VALUE a.account_type,
            'currency'     VALUE a.currency,
            'balanceCents' VALUE a.balance_cents,
            'status'       VALUE a.status,
            'openedTs'     VALUE a.opened_ts,
            'region'       VALUE (SELECT JSON_OBJECT(
                                  'branchCode' VALUE b.branch_code, 'name' VALUE b.name,
                                  'city' VALUE b.city, 'country' VALUE b.country,
                                  'region' VALUE b.region)
                                FROM __S__.branches b WHERE b.branch_id = a.branch_id),
            'customer'     VALUE (SELECT JSON_OBJECT(
                                  'customerId' VALUE cu.customer_id, 'fullName' VALUE cu.full_name,
                                  'ssn' VALUE cu.ssn, 'segment' VALUE cu.segment,
                                  'riskRating' VALUE cu.risk_rating)
                                FROM __S__.customers cu WHERE cu.customer_id = a.customer_id),
            'cards'        VALUE (SELECT JSON_ARRAYAGG(JSON_OBJECT(
                                  'cardId' VALUE ca.card_id, 'cardType' VALUE ca.card_type,
                                  'cardNumber' VALUE ca.card_number, 'status' VALUE ca.status,
                                  'dailyLimitCents' VALUE ca.daily_limit_cents) RETURNING CLOB)
                                FROM __S__.cards ca WHERE ca.account_id = a.account_id),
            'transactions' VALUE (SELECT JSON_ARRAYAGG(JSON_OBJECT(
                                  'txnId' VALUE t.txn_id, 'txnTs' VALUE t.txn_ts,
                                  'amountCents' VALUE t.amount_cents, 'currency' VALUE t.currency,
                                  'channel' VALUE t.channel, 'txnType' VALUE t.txn_type,
                                  'status' VALUE t.status, 'flagReason' VALUE t.flag_reason,
                                  'region' VALUE t.region,
                                  'merchant' VALUE (SELECT JSON_OBJECT(
                                      'merchantId' VALUE m.merchant_id, 'name' VALUE m.name,
                                      'mccCode' VALUE m.mcc_code, 'category' VALUE m.category,
                                      'country' VALUE m.country)
                                    FROM __S__.merchants m WHERE m.merchant_id = t.merchant_id),
                                  'wireMessage' VALUE (SELECT JSON_OBJECT(
                                      'messageId' VALUE w.message_id, 'senderBic' VALUE w.sender_bic,
                                      'receiverBic' VALUE w.receiver_bic,
                                      'beneficiaryName' VALUE w.beneficiary_name,
                                      'beneficiaryCountry' VALUE w.beneficiary_country,
                                      'purposeCode' VALUE w.purpose_code)
                                    FROM __S__.wire_messages w WHERE w.txn_id = t.txn_id)) RETURNING CLOB)
                                FROM __S__.transactions t WHERE t.account_id = a.account_id)
          )""",
    },
    "customer_dv": {
        "root": "customers cu",
        "pk": "cu.customer_id",
        "doc": """JSON_OBJECT(
            '_id'         VALUE cu.customer_id,
            'fullName'    VALUE cu.full_name,
            'ssn'         VALUE cu.ssn,
            'segment'     VALUE cu.segment,
            'riskRating'  VALUE cu.risk_rating,
            'country'     VALUE cu.country,
            'accounts'    VALUE (SELECT JSON_ARRAYAGG(JSON_OBJECT(
                              'accountId' VALUE a.account_id, 'accountType' VALUE a.account_type,
                              'currency' VALUE a.currency, 'balanceCents' VALUE a.balance_cents,
                              'status' VALUE a.status,
                              'branch' VALUE (SELECT JSON_OBJECT(
                                  'branchCode' VALUE b.branch_code, 'name' VALUE b.name,
                                  'city' VALUE b.city, 'region' VALUE b.region)
                                FROM __S__.branches b WHERE b.branch_id = a.branch_id)) RETURNING CLOB)
                            FROM __S__.accounts a WHERE a.customer_id = cu.customer_id),
            'loans'       VALUE (SELECT JSON_ARRAYAGG(JSON_OBJECT(
                              'loanId' VALUE l.loan_id, 'loanType' VALUE l.loan_type,
                              'amountCents' VALUE l.amount_cents, 'rateBp' VALUE l.rate_bp,
                              'termMonths' VALUE l.term_months, 'status' VALUE l.status) RETURNING CLOB)
                            FROM __S__.loans l WHERE l.customer_id = cu.customer_id),
            'sanctionsScreenings' VALUE (SELECT JSON_ARRAYAGG(JSON_OBJECT(
                              'screeningId' VALUE s.screening_id, 'listType' VALUE s.list_type,
                              'matchScore' VALUE s.match_score, 'disposition' VALUE s.disposition,
                              'screenedTs' VALUE s.screened_ts) RETURNING CLOB)
                            FROM __S__.sanctions_screenings s WHERE s.customer_id = cu.customer_id),
            'kycDocuments' VALUE (SELECT JSON_ARRAYAGG(JSON_OBJECT(
                              'documentId' VALUE d.document_id, 'docType' VALUE d.doc_type,
                              'status' VALUE d.status, 'expiresTs' VALUE d.expires_ts) RETURNING CLOB)
                            FROM __S__.kyc_documents d WHERE d.customer_id = cu.customer_id),
            'beneficialOwners' VALUE (SELECT JSON_ARRAYAGG(JSON_OBJECT(
                              'ownershipId' VALUE o.ownership_id, 'ownerName' VALUE o.owner_name,
                              'ownershipPct' VALUE o.ownership_pct, 'layer' VALUE o.layer,
                              'jurisdiction' VALUE o.jurisdiction) RETURNING CLOB)
                            FROM __S__.beneficial_owners o WHERE o.company_id = cu.customer_id)
          )""",
    },
}

# ORA codes that mean "the duality view can't run here" (VPD conflict / missing
# view / JSON processor). On any of these we fall back to the SQL/JSON builder.
_DV_FALLBACK_CODES = {942, 40606, 40617, 40664, 40666}
_DV_FALLBACK_LOGGED: set[str] = set()


def _dv_error_code(exc) -> int | None:
    try:
        return exc.args[0].code
    except Exception:
        return None


def _lob_text(value) -> str:
    return value.read() if hasattr(value, "read") else str(value)


def _log_dv_fallback_once(view: str, code: int | None) -> None:
    if view in _DV_FALLBACK_LOGGED:
        return
    _DV_FALLBACK_LOGGED.add(view)
    print(f"[tools] {view}: duality view unavailable (ORA-{code}); using the "
          f"direct SQL/JSON document over the base tables (VPD still enforced).")


@contextlib.contextmanager
def _identity_cursor():
    """A cursor on a private READ ONLY session carrying the active persona, so
    the DBMS_RLS policies evaluate the right end-user (see
    db.deep_security.identity_session). Read any LOB before leaving the block."""
    with identity_session(get_request_identity(), read_only=True) as conn:
        with conn.cursor() as cur:
            yield cur


# Hard-coded centroids for bank regions — used by tool_focus_world when the
# user asks for a region like 'EUROPE' (no row in FINANCE.branches we can
# lat/lng directly).
_REGION_CENTROIDS = {
    "AMERICAS":     (38.0, -98.0, 2.6),
    "EUROPE":       (50.0,   8.0, 2.6),
    "MIDDLE_EAST":  (27.0,  45.0, 2.4),
    "ASIA_PACIFIC": (12.0, 105.0, 2.6),
}


def _resolve_world_target(kind: str, target: str):
    """Look up a world-view target (branch name, merchant name, customer name,
    or bank region) and return {lat, lng, label, ...} for the front-end globe
    camera. Returns None when nothing matches.
    """
    target = target.strip()
    needle = f"%{target.lower()}%"

    if kind == "region":
        c = _REGION_CENTROIDS.get(target.upper())
        if not c:
            return None
        return {"lat": c[0], "lng": c[1], "label": target.upper(),
                "region": target.upper(),
                "metadata": {"altitude_hint": c[2]}}

    if kind == "branch":
        with _identity_cursor() as cur:
            cur.execute(
                f"SELECT branch_id, name, city, country, region, latitude, longitude "
                f"  FROM {DEMO_USER}.branches "
                f" WHERE LOWER(branch_code) = :exact OR LOWER(name) LIKE :needle "
                f"    OR LOWER(city) LIKE :needle "
                f" ORDER BY CASE WHEN LOWER(branch_code) = :exact THEN 0 ELSE 1 END "
                f" FETCH FIRST 1 ROWS ONLY",
                exact=target.lower(), needle=needle,
            )
            row = cur.fetchone()
        if not row:
            return None
        bid, name, city, country, region, lat, lng = row
        return {"lat": float(lat), "lng": float(lng),
                "label": f"{name} ({city})", "region": region,
                "metadata": {"branch_id": int(bid), "country": country}}

    if kind == "merchant":
        with _identity_cursor() as cur:
            cur.execute(
                f"SELECT merchant_id, name, category, country, region, latitude, longitude "
                f"  FROM {DEMO_USER}.merchants "
                f" WHERE LOWER(name) LIKE :needle OR LOWER(category) LIKE :needle "
                f" FETCH FIRST 1 ROWS ONLY",
                needle=needle,
            )
            row = cur.fetchone()
        if not row:
            return None
        mid, name, category, country, region, lat, lng = row
        return {"lat": float(lat), "lng": float(lng),
                "label": f"{name} ({category})", "region": region,
                "metadata": {"merchant_id": int(mid), "country": country}}

    if kind == "customer":
        # Anchor the customer at their primary (oldest) account's branch.
        with _identity_cursor() as cur:
            cur.execute(
                f"SELECT cu.customer_id, cu.full_name, b.name, b.city, b.region, "
                f"       b.latitude, b.longitude "
                f"  FROM {DEMO_USER}.customers cu "
                f"  JOIN {DEMO_USER}.accounts a ON a.customer_id = cu.customer_id "
                f"  JOIN {DEMO_USER}.branches b ON b.branch_id = a.branch_id "
                f" WHERE LOWER(cu.full_name) LIKE :needle "
                f" ORDER BY a.opened_ts "
                f" FETCH FIRST 1 ROWS ONLY",
                needle=needle,
            )
            row = cur.fetchone()
        if not row:
            return None
        cid, name, branch_name, city, region, lat, lng = row
        return {"lat": float(lat), "lng": float(lng),
                "label": f"{name} → {branch_name} ({city})", "region": region,
                "metadata": {"customer_id": int(cid), "branch": branch_name}}

    return None


# --------------------------------------------------------------------------- #
# Automatic world-focus inference
# --------------------------------------------------------------------------- #
# The globe should react to what the agent is *doing*, not only to explicit
# focus_world calls. After each data tool runs we try to read a geographic
# anchor out of its arguments / results and stream a `focus_world` event with
# source="auto". Events are deduped and capped per turn so a wide scan can't
# thrash the camera. The front-end can mute auto-focus with an "auto-follow"
# toggle; explicit focus_world calls always land.

_AUTO_FOCUS_MAX = 4  # most automatic camera moves per turn

# Natural-language aliases → canonical bank region. Matched on word boundaries
# so "MENA" doesn't fire inside "amenable".
_REGION_ALIASES = {
    "AMERICAS": "AMERICAS", "AMERICA": "AMERICAS", "AMERICAN": "AMERICAS",
    "NORTH AMERICA": "AMERICAS", "LATAM": "AMERICAS",
    "EUROPE": "EUROPE", "EUROPEAN": "EUROPE", "EMEA": "EUROPE",
    "MIDDLE EAST": "MIDDLE_EAST", "MENA": "MIDDLE_EAST",
    "ASIA PACIFIC": "ASIA_PACIFIC", "ASIA": "ASIA_PACIFIC",
    "ASIAN": "ASIA_PACIFIC", "APAC": "ASIA_PACIFIC",
}

_WORLD_ACTIVITY = threading.local()


def reset_world_activity() -> None:
    """Clear the per-turn auto-focus state. Called at the start of each turn."""
    _WORLD_ACTIVITY.last = None
    _WORLD_ACTIVITY.count = 0


def _emit_world_focus(payload: dict) -> None:
    sock, sid = get_request_socket()
    if sock is None:
        return
    try:
        if sid:
            sock.emit("focus_world", payload, room=sid)
        else:
            sock.emit("focus_world", payload)
    except Exception as e:
        print(f"[world] emit failed: {type(e).__name__}: {e}")


def _focus_payload(kind, target, lat, lng, label=None, region=None,
                   metadata=None, altitude=1.5, source="auto"):
    return {
        "kind": kind,
        "target": target,
        "lat": float(lat),
        "lng": float(lng),
        "altitude": float(altitude),
        "label": label or target,
        "region": region,
        "metadata": metadata or {},
        "source": source,
    }


def _anchor_key(payload: dict):
    return (payload.get("kind"),
            round(float(payload.get("lat") or 0.0), 2),
            round(float(payload.get("lng") or 0.0), 2))


def _region_from_text(text: str) -> str | None:
    up = re.sub(r"[_\-]+", " ", (text or "").upper())
    for alias, region in _REGION_ALIASES.items():
        if re.search(rf"\b{re.escape(alias)}\b", up):
            return region
    return None


def _anchor_for_branch(code_or_name: str):
    resolved = _resolve_world_target("branch", code_or_name)
    if not resolved:
        return None
    return _focus_payload(
        "branch", code_or_name, resolved["lat"], resolved["lng"],
        label=resolved.get("label"), region=resolved.get("region"),
        metadata=resolved.get("metadata"),
    )


def _anchor_for_region(region: str):
    resolved = _resolve_world_target("region", region)
    if not resolved:
        return None
    meta = resolved.get("metadata") or {}
    return _focus_payload(
        "region", region.upper(), resolved["lat"], resolved["lng"],
        label=region.upper(), region=region.upper(), metadata=meta,
        altitude=meta.get("altitude_hint", 2.6),
    )


def _anchor_from_document(output: str):
    """Read a branch/customer anchor out of a get_document/query_documents JSON."""
    try:
        doc = json.loads(output)
    except Exception:
        return None
    if not isinstance(doc, dict) or doc.get("error"):
        return None
    if isinstance(doc.get("documents"), list):
        if not doc["documents"] or not isinstance(doc["documents"][0], dict):
            return None
        doc = doc["documents"][0]

    # account_dv exposes `region` as the branch object; customer_dv nests it
    # under accounts[].branch.
    branch = None
    if isinstance(doc.get("region"), dict):
        branch = doc["region"]
    elif isinstance(doc.get("accounts"), list) and doc["accounts"]:
        first = doc["accounts"][0]
        if isinstance(first, dict):
            branch = first.get("branch")

    if isinstance(branch, dict):
        code = branch.get("branchCode")
        if code:
            anchor = _anchor_for_branch(str(code))
            if anchor:
                anchor["metadata"]["city"] = branch.get("city")
                return anchor

    # Fall back to the customer's own name (anchored at their home branch).
    name = None
    cust = doc.get("customer")
    if isinstance(cust, dict):
        name = cust.get("fullName")
    name = name or doc.get("fullName")
    if name:
        resolved = _resolve_world_target("customer", str(name))
        if resolved:
            return _focus_payload(
                "customer", str(name), resolved["lat"], resolved["lng"],
                label=resolved.get("label"), region=resolved.get("region"),
                metadata=resolved.get("metadata"),
            )
    return None


def _anchor_from_run_sql(sql: str, output: str):
    """Read a location out of a run_sql result (columns) or its WHERE clause."""
    try:
        data = json.loads(output)
    except Exception:
        data = None

    if isinstance(data, dict) and isinstance(data.get("columns"), list):
        cols = [str(c).upper() for c in data["columns"]]
        rows = data.get("rows") or []

        def col(*names):
            for n in names:
                if n in cols:
                    return cols.index(n)
            return None

        reg_i = col("REGION")

        # 1. Explicit coordinates win — plot the exact point.
        lat_i, lng_i = col("LATITUDE"), col("LONGITUDE")
        if lat_i is not None and lng_i is not None and rows:
            for r in rows:
                if r[lat_i] is not None and r[lng_i] is not None:
                    reg = r[reg_i] if reg_i is not None else None
                    return _focus_payload(
                        "coords", str(reg or "result"), r[lat_i], r[lng_i],
                        label=f"query result ({reg})" if reg else "query result",
                        region=str(reg) if reg else None, altitude=1.8,
                    )

        # 2. A branch code / name / merchant / city column anchors more precisely.
        code_i = col("BRANCH_CODE")
        if code_i is not None:
            for r in rows:
                if r[code_i]:
                    anchor = _anchor_for_branch(str(r[code_i]))
                    if anchor:
                        return anchor

        branch_i = col("BRANCH_NAME", "BRANCH")
        if branch_i is not None:
            for r in rows:
                if r[branch_i]:
                    anchor = _anchor_for_branch(str(r[branch_i]))
                    if anchor:
                        return anchor

        name_i = col("MERCHANT_NAME", "MERCHANT")
        if name_i is not None:
            for r in rows:
                if r[name_i]:
                    resolved = _resolve_world_target("merchant", str(r[name_i]))
                    if resolved:
                        return _focus_payload(
                            "merchant", str(r[name_i]), resolved["lat"], resolved["lng"],
                            label=resolved.get("label"), region=resolved.get("region"),
                            metadata=resolved.get("metadata"),
                        )

        city_i = col("CITY")
        if city_i is not None:
            for r in rows:
                if r[city_i]:
                    anchor = _anchor_for_branch(str(r[city_i]))
                    if anchor:
                        return anchor

        # 3. Otherwise fly to the region the rows are concentrated in.
        if reg_i is not None and rows:
            tally: dict[str, int] = {}
            for r in rows:
                v = r[reg_i]
                if v and str(v).upper() in _REGION_CENTROIDS:
                    tally[str(v).upper()] = tally.get(str(v).upper(), 0) + 1
            if tally:
                top = max(tally, key=tally.get)
                anchor = _anchor_for_region(top)
                if anchor:
                    anchor["metadata"]["row_count"] = tally[top]
                    return anchor

    # Last resort: a region literal in the SQL itself.
    reg = _region_from_text(sql)
    if reg:
        return _anchor_for_region(reg)
    return None


def infer_world_activity(name: str, args: dict, output: str):
    """Infer a globe anchor from a tool call and stream a focus_world event.

    Returns the emitted payload, or None when the call has no geography (or the
    per-turn budget / dedupe suppresses it).
    """
    anchor = None
    try:
        if name in ("get_document", "query_documents"):
            anchor = _anchor_from_document(output)
        elif name == "run_sql":
            anchor = _anchor_from_run_sql(args.get("sql") or "", output)
    except Exception as e:
        print(f"[world] infer failed for {name}: {type(e).__name__}: {e}")
        return None

    return _consider_auto_focus(anchor)


def infer_world_activity_from_query(user_query: str):
    """Fly to a bank region the user named, before any tool has run.

    Makes the globe feel immediately responsive to a geographic question
    ("what's happening in Europe?") instead of waiting for the first SQL call.
    """
    reg = _region_from_text(user_query)
    if not reg:
        return None
    return _consider_auto_focus(_anchor_for_region(reg))


def _consider_auto_focus(anchor: dict | None):
    """Emit an auto-focus event unless there is no anchor, the turn's budget is
    spent, or it would repeat the previous camera position."""
    if not anchor:
        return None
    if getattr(_WORLD_ACTIVITY, "count", 0) >= _AUTO_FOCUS_MAX:
        return None
    if _anchor_key(anchor) == getattr(_WORLD_ACTIVITY, "last", None):
        return None
    _WORLD_ACTIVITY.last = _anchor_key(anchor)
    _WORLD_ACTIVITY.count = getattr(_WORLD_ACTIVITY, "count", 0) + 1
    _emit_world_focus(anchor)
    return anchor


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
    def tool_search_knowledge(query: str, k: int = 5, kinds: list[str] | None = None,
                              follow_links: bool = False) -> str:
        """Search institutional knowledge (what the agent has learned about the target database) by semantic similarity.
        Use this BEFORE running SQL to discover which tables and columns are relevant.
        `kinds` is an optional filter: table, column, relationship, query_pattern, correction.
        `follow_links` also returns memories linked to each hit (one hop): corrections show the
        fact they superseded, and schema facts show the tables/columns they connect to. Superseded
        facts are hidden from normal results but visible here.
        """
        hits = _retrieve_knowledge(query, k=k, kinds=kinds, follow_links=follow_links)
        for h in hits:
            h["body"] = h["body"][:500]
            for link in h.get("links", []):
                link["body"] = link["body"][:300]
        return json.dumps(hits)

    @register
    def tool_run_sql(sql: str, max_rows: int = 50) -> str:
        """Execute a READ-ONLY SQL statement (SELECT/WITH only) against the target Oracle AI Database
        and return up to `max_rows` rows as JSON.

        Identity-gated: the active "Use As" persona's authorization rules apply.
        Forbidden tables refuse with a clear error naming the missing role/clearance;
        masked columns return as "[REDACTED]"; rows whose region falls outside
        the identity's authorized regions are dropped post-fetch. Quote table names
        as SCHEMA.TABLE so the forbid-check can see them.
        """
        if not _READ_ONLY.match(sql.strip()):
            return json.dumps({"error": "only SELECT / WITH statements are allowed"})

        identity = get_request_identity()

        # 1. Pre-execution: refuse SQL that touches a forbidden table or could
        #    run SQL we cannot inspect (dynamic-SQL packages, inline PL/SQL).
        denial = _sql_denial(sql, identity)
        if denial:
            out = {"error": denial}
            if identity is not None:
                out["identity"] = {
                    "id": identity.id,
                    "label": identity.label,
                    "clearance": identity.clearance,
                    "forbid_tables": list(identity.forbid_tables),
                }
            return json.dumps(out)

        try:
            max_rows = max(1, int(max_rows))
        except (TypeError, ValueError):
            max_rows = 50

        # 2. Run on a dedicated session with the persona pushed into it. From
        #    here the kernel enforces rows, columns and denials itself; the
        #    post-fetch filters below stay as defence in depth and become
        #    no-ops when the database already answered correctly. The session is
        #    READ ONLY, so the database (not the regex above) refuses DML and
        #    SELECT ... FOR UPDATE, and it is private to this call, so another
        #    request's persona cannot bleed into it.
        truncated = False
        try:
            with identity_session(identity, read_only=True) as conn:
                with conn.cursor() as cur:
                    cur.execute(sql)
                    cols = [d[0] for d in cur.description]
                    raw_rows = []
                    for i, r in enumerate(cur):
                        if i >= max_rows:
                            truncated = True
                            break
                        raw_rows.append([(v.read() if hasattr(v, "read") else v) for v in r])
        except Exception as e:
            return json.dumps({"error": str(e)})

        notes: list[str] = []
        rows = raw_rows

        if identity is not None:
            # 2. Post-fetch: drop rows whose REGION isn't authorized.
            keep = region_drop_predicate(identity)
            kept = [r for r in rows if keep(r, cols)]
            dropped = len(rows) - len(kept)
            rows = kept
            if dropped:
                notes.append(
                    f"{dropped} row(s) dropped because their region "
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
        if truncated:
            out["truncated"] = f"more rows exist beyond max_rows={max_rows}; aggregate or filter instead of assuming this is the full result"
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
    def tool_remember(subject: str, body: str, kind: str = "correction",
                      supersedes: str | None = None,
                      link_type: str = "supersedes") -> str:
        """Persist a correction or learning into institutional knowledge so future turns benefit.
        Use when the user corrects you, or when you discover a non-obvious fact that future retrievals should surface.

        Memories written here are globally retrievable (search_knowledge can
        find them from any thread) but they are tagged with the thread_id
        they were first written on, so you can trace provenance.

        `subject` is a short label (e.g. 'SALES.ORDERS.total_cents'); `body` is the fact written as a full sentence.

        When this replaces an earlier fact, pass `supersedes` with the old memory's id OR a phrase that
        finds it. The new memory is linked to the old one and OAMP retires the old fact (it stops
        appearing in normal search but stays visible through search_knowledge(follow_links=True)).
        `link_type` is normally 'supersedes'.
        """
        tid = get_request_thread_id()
        if supersedes:
            target = find_memory(_MEMORY_CLIENT, supersedes)
            if target is None:
                return json.dumps({
                    "ok": False,
                    "error": f"no memory matched {supersedes!r}; write it without "
                             "`supersedes` if there is no earlier fact to retire",
                })
            meta = {"kind": kind, "subject": subject, "source": "agent_remember"}
            if tid:
                meta["origin_thread_id"] = tid
            kwargs = dict(
                user_id=USER_ID, agent_id=AGENT_ID, metadata=meta,
                memory_id_to_link=target.id, link_type=link_type,
                autonomous_linking=False,
            )
            if tid:
                kwargs["thread_id"] = tid
            new_id = _MEMORY_CLIENT.add_memory(body, **kwargs)
            target_meta = getattr(target, "metadata", None) or {}
            return json.dumps({
                "ok": True,
                "memory_id": new_id,
                "linked_to": target.id,
                "link_type": link_type,
                "retired_subject": target_meta.get("subject", ""),
                "retired_status": str(getattr(target, "status", "")).split(".")[-1],
                "origin_thread_id": tid,
            })
        fact = Fact(
            kind=kind, subject=subject, body=body,
            metadata={"source": "agent_remember"},
        )
        result = write_facts(_MEMORY_CLIENT, [fact], thread_id=tid)
        return json.dumps({"ok": True, "origin_thread_id": tid, **result})

    @register
    def tool_link_memories(source: str, target: str, link_type: str = "supports",
                           reason: str = "") -> str:
        """Link two memories you already know about, so retrieval can follow the connection.
        `source` and `target` are memory ids or phrases that find them; the relation reads
        source -> target. Types:
          supports / contradicts  - both memories stay current (evidence, or a flagged conflict)
          supersedes / refines / duplicates - the TARGET is retired (hidden from normal search,
                                              still visible via search_knowledge(follow_links=True))
        Use `remember(supersedes=...)` for the common correction flow; use this tool to connect
        facts that were written at different times (e.g. a later observation that supports an earlier one).
        """
        if link_type not in LINK_TYPES:
            return json.dumps({"ok": False,
                               "error": f"link_type must be one of {list(LINK_TYPES)}"})
        src = find_memory(_MEMORY_CLIENT, source)
        tgt = find_memory(_MEMORY_CLIENT, target)
        if src is None or tgt is None:
            missing = source if src is None else target
            return json.dumps({"ok": False, "error": f"no memory matched {missing!r}"})
        if src.id == tgt.id:
            return json.dumps({"ok": False, "error": "source and target are the same memory"})
        rel_id = link_memories(
            _MEMORY_CLIENT, src.id, tgt.id, link_type=link_type,
            metadata={"source": "agent_link", **({"reason": reason} if reason else {})},
        )
        return json.dumps({
            "ok": rel_id is not None,
            "relation_id": rel_id,
            "link_type": link_type,
            "source_id": src.id,
            "target_id": tgt.id,
            "target_retired": link_type in INVALIDATING_LINK_TYPES,
        })

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
        'flagged_transactions.sql' becomes '/scratch/threads/<this_thread>/flagged_transactions.sql' on
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
        (an account with its customer/branch/cards/transactions, or a customer with its
        accounts/loans). Returns a JSON document.

        Identity-gated: if the active "Use As" persona is forbidden from any of the
        underlying tables the view projects, the call refuses with a clear error.
        Row and column policies are enforced by the database, so masked fields come
        back as null and out-of-region rows are absent.

        `view` must be one of: account_dv, customer_dv.
        `key` is the value of the document _id (numeric account_id or customer_id, as a string).
        """
        from config import DEMO_USER
        allowed = {"account_dv", "customer_dv"}
        if view not in allowed:
            return json.dumps({"error": f"unknown view {view!r}; allowed: {sorted(allowed)}"})

        denial = _duality_forbid_check(view)
        if denial:
            return json.dumps({"error": denial})

        k = int(key) if str(key).isdigit() else key

        # 1. Preferred path — the duality view.
        try:
            with _identity_cursor() as cur:
                cur.execute(
                    f'SELECT JSON_SERIALIZE(data PRETTY) FROM {DEMO_USER}.{view} '
                    f"WHERE JSON_VALUE(data, '$._id') = :k",
                    k=k,
                )
                row = cur.fetchone()
                text = _lob_text(row[0]) if row else None
            if text is None:
                return json.dumps({"error": f"no document with _id={key} in {view}"})
            return text
        except Exception as e:
            code = _dv_error_code(e)
            if code not in _DV_FALLBACK_CODES:
                return json.dumps({"error": f"{type(e).__name__}: {e}"})
            _log_dv_fallback_once(view, code)

        # 2. Fallback — the same document, built directly over the base tables.
        #    VPD still applies (rows + masks), so the identity boundary holds.
        spec = _DOC_SQL[view]
        doc_sql = spec["doc"].replace("__S__", DEMO_USER)
        try:
            with _identity_cursor() as cur:
                cur.execute(
                    f"SELECT JSON_SERIALIZE({doc_sql} RETURNING CLOB PRETTY) "
                    f"FROM {DEMO_USER}.{spec['root']} WHERE {spec['pk']} = :k",
                    k=k,
                )
                row = cur.fetchone()
                text = _lob_text(row[0]) if row else None
            if text is None:
                return json.dumps({"error": f"no document with _id={key} in {view}"})
            return text
        except Exception as e:
            return json.dumps({"error": f"{type(e).__name__}: {e}"})

    @register
    def tool_query_documents(view: str, where: str = "1=1", max_rows: int = 10) -> str:
        """Filter a JSON Relational Duality View with a SQL predicate.
        Use when you want a list of documents matching some condition without writing
        JOINs by hand. The predicate references underlying-table columns of the view's
        root table (e.g. status, account_type for account_dv; segment, risk_rating for customer_dv).

        Identity-gated: same forbid-table check as `get_document`. The database enforces
        row/column policies, so masked fields come back as null and out-of-region rows
        are absent.

        `view` must be one of: account_dv, customer_dv.
        `where` is a SQL boolean expression on the root table's columns (default '1=1').
        `max_rows` caps the result set.
        """
        from config import DEMO_USER
        allowed = {"account_dv", "customer_dv"}
        if view not in allowed:
            return json.dumps({"error": f"unknown view {view!r}; allowed: {sorted(allowed)}"})

        denial = _duality_forbid_check(view)
        if denial:
            return json.dumps({"error": denial})

        # `where` is spliced into SQL: hold it to the same table checks run_sql
        # applies, so it cannot subquery a table the persona may not read.
        denial = _sql_denial(where, get_request_identity())
        if denial:
            return json.dumps({"error": denial})
        try:
            max_rows = max(1, min(int(max_rows), 100))
        except (TypeError, ValueError):
            max_rows = 10

        # 1. Preferred path — the duality view.
        dv_sql = (f"SELECT JSON_SERIALIZE(data) FROM {DEMO_USER}.{view} "
                  f" WHERE ({where}) FETCH FIRST :n ROWS ONLY")
        try:
            with _identity_cursor() as cur:
                cur.execute(dv_sql, n=max_rows)
                docs = [_lob_text(r[0]) for r in cur]
            return json.dumps({"count": len(docs), "documents": [json.loads(d) for d in docs]},
                              default=str)
        except Exception as e:
            code = _dv_error_code(e)
            if code not in _DV_FALLBACK_CODES:
                return json.dumps({"error": f"{type(e).__name__}: {e}", "sql": dv_sql})
            _log_dv_fallback_once(view, code)

        # 2. Fallback — same shape over the base tables.
        spec = _DOC_SQL[view]
        doc_sql = spec["doc"].replace("__S__", DEMO_USER)
        sql = (f"SELECT JSON_SERIALIZE({doc_sql} RETURNING CLOB) "
               f"FROM {DEMO_USER}.{spec['root']} WHERE ({where}) "
               f"FETCH FIRST :n ROWS ONLY")
        try:
            with _identity_cursor() as cur:
                cur.execute(sql, n=max_rows)
                docs = [_lob_text(r[0]) for r in cur]
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
        body = content_to_text(getattr(rec, "content", ""))
        return json.dumps({
            "tool_call_id": tool_call_id,
            "tool_name": meta.get("tool_name"),
            "tool_args": meta.get("tool_args"),
            "tool_output": body,
        })

    @register
    def tool_search_tavily(query: str, max_results: int = 5, topic: str = "general") -> str:
        """Search the live web for real-time news, breaking events, sanctions
        updates, fraud rings, bank failures, regulatory action, anything
        time-sensitive that the database doesn't carry. Backed by Tavily's
        AI-optimised search API.

        Use this when the user asks about CURRENT events ("what's happening
        with X right now?", "any disruptions affecting Y?", "news about Z"),
        or when you need to ground a FINANCE answer in something happening
        in the real world right now (e.g. "which customers are exposed by
        current news?" — search the news for events, then cross-reference
        FINANCE.transactions / accounts / merchants via run_sql).

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
        branch, merchant, customer, or bank region.

        Use this whenever the user says things like:
          - "show me the Wall Street branch on the globe"
          - "fly to Dubai"
          - "highlight the BitVault Exchange merchant"
          - "zoom to Europe"

        `target_kind` — one of: branch, merchant, customer, region.
        `target`      — the entity name / code / region label, e.g.
                        'Wall Street', 'BitVault Exchange', 'Isabella Allen',
                        'EUROPE'.
        `altitude`    — globe camera altitude (1.0 = close, 2.5 = global view).
        """
        kind = (target_kind or "").strip().lower()
        if kind not in ("branch", "merchant", "customer", "region"):
            return json.dumps({"error": f"unknown target_kind {target_kind!r}; "
                              "must be one of branch|merchant|customer|region"})
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
            "region": anchor.get("region"),
            "metadata": anchor.get("metadata", {}),
            "source": "explicit",
        }
        _emit_world_focus(payload)
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
