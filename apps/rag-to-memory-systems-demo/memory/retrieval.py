"""Unified retrieval: policy + preference + fact + episodic + recent
trace in one round trip via four cascading query tiers.

assemble() enters at the requested tier and steps down on Oracle errors
until one succeeds. RetrievalResult.mode reports the tier that served.

  HYBRID_QUERY       — vector + lexical fused for facts and episodes
                       (0.4 vec / 0.6 lex when both fire, floor 0.4)
  VECTOR_ONLY_QUERY  — pure vector; Oracle Text unavailable
  LEXICAL_ONLY_QUERY — Oracle Text CONTAINS only; no embedding model
  LIKE_QUERY         — INSTR substring; last-resort, no indexes needed
"""
from __future__ import annotations
import json
import re
from dataclasses import dataclass
from typing import Any
import oracledb
from memory.embeddings import vector_embedding_sql

# Oracle Text operator/reserved words that must be removed from free-form user
# queries before they are passed to CONTAINS().  These cause DRG-50901 syntax
# errors when they appear without operands.
_OT_RESERVED = frozenset({
    "about", "accum", "and", "btitle", "defn", "fuzzy", "haspath",
    "inpath", "minus", "near", "not", "or", "stem", "threshold",
    "weight", "within",
})
_OT_RESERVED_RE = re.compile(
    r"\b(" + "|".join(re.escape(w) for w in _OT_RESERVED) + r")\b",
    re.IGNORECASE,
)


def _sanitize_for_contains(text: str) -> str:
    """Sanitize a free-form query string for Oracle Text CONTAINS().

    Oracle Text reserves several operator keywords (ABOUT, NEAR, …) and
    punctuation characters (?, $, %, !, ~, {, }, (, ), [, ], <, >, ^, ;)
    that cause DRG-50901 syntax errors when they appear in arbitrary prose.
    This function removes them so the lexical CTE stays safe without
    disabling the hybrid search path.
    """
    # Remove Oracle Text operator keywords.
    cleaned = _OT_RESERVED_RE.sub(" ", text)
    # Remove Oracle Text special punctuation that acts as operators.
    cleaned = re.sub(r"[?$%!~{}()\[\]<>^;,]", " ", cleaned)
    # Collapse multiple spaces and strip surrounding whitespace.
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned or "the"  # CONTAINS requires at least one term


def _decode_json(raw: Any) -> Any:
    """Decode Oracle JSON column output defensively (handles scalar
    auto-decode and LOB results)."""
    if raw is None:
        return None
    if hasattr(raw, "read"):
        result = raw.read()
        # Async LOBs return coroutines
        import asyncio
        if asyncio.iscoroutine(result):
            raise RuntimeError("Got coroutine from LOB.read() — call _decode_json_async instead")
        raw = result
    if isinstance(raw, (dict, list)):
        return raw
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return raw


async def _decode_json_async(raw: Any) -> Any:
    """Async variant for AsyncLOB returns."""
    if raw is None:
        return None
    if hasattr(raw, "read"):
        result = raw.read()
        import asyncio
        if asyncio.iscoroutine(result):
            raw = await result
        else:
            raw = result
    if isinstance(raw, (dict, list)):
        return raw
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return raw


# NOTE: fact_memory.content and episodic_memory.summary are CLOB columns.
# Oracle does not allow CLOB in COALESCE or FULL OUTER JOIN ON equality.
# We materialize them as VARCHAR2(4000) via DBMS_LOB.SUBSTR inside inner CTEs
# before the FULL OUTER JOIN and JSON_OBJECT calls.
_VEMB = vector_embedding_sql(":query_text")

