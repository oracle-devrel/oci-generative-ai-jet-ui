"""Oracle AI Agent Memory (OAMP) — the official package as the DEFAULT memory core.

This is the honest recommendation and what a fresh clone runs (unless you configure
Ollama — see the resolver in research_agent.py): `oracleagentmemory` turns the same
database this repo already uses into a managed memory core, maintained and benchmarked
by Oracle. What it takes over, and what stays:

  conversational memory -> OAMP threads + context summaries   (BRAIN_THREAD / BRAIN_MESSAGE)
  semantic memory       -> OAMP durable memories, extracted   (BRAIN_MEMORY)
                           automatically by an LLM from each exchange
  episodic run log      -> stays custom (memory.py)           (AGENT_MEMORY)
  procedural tool stats -> stays custom (procedural.py)       (TOOL_REGISTRY)

OAMP has no run-log or tool-ranking record types — those two are this repo's EXTENSION
of the memory core, living in the same database. MEMORY_BACKEND=custom switches to the
from-scratch learning track (semantic_memory.py + conversation.py) — hand-built tables,
and the fully-local path: it's verified on every LLM provider including $0 Ollama,
while OAMP extraction is verified here with claude-sonnet-5 (small local models fail
its structured-output format silently — which is why the resolver auto-picks custom
when LLM_PROVIDER=ollama).

Everything below reuses the repo's existing configuration:
  - the in-DB MINILM embedder (zero embedding API calls — same story as search)
  - LLM_PROVIDER / LLM_MODEL from llm.py, mapped to LiteLLM ids for OAMP
  - the PRIVACY GUARD, passed as 26.6's memory_extraction_custom_instructions,
    so the managed extractor obeys the same rule as the custom consolidator

Inspect it like everything else in this build — it's just tables:
  SELECT memory_type, content FROM brain_memory ORDER BY created_at DESC;
"""
import os
import re
import uuid

_MINILM_DIM = 384
_MINILM_TOKENS = 128          # all_MiniLM_L12_v2 context window
STORE_ID = os.environ.get("OAMP_STORE_ID", "brain")   # table prefix: BRAIN_*
USER_ID = os.environ.get("BRAIN_USER", "me")
AGENT_ID = "research"

# Same rule as semantic_memory.py's consolidator — the guard moves INTO the managed core.
# Written adversarially on purpose: the first version of this rule let a contract term
# (a fictional-fixture "999-day exclusivity clause") through extraction while correctly dropping the dollar
# amount — tests/eval_oamp.py probe 2 exists to catch exactly that regression.
_PRIVACY_GUARD = (
    "HARD RULE — private business information must NEVER become a memory, not even "
    "paraphrased or partially. That means: no earnings, rates, fees, pricing, invoices, "
    "payments, banking, budgets, or taxes; no brand/client names attached to deals; and "
    "no contract or deal terms OF ANY KIND — exclusivity, duration, deliverable counts, "
    "usage rights, legal clauses. If a message mixes private business detail with normal "
    "content, extract ONLY the normal content and silently drop the rest. When unsure "
    "whether something is a business/deal detail, do not extract it."
)

# LiteLLM model ids per provider (OAMP speaks LiteLLM). Overridable with OAMP_LLM_MODEL.
# NOTE: haiku-4-5 fails OAMP 26.6's structured extraction format (verified: "invalid
# structured output" -> zero memories), so the anthropic default is sonnet-5.
_EXTRACT_DEFAULTS = {
    "anthropic": "anthropic/claude-sonnet-5",
    "openai": "openai/gpt-5.6-terra",
    "ollama": "ollama/llama3.2",
}

# DEFENSE IN DEPTH: the prompt guard above gets PARTIAL compliance (tests/eval_oamp.py
# probe 2 caught a contract term surviving extraction before the guard was hardened), so
# extracted memories are ALSO swept against these structural deny patterns — an enforced
# check, not an instruction. Adapt to your own private categories (same advice as the
# classifier rubric) and extend without code edits via OAMP_DENY_EXTRA (comma-separated
# regexes). False positives delete a benign memory — the right failure direction for a
# privacy control.
_DENY_PATTERNS = [
    r"\$\s?(?!0(?:\.0+)?\b)\d[\d,]*(?:\.\d+)?\s?[km]?\b",         # money amounts (not $0)
    r"\b(?:rate|fee|price|pricing|quote|invoice|payment|payout|"   # money words near a number
    r"budget|earnings|income|salary|compensation)\b.{0,40}\d",
    r"\b(?:exclusivity|usage rights|deliverables?|sow|nda|non-disclosure|"
    r"contract (?:term|clause)|deal terms?)\b",
    r"\b(?:iban|routing number|account number|wire transfer)\b",
]


def violates_privacy(text):
    """Pure check: the deny pattern `text` matches, or None. Unit-tested in test_brain."""
    low = (text or "").lower()
    pats = _DENY_PATTERNS + [p for p in os.environ.get("OAMP_DENY_EXTRA", "").split(",") if p.strip()]
    for pat in pats:
        if re.search(pat, low):
            return pat
    return None