HYBRID_QUERY = f"""
WITH
policies AS (
  SELECT 'policy' AS kind, NULL AS rank_score, 0 AS sort_bucket,
         JSON_OBJECT('policy_key' VALUE policy_key,
                     'policy_value' VALUE policy_value,
                     'policy_type' VALUE policy_type,
                     'version' VALUE version) AS payload
  FROM policy_memory
  WHERE tenant_id = :tenant_id
    AND (effective_until IS NULL OR effective_until > SYSTIMESTAMP)
),
preferences AS (
  SELECT 'preference' AS kind, NULL AS rank_score, 1 AS sort_bucket,
         JSON_OBJECT('pref_key' VALUE pref_key,
                     'pref_value' VALUE pref_value,
                     'source' VALUE source,
                     'confidence' VALUE confidence) AS payload
  FROM preference_memory
  WHERE tenant_id = :tenant_id AND user_id = :user_id
),
fact_vec AS (
  SELECT fact_id,
         DBMS_LOB.SUBSTR(content, 4000, 1) AS content,
         subject, predicate, confidence,
         VECTOR_DISTANCE(embedding, {_VEMB}, COSINE) AS vec_dist
  FROM fact_memory
  WHERE tenant_id = :tenant_id
    AND status = 'active'
    AND superseded_by IS NULL
    AND (user_id IS NULL OR user_id = :user_id)
    AND (expires_at IS NULL OR expires_at > SYSTIMESTAMP)
  ORDER BY vec_dist
  FETCH FIRST 20 ROWS ONLY
),
fact_lex AS (
  SELECT fact_id,
         DBMS_LOB.SUBSTR(content, 4000, 1) AS content,
         subject, predicate, confidence, SCORE(1) AS lex_score
  FROM fact_memory
  WHERE tenant_id = :tenant_id
    AND status = 'active'
    AND superseded_by IS NULL
    AND (user_id IS NULL OR user_id = :user_id)
    AND (expires_at IS NULL OR expires_at > SYSTIMESTAMP)
    AND CONTAINS(content, :lex_query, 1) > 0
  ORDER BY lex_score DESC
  FETCH FIRST 20 ROWS ONLY
),
fact_max_lex AS (SELECT NULLIF(MAX(lex_score), 0) AS max_lex FROM fact_lex),
fact_fused AS (
  SELECT COALESCE(v.fact_id, l.fact_id) AS fact_id,
         COALESCE(v.content, l.content) AS content,
         COALESCE(v.subject, l.subject) AS subject,
         COALESCE(v.predicate, l.predicate) AS predicate,
         COALESCE(v.confidence, l.confidence) AS confidence,
         CASE
           WHEN v.vec_dist IS NOT NULL AND l.lex_score IS NOT NULL THEN
             0.4 * (1.0 / (1.0 + v.vec_dist)) + 0.6 * (l.lex_score / m.max_lex)
           WHEN v.vec_dist IS NOT NULL THEN 1.0 / (1.0 + v.vec_dist)
           ELSE l.lex_score / m.max_lex
         END AS rank_score
  FROM fact_vec v FULL OUTER JOIN fact_lex l ON v.fact_id = l.fact_id
  CROSS JOIN fact_max_lex m
),
facts AS (
  SELECT 'fact' AS kind, rank_score, 2 AS sort_bucket,
         JSON_OBJECT('fact_id' VALUE fact_id, 'content' VALUE content,
                     'subject' VALUE subject, 'predicate' VALUE predicate,
                     'confidence' VALUE confidence) AS payload
  FROM fact_fused WHERE rank_score >= 0.4
  ORDER BY rank_score DESC FETCH FIRST 5 ROWS ONLY
),
ep_vec AS (
  SELECT episode_id, task_type, title,
         DBMS_LOB.SUBSTR(summary, 4000, 1) AS summary, outcome,
         VECTOR_DISTANCE(embedding, {_VEMB}, COSINE) AS vec_dist
  FROM episodic_memory
  WHERE tenant_id = :tenant_id AND status = 'active'
  ORDER BY vec_dist
  FETCH FIRST 20 ROWS ONLY
),
ep_lex AS (
  -- CONTAINS label 2 keeps SCORE() distinct from fact's SCORE(1).
  SELECT episode_id, task_type, title,
         DBMS_LOB.SUBSTR(summary, 4000, 1) AS summary, outcome,
         SCORE(2) AS lex_score
  FROM episodic_memory
  WHERE tenant_id = :tenant_id AND status = 'active'
    AND CONTAINS(summary, :lex_query, 2) > 0
  ORDER BY lex_score DESC
  FETCH FIRST 20 ROWS ONLY
),
ep_max_lex AS (SELECT NULLIF(MAX(lex_score), 0) AS max_lex FROM ep_lex),
ep_fused AS (
  SELECT COALESCE(v.episode_id, l.episode_id) AS episode_id,
         COALESCE(v.task_type, l.task_type) AS task_type,
         COALESCE(v.title, l.title) AS title,
         COALESCE(v.summary, l.summary) AS summary,
         COALESCE(v.outcome, l.outcome) AS outcome,
         CASE
           WHEN v.vec_dist IS NOT NULL AND l.lex_score IS NOT NULL THEN
             0.4 * (1.0 / (1.0 + v.vec_dist)) + 0.6 * (l.lex_score / m.max_lex)
           WHEN v.vec_dist IS NOT NULL THEN 1.0 / (1.0 + v.vec_dist)
           ELSE l.lex_score / m.max_lex
         END AS rank_score
  FROM ep_vec v FULL OUTER JOIN ep_lex l ON v.episode_id = l.episode_id
  CROSS JOIN ep_max_lex m
),
episodes AS (
  SELECT 'episodic' AS kind, rank_score, 3 AS sort_bucket,
         JSON_OBJECT('episode_id' VALUE episode_id, 'task_type' VALUE task_type,
                     'title' VALUE title,
                     'summary' VALUE summary,
                     'outcome' VALUE outcome) AS payload
  FROM ep_fused WHERE rank_score >= 0.4
  ORDER BY rank_score DESC FETCH FIRST 3 ROWS ONLY
),
recent_trace AS (
  SELECT 'trace' AS kind, NULL AS rank_score, 4 AS sort_bucket,
         JSON_OBJECT('turn_index' VALUE turn_index,
                     'event_type' VALUE event_type,
                     'payload' VALUE payload) AS payload
  FROM trace_memory
  WHERE run_id = :run_id
  ORDER BY turn_index DESC FETCH FIRST 5 ROWS ONLY
)
SELECT kind, rank_score, payload, sort_bucket FROM policies
UNION ALL SELECT kind, rank_score, payload, sort_bucket FROM preferences
UNION ALL SELECT kind, rank_score, payload, sort_bucket FROM facts
UNION ALL SELECT kind, rank_score, payload, sort_bucket FROM episodes
UNION ALL SELECT kind, rank_score, payload, sort_bucket FROM recent_trace
ORDER BY sort_bucket, rank_score DESC NULLS LAST
"""


VECTOR_ONLY_QUERY = f"""
WITH
policies AS (
  SELECT 'policy' AS kind, NULL AS rank_score, 0 AS sort_bucket,
         JSON_OBJECT('policy_key' VALUE policy_key,
                     'policy_value' VALUE policy_value,
                     'policy_type' VALUE policy_type,
                     'version' VALUE version) AS payload
  FROM policy_memory
  WHERE tenant_id = :tenant_id
    AND (effective_until IS NULL OR effective_until > SYSTIMESTAMP)
),
preferences AS (
  SELECT 'preference' AS kind, NULL AS rank_score, 1 AS sort_bucket,
         JSON_OBJECT('pref_key' VALUE pref_key,
                     'pref_value' VALUE pref_value,
                     'source' VALUE source,
                     'confidence' VALUE confidence) AS payload
  FROM preference_memory
  WHERE tenant_id = :tenant_id AND user_id = :user_id
),
facts AS (
  SELECT 'fact' AS kind,
         1.0 / (1.0 + VECTOR_DISTANCE(embedding, {vector_embedding_sql(':query_text')}, COSINE)) AS rank_score,
         2 AS sort_bucket,
         JSON_OBJECT('fact_id' VALUE fact_id,
                     'content' VALUE DBMS_LOB.SUBSTR(content, 4000, 1),
                     'subject' VALUE subject, 'predicate' VALUE predicate,
                     'confidence' VALUE confidence) AS payload
  FROM fact_memory
  WHERE tenant_id = :tenant_id
    AND status = 'active'
    AND superseded_by IS NULL
    AND (user_id IS NULL OR user_id = :user_id)
    AND (expires_at IS NULL OR expires_at > SYSTIMESTAMP)
  ORDER BY VECTOR_DISTANCE(embedding, {vector_embedding_sql(':query_text')}, COSINE)
  FETCH FIRST 5 ROWS ONLY
),
episodes AS (
  SELECT 'episodic' AS kind,
         1.0 / (1.0 + VECTOR_DISTANCE(embedding, {vector_embedding_sql(':query_text')}, COSINE)) AS rank_score,
         3 AS sort_bucket,
         JSON_OBJECT('episode_id' VALUE episode_id, 'task_type' VALUE task_type,
                     'title' VALUE title,
                     'summary' VALUE DBMS_LOB.SUBSTR(summary, 4000, 1),
                     'outcome' VALUE outcome) AS payload
  FROM episodic_memory
  WHERE tenant_id = :tenant_id AND status = 'active'
  ORDER BY VECTOR_DISTANCE(embedding, {vector_embedding_sql(':query_text')}, COSINE)
  FETCH FIRST 3 ROWS ONLY
),
recent_trace AS (
  SELECT 'trace' AS kind, NULL AS rank_score, 4 AS sort_bucket,
         JSON_OBJECT('turn_index' VALUE turn_index,
                     'event_type' VALUE event_type,
                     'payload' VALUE payload) AS payload
  FROM trace_memory
  WHERE run_id = :run_id
  ORDER BY turn_index DESC FETCH FIRST 5 ROWS ONLY
)
SELECT kind, rank_score, payload, sort_bucket FROM policies
UNION ALL SELECT kind, rank_score, payload, sort_bucket FROM preferences
UNION ALL SELECT kind, rank_score, payload, sort_bucket FROM facts
UNION ALL SELECT kind, rank_score, payload, sort_bucket FROM episodes
UNION ALL SELECT kind, rank_score, payload, sort_bucket FROM recent_trace
ORDER BY sort_bucket, rank_score DESC NULLS LAST
"""