def enforce_privacy(conn, hours=None):
    """Sweep extracted memories against the deny patterns and DELETE violators via the
    package's own lifecycle API. `hours` limits the scan to recent rows (the inline
    sweep after each exchange); None scans everything (the daily sync sweep).
    Returns the removed contents so callers can report."""
    client = get_client(conn)
    sql = f"select record_id, content from {STORE_ID}_memory"
    binds = {}
    if hours:
        sql += " where created_at > sysdate - :h/24"
        binds["h"] = hours
    with conn.cursor() as cur:
        cur.execute(sql, **binds)
        rows = [(rid, c.read() if hasattr(c, "read") else c) for rid, c in cur.fetchall()]
    removed = []
    for rid, content in rows:
        if violates_privacy(content):
            try:
                client.delete_memory(rid)
                removed.append(content[:120])
            except Exception as e:
                print(f"[oamp] sweep could not delete {rid}: {type(e).__name__}")
    if removed:
        print(f"[oamp] privacy sweep removed {len(removed)} memory(ies)")
    return removed


_client = None
_thread = None


def _llm():
    from oracleagentmemory.core.llms import Llm
    provider = os.environ.get("LLM_PROVIDER", "anthropic").lower()
    model = os.environ.get("OAMP_LLM_MODEL") or _EXTRACT_DEFAULTS.get(
        provider, _EXTRACT_DEFAULTS["anthropic"])
    kwargs = {}
    if provider == "ollama":
        kwargs["api_base"] = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
    return Llm(model=model, **kwargs)


def _db_handle(conn):
    """Prefer the repo's connection POOL over a single session — OAMP runs its
    per-type context-card searches concurrently only with a pool, and a pool is the
    package's recommended production setup. Falls back to the caller's connection
    (single-session mode) when pooling is disabled (DB_POOL=0, e.g. the evals)."""
    import os as _os
    if _os.environ.get("DB_POOL", "1") == "0":
        return conn
    try:
        import db
        return db._get_pool()
    except Exception:
        return conn


def get_client(conn):
    """One OracleAgentMemory client per process, over the repo's pool (or the given
    connection). Schema is auto-created on first use (CREATE_IF_NECESSARY)."""
    global _client
    if _client is None:
        from oracleagentmemory.core import (
            OracleAgentMemory, SchemaPolicy, SearchStrategy, MemoryExtractionConfig)
        from oracleagentmemory.core.embedders import OracleDBEmbedder
        handle = _db_handle(conn)
        _client = OracleAgentMemory(
            connection=handle,
            embedder=OracleDBEmbedder(connection=handle, model="MINILM",
                                      embedding_dimension=_MINILM_DIM,
                                      max_input_tokens=_MINILM_TOKENS),
            llm=_llm(),
            schema_policy=SchemaPolicy.CREATE_IF_NECESSARY,
            memory_store_id=STORE_ID,
            search_strategy=SearchStrategy.HYBRID,   # 26.6: lexical + vector, one index
            memory_extraction_config=MemoryExtractionConfig(
                memory_extraction_custom_instructions=_PRIVACY_GUARD),
        )
    return _client


def recall_facts(conn, query, k=5):
    """Durable memories relevant to `query`, shaped like semantic_memory.semantic_recall
    (category + fact) so the agent prompt renders identically on either backend.

    HYBRID BY DESIGN: OAMP extracts per-exchange (what THIS conversation taught us);
    the repo's global consolidation distills across ALL runs + content (what it all
    adds up to). The ship path keeps both — package memories first, then the top
    consolidated global facts, deduped. Best of the managed core and the editorial layer."""
    results = get_client(conn).search(
        query=query, user_id=USER_ID, exact_user_match=True, max_results=k,
        record_types=["memory", "fact", "preference", "guideline"])
    facts = [{"category": getattr(r, "record_type", None) or "memory",
              "fact": getattr(r, "content", None) or str(r)} for r in results]
    try:   # the global consolidated layer (semantic_memory table) still enriches recall
        from semantic_memory import semantic_recall
        seen = {f["fact"][:60].lower() for f in facts}
        for g in semantic_recall(conn, query, k=3):
            if g["fact"][:60].lower() not in seen:
                facts.append({"category": f"global/{g['category']}", "fact": g["fact"]})
    except Exception:
        pass   # no consolidated facts yet (fresh brain) — package memories alone are fine
    return facts


def record_exchange(conn, question, answer):
    """Persist one Q/A exchange to the session thread. OAMP extracts durable memories
    from it automatically (this replaces the custom episodic->semantic consolidation
    step on this backend). Best-effort: memory must never break a research answer."""
    global _thread
    try:
        client = get_client(conn)
        if _thread is None:
            _thread = client.create_thread(
                thread_id="sess-" + uuid.uuid4().hex[:10],
                user_id=USER_ID, agent_id=AGENT_ID)
        _thread.add_messages([
            {"role": "user", "content": question},
            {"role": "assistant", "content": answer},
        ])
        # defense in depth: sweep what the extractor just wrote (recent rows only) —
        # the prompt guard filters at extraction, this ENFORCES after it
        enforce_privacy(conn, hours=1)
        return _thread.thread_id
    except Exception as e:
        print(f"[oamp] exchange not recorded: {type(e).__name__}: {str(e)[:120]}")
        return None