LEXICAL_ONLY_QUERY = """
WITH
policies AS (
  SELECT 'policy' AS kind, NULL AS rank_score, 0 AS sort_bucket,
         JSON_OBJECT('policy_key' VALUE policy_key,
                     'policy_value' VALUE policy_value,
                     'policy_type' VALUE policy_type,
                     'version' VALUE version) AS payload
  FROM policy_memory
  WHERE tenant_id = :tenant_id
    AND (effective_until IS NULL OR effective_until > SYSTIMESTAMP)
),
preferences AS (
  SELECT 'preference' AS kind, NULL AS rank_score, 1 AS sort_bucket,
         JSON_OBJECT('pref_key' VALUE pref_key,
                     'pref_value' VALUE pref_value,
                     'source' VALUE source,
                     'confidence' VALUE confidence) AS payload
  FROM preference_memory
  WHERE tenant_id = :tenant_id AND user_id = :user_id
),
fact_lex AS (
  SELECT fact_id,
         DBMS_LOB.SUBSTR(content, 4000, 1) AS content,
         subject, predicate, confidence, SCORE(1) AS lex_score
  FROM fact_memory
  WHERE tenant_id = :tenant_id
    AND status = 'active'
    AND superseded_by IS NULL
    AND (user_id IS NULL OR user_id = :user_id)
    AND (expires_at IS NULL OR expires_at > SYSTIMESTAMP)
    AND CONTAINS(content, :lex_query, 1) > 0
  ORDER BY lex_score DESC
  FETCH FIRST 20 ROWS ONLY
),
fact_max_lex AS (SELECT NULLIF(MAX(lex_score), 0) AS max_lex FROM fact_lex),
facts AS (
  SELECT 'fact' AS kind, (f.lex_score / m.max_lex) AS rank_score,
         2 AS sort_bucket,
         JSON_OBJECT('fact_id' VALUE f.fact_id, 'content' VALUE f.content,
                     'subject' VALUE f.subject, 'predicate' VALUE f.predicate,
                     'confidence' VALUE f.confidence) AS payload
  FROM fact_lex f CROSS JOIN fact_max_lex m
  ORDER BY rank_score DESC FETCH FIRST 5 ROWS ONLY
),
ep_lex AS (
  SELECT episode_id, task_type, title,
         DBMS_LOB.SUBSTR(summary, 4000, 1) AS summary, outcome,
         SCORE(2) AS lex_score
  FROM episodic_memory
  WHERE tenant_id = :tenant_id AND status = 'active'
    AND CONTAINS(summary, :lex_query, 2) > 0
  ORDER BY lex_score DESC
  FETCH FIRST 20 ROWS ONLY
),
ep_max_lex AS (SELECT NULLIF(MAX(lex_score), 0) AS max_lex FROM ep_lex),
episodes AS (
  SELECT 'episodic' AS kind, (e.lex_score / m.max_lex) AS rank_score,
         3 AS sort_bucket,
         JSON_OBJECT('episode_id' VALUE e.episode_id, 'task_type' VALUE e.task_type,
                     'title' VALUE e.title,
                     'summary' VALUE e.summary,
                     'outcome' VALUE e.outcome) AS payload
  FROM ep_lex e CROSS JOIN ep_max_lex m
  ORDER BY rank_score DESC FETCH FIRST 3 ROWS ONLY
),
recent_trace AS (
  SELECT 'trace' AS kind, NULL AS rank_score, 4 AS sort_bucket,
         JSON_OBJECT('turn_index' VALUE turn_index,
                     'event_type' VALUE event_type,
                     'payload' VALUE payload) AS payload
  FROM trace_memory
  WHERE run_id = :run_id
  ORDER BY turn_index DESC FETCH FIRST 5 ROWS ONLY
)
SELECT kind, rank_score, payload, sort_bucket FROM policies
UNION ALL SELECT kind, rank_score, payload, sort_bucket FROM preferences
UNION ALL SELECT kind, rank_score, payload, sort_bucket FROM facts
UNION ALL SELECT kind, rank_score, payload, sort_bucket FROM episodes
UNION ALL SELECT kind, rank_score, payload, sort_bucket FROM recent_trace
ORDER BY sort_bucket, rank_score DESC NULLS LAST
"""


# Plain INSTR substring match: no index, model, or extension required.
# No ranking signal, so rank_score=NULL and rows order by recency.
LIKE_QUERY = """
WITH
policies AS (
  SELECT 'policy' AS kind, NULL AS rank_score, 0 AS sort_bucket,
         JSON_OBJECT('policy_key' VALUE policy_key,
                     'policy_value' VALUE policy_value,
                     'policy_type' VALUE policy_type,
                     'version' VALUE version) AS payload
  FROM policy_memory
  WHERE tenant_id = :tenant_id
    AND (effective_until IS NULL OR effective_until > SYSTIMESTAMP)
),
preferences AS (
  SELECT 'preference' AS kind, NULL AS rank_score, 1 AS sort_bucket,
         JSON_OBJECT('pref_key' VALUE pref_key,
                     'pref_value' VALUE pref_value,
                     'source' VALUE source,
                     'confidence' VALUE confidence) AS payload
  FROM preference_memory
  WHERE tenant_id = :tenant_id AND user_id = :user_id
),
facts AS (
  SELECT 'fact' AS kind, NULL AS rank_score, 2 AS sort_bucket,
         JSON_OBJECT('fact_id' VALUE fact_id,
                     'content' VALUE DBMS_LOB.SUBSTR(content, 4000, 1),
                     'subject' VALUE subject, 'predicate' VALUE predicate,
                     'confidence' VALUE confidence) AS payload
  FROM fact_memory
  WHERE tenant_id = :tenant_id
    AND status = 'active'
    AND superseded_by IS NULL
    AND (user_id IS NULL OR user_id = :user_id)
    AND (expires_at IS NULL OR expires_at > SYSTIMESTAMP)
    AND INSTR(LOWER(DBMS_LOB.SUBSTR(content, 4000, 1)), LOWER(:like_term)) > 0
  ORDER BY created_at DESC FETCH FIRST 5 ROWS ONLY
),
episodes AS (
  SELECT 'episodic' AS kind, NULL AS rank_score, 3 AS sort_bucket,
         JSON_OBJECT('episode_id' VALUE episode_id, 'task_type' VALUE task_type,
                     'title' VALUE title,
                     'summary' VALUE DBMS_LOB.SUBSTR(summary, 4000, 1),
                     'outcome' VALUE outcome) AS payload
  FROM episodic_memory
  WHERE tenant_id = :tenant_id AND status = 'active'
    AND INSTR(LOWER(DBMS_LOB.SUBSTR(summary, 4000, 1)), LOWER(:like_term)) > 0
  ORDER BY completed_at DESC FETCH FIRST 3 ROWS ONLY
),
recent_trace AS (
  SELECT 'trace' AS kind, NULL AS rank_score, 4 AS sort_bucket,
         JSON_OBJECT('turn_index' VALUE turn_index,
                     'event_type' VALUE event_type,
                     'payload' VALUE payload) AS payload
  FROM trace_memory
  WHERE run_id = :run_id
  ORDER BY turn_index DESC FETCH FIRST 5 ROWS ONLY
)
SELECT kind, rank_score, payload, sort_bucket FROM policies
UNION ALL SELECT kind, rank_score, payload, sort_bucket FROM preferences
UNION ALL SELECT kind, rank_score, payload, sort_bucket FROM facts
UNION ALL SELECT kind, rank_score, payload, sort_bucket FROM episodes
UNION ALL SELECT kind, rank_score, payload, sort_bucket FROM recent_trace
ORDER BY sort_bucket, rank_score DESC NULLS LAST
"""


# Cascade order. "like" never degrades — plain SQL.
_CASCADE: list[str] = ["hybrid", "vector", "lexical", "like"]


def _build_like_term(text: str) -> str:
    """Reduce a free-form query to a single substring for INSTR.
    Picks the longest word (heuristic for the most-distinctive token),
    falls back to the whole sanitized string."""
    sanitized = _sanitize_for_contains(text)
    words = [w for w in sanitized.split() if len(w) >= 3]
    if not words:
        return sanitized
    return max(words, key=len)


def relevance_tier(score: float | None) -> str:
    """Map a fused rank score to a tier the agent reads directly.

    high ≥ 0.7, standard ≥ 0.5, low < 0.5. None (no vector signal,
    lexical-only fallback) maps to "standard".
    """
    if score is None:
        return "standard"
    if score >= 0.7:
        return "high"
    if score >= 0.5:
        return "standard"
    return "low"


@dataclass
class RetrievedRow:
    kind: str
    rank_score: float | None
    payload: dict[str, Any]

    @property
    def relevance(self) -> str:
        return relevance_tier(self.rank_score)


@dataclass
class RetrievalResult:
    rows: list
    mode: str = "hybrid"

    def by_kind(self, kind: str) -> list:
        return [r for r in self.rows if r.kind == kind]

    def counts(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for r in self.rows:
            out[r.kind] = out.get(r.kind, 0) + 1
        return out


_TIER_SQL: dict[str, str] = {
    "hybrid": HYBRID_QUERY,
    "vector": VECTOR_ONLY_QUERY,
    "lexical": LEXICAL_ONLY_QUERY,
    "like": LIKE_QUERY,
}


def _params_for_tier(
    tier: str, tenant_id: str, user_id: str, run_id: str, query_text: str,
) -> dict:
    """Bind only the variables each tier's SQL references."""
    params: dict = {"tenant_id": tenant_id, "user_id": user_id, "run_id": run_id}
    if tier in ("hybrid", "vector"):
        params["query_text"] = query_text
    if tier in ("hybrid", "lexical"):
        params["lex_query"] = _sanitize_for_contains(query_text)
    if tier == "like":
        params["like_term"] = _build_like_term(query_text)
    return params


async def assemble(
    conn: oracledb.AsyncConnection,
    tenant_id: str,
    user_id: str,
    run_id: str,
    query_text: str,
    mode: str = "hybrid",
) -> RetrievalResult:
    """Issue retrieval starting at `mode`, cascading down on Oracle
    errors. RetrievalResult.mode reports the tier that actually served."""
    if mode not in _TIER_SQL:
        raise ValueError(f"unknown retrieval mode {mode!r}; expected one of {_CASCADE}")
    start_idx = _CASCADE.index(mode)
    last_err: Exception | None = None
    for tier in _CASCADE[start_idx:]:
        try:
            cur = conn.cursor()
            params = _params_for_tier(
                tier, tenant_id, user_id, run_id, query_text,
            )
            await cur.execute(_TIER_SQL[tier], **params)
            rows: list[RetrievedRow] = []
            async for kind, rank, payload, _bucket in cur:
                decoded = await _decode_json_async(payload)
                rows.append(RetrievedRow(kind=kind, rank_score=rank, payload=decoded))
            return RetrievalResult(rows=rows, mode=tier)
        except oracledb.DatabaseError as e:
            # Missing Oracle Text (ORA-29900/29855) or unregistered
            # embedding model (ORA-51xxx). "like" never lands here.
            last_err = e
            continue
    raise last_err if last_err else RuntimeError("retrieval cascade exhausted")
