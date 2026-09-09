"""Real tests for the second brain — true cases against the live database (db.connect()) plus
pure-function unit tests. No LLM calls, so it's fast and deterministic.

  python tests/test_brain.py        # standalone runner (prints PASS/FAIL, exit code)
  pytest tests/test_brain.py        # also works
"""
import asyncio
import os
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "oracle" / "agent"))

import db                # noqa: E402


def _skip_if_empty(c, table, hint):
    """Fresh brains aren't failures: Lab 1 alone leaves these tables empty by design."""
    n = c.cursor().execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    if n == 0:
        c.close()
        raise unittest.SkipTest(f"{table} is empty — {hint}")

import content           # noqa: E402
import memory            # noqa: E402
import semantic_memory   # noqa: E402
import mcp_server        # noqa: E402


# ---- integration: the live brain ----------------------------------------------------------

def test_connect():
    c = db.connect()
    user = c.cursor().execute("SELECT user FROM dual").fetchone()[0]
    assert user, "no DB user"
    c.close()


def test_tables_have_data():
    c = db.connect()
    _skip_if_empty(c, "posts", "load content first (Lab 2 sample or your own), then re-run")
    cur = c.cursor()
    # thresholds work for a real library, the 7-video tutorial sample, or a tiny own-data start
    for t, lo in [("posts", 1), ("content_chunks", 0), ("wiki_pages", 0),
                  ("page_sources", 0), ("semantic_memory", 0)]:
        n = cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        assert n >= lo, f"{t} has {n} rows (< {lo})"
    c.close()


def test_duality_views_readable():
    c = db.connect()
    _skip_if_empty(c, "posts", "load content first (Lab 2), then re-run")
    _skip_if_empty(c, "wiki_pages", "compile the wiki first (Lab 5 / Step 5), then re-run")
    cur = c.cursor()
    cur.execute("SELECT JSON_VALUE(data,'$.topic') FROM wiki_page_dv FETCH FIRST 1 ROWS ONLY")
    assert (cur.fetchone() or [None])[0], "wiki_page_dv not readable"
    cur.execute("SELECT JSON_VALUE(data,'$._id') FROM post_dv FETCH FIRST 1 ROWS ONLY")
    assert cur.fetchone(), "post_dv not readable"
    c.close()


def test_vector_search():
    c = db.connect()
    _skip_if_empty(c, "posts", "load content first (Lab 2), then re-run")
    res = content.search_content(c, "AI inference and the compute stack", 5)
    assert res and {"lvl", "title", "snippet"} <= set(res[0]), "bad search result shape"
    assert any(r["lvl"] == "wiki" for r in res) or len(res) >= 3, "expected layered results"
    c.close()


def test_hybrid_rescues_exact_name():
    """Hybrid search must rescue an exact keyword that vector-only ranking can bury.
    Self-contained + data-independent: seed a post with a unique token, confirm hybrid
    surfaces it by that exact token, then clean up."""
    c = db.connect()
    token = "zqxwvlemma"   # distinctive — won't collide with real content
    cur = c.cursor()
    cur.execute("alter session disable parallel dml")   # Autonomous DB: delete+insert in one txn
    cur.execute("merge into platforms p using (select 'test' id from dual) s "
                "on (p.platform_id=s.id) when not matched then "
                "insert (platform_id, display_name) values ('test','Test')")
    cur.execute("insert into posts (platform_id, kind, title, caption, content_embedding) "
                "values ('test','note', :t, 'probe', vector_embedding(MINILM using :e as data))",
                t=f"{token} exact-match probe", e=token)
    c.commit()
    try:
        res = content.search_hybrid(c, token, 8)
        titles = " ".join((r.get("title") or "") for r in res).lower()
        assert token in titles, "hybrid search missed an exact-token lexical hit"
    finally:
        cur.execute("delete from posts where platform_id = 'test'")
        c.commit()
        c.close()


def test_related_posts_visibility_and_shape():
    """related() must connect by meaning but NEVER across the privacy line: a business-scope
    sibling must not surface as a neighbor, a business-scope anchor must return [] (it must
    not act as a query vector), and a no-embedding anchor is an empty result, not an error."""
    c = db.connect()
    token = "zqxrelprobe"   # distinctive — won't collide with real content
    cur = c.cursor()
    cur.execute("alter session disable parallel dml")
    cur.execute("merge into platforms p using (select 'test' id from dual) s "
                "on (p.platform_id=s.id) when not matched then "
                "insert (platform_id, display_name) values ('test','Test')")
    ids = {}
    for name, vis in [("anchor", "content"), ("sibling", "content"), ("hidden", "business")]:
        out = cur.var(int)
        cur.execute(
            "insert into posts (platform_id, kind, title, caption, visibility, "
            "content_embedding) values ('test','note', :t, 'probe', :v, "
            "vector_embedding(MINILM using :e as data)) returning post_id into :outid",
            t=f"{token} {name}", v=vis, e=f"{token} probe text", outid=out)
        ids[name] = int(out.getvalue()[0])
    out = cur.var(int)
    cur.execute("insert into posts (platform_id, kind, title, caption) "
                "values ('test','note', :t, 'probe') returning post_id into :outid",
                t=f"{token} noembed", outid=out)
    ids["noembed"] = int(out.getvalue()[0])
    c.commit()
    try:
        got = content.related_posts(c, ids["anchor"], k=10)
        got_ids = {r["post_id"] for r in got}
        assert ids["sibling"] in got_ids, "near-identical content sibling not found"
        assert ids["hidden"] not in got_ids, "PRIVACY LEAK: business post surfaced as neighbor"
        assert ids["anchor"] not in got_ids, "anchor returned as its own neighbor"
        assert all({"post_id", "title", "dist"} <= set(r) for r in got), "bad row shape"
        assert content.related_posts(c, ids["hidden"], k=5) == [], \
            "PRIVACY LEAK: business anchor acted as a query vector"
        assert content.related_posts(c, ids["noembed"], k=5) == [], \
            "no-embedding anchor should return [] not error"
    finally:
        cur.execute("delete from posts where platform_id = 'test'")
        c.commit()
        c.close()


def test_graph_data_visibility():
    """The graph payload must not leak private items through citation edges: a business post
    cited by a wiki page appears in neither nodes nor links. Seeded in a transaction and
    rolled back — nothing persists."""
    c = db.connect()
    token = "zqxgraphprobe"
    cur = c.cursor()
    cur.execute("alter session disable parallel dml")
    cur.execute("merge into platforms p using (select 'test' id from dual) s "
                "on (p.platform_id=s.id) when not matched then "
                "insert (platform_id, display_name) values ('test','Test')")
    try:
        pg = cur.var(int)
        cur.execute("insert into wiki_pages (topic, body) values (:t, 'probe body') "
                    "returning page_id into :outid", t=f"{token} topic", outid=pg)
        page_id = int(pg.getvalue()[0])
        ids = {}
        for name, vis in [("pub", "content"), ("priv", "business")]:
            out = cur.var(int)
            cur.execute("insert into posts (platform_id, kind, title, caption, visibility) "
                        "values ('test','note', :t, 'probe', :v) returning post_id into :outid",
                        t=f"{token} {name}", v=vis, outid=out)
            ids[name] = int(out.getvalue()[0])
            cur.execute("insert into page_sources (page_id, post_id) values (:pg, :po)",
                        pg=page_id, po=ids[name])
        g = content.graph_data(c)
        node_ids = {n["id"] for n in g["nodes"]}
        link_ends = {(l["source"], l["target"]) for l in g["links"]}
        assert f"wiki:{token} topic" in node_ids, "seeded topic missing from graph"
        assert f"item:{ids['pub']}" in node_ids, "cited content post missing from graph"
        assert f"item:{ids['priv']}" not in node_ids, "PRIVACY LEAK: business post is a node"
        assert (f"wiki:{token} topic", f"item:{ids['priv']}") not in link_ends, \
            "PRIVACY LEAK: business post reachable via citation edge"
        assert (f"wiki:{token} topic", f"item:{ids['pub']}") in link_ends, \
            "citation edge to content post missing"
    finally:
        c.rollback()
        c.close()


def test_related_topics_visibility():
    """related_topics (semantic neighbors of a wiki topic) must also respect the privacy line:
    a business post must never surface as a topic's nearest item. Sibling of related_posts,
    same filter — pinned separately because it joins wiki_pages to posts, not posts to posts."""
    c = db.connect()
    token = "zqxreltopic"
    cur = c.cursor()
    cur.execute("alter session disable parallel dml")
    cur.execute("merge into platforms p using (select 'test' id from dual) s "
                "on (p.platform_id=s.id) when not matched then "
                "insert (platform_id, display_name) values ('test','Test')")
    try:
        cur.execute("insert into wiki_pages (topic, body, embedding) values (:t, 'probe body', "
                    "vector_embedding(MINILM using :e as data))",
                    t=f"{token} topic", e=f"{token} shared subject")
        ids = {}
        for name, vis in [("pub", "content"), ("priv", "business")]:
            out = cur.var(int)
            cur.execute("insert into posts (platform_id, kind, title, caption, visibility, "
                        "content_embedding) values ('test','note', :t, 'probe', :v, "
                        "vector_embedding(MINILM using :e as data)) returning post_id into :outid",
                        t=f"{token} {name}", v=vis, e=f"{token} shared subject", outid=out)
            ids[name] = int(out.getvalue()[0])
        got = content.related_topics(c, f"{token} topic", k=10)
        got_ids = {r["post_id"] for r in got}
        assert ids["pub"] in got_ids, "content post not found as a topic neighbor"
        assert ids["priv"] not in got_ids, "PRIVACY LEAK: business post surfaced as a topic neighbor"
    finally:
        c.rollback()
        c.close()


def test_get_wiki_page():
    c = db.connect()
    _skip_if_empty(c, "wiki_pages", "compile the wiki first (Lab 5 / Step 5), then re-run")
    topic = content.list_topics(c)[0]
    p = content.get_wiki_page(c, topic)
    assert p and p["body"] and isinstance(p["citations"], list), "wiki page incomplete"
    c.close()


def test_get_post():
    c = db.connect()
    _skip_if_empty(c, "posts", "load content first (Lab 2), then re-run")
    pid = c.cursor().execute("SELECT MIN(post_id) FROM posts").fetchone()[0]
    post = content.get_post(c, pid)
    assert post and "caption" in post, "get_post failed"
    c.close()


def test_memory_recall_shapes():
    c = db.connect()
    assert isinstance(memory.recall(c, "AI inference", k=3), list)
    assert isinstance(semantic_memory.semantic_recall(c, "audience", k=3), list)
    c.close()


def test_episodic_memory_privacy_filter():
    """A research memory that mentions a fee/deal must be tagged business at WRITE time and
    then be unreachable: not via recall(), not in list_recent(). It's stored (structural
    privacy, not deletion) but filtered from every read — same contract as posts.visibility.
    This also protects the agent itself: private memories never resurface in its reasoning."""
    import memory
    c = db.connect()
    cur = c.cursor()
    try:
        memory.record(c, "test-priv", "zqxbizprobe negotiating a $5,000 brand deal fee",
                      "agreed the terms", "none", "success", detail="private")
        memory.record(c, "test-priv", "zqxconprobe notes on vector search",
                      "explained cosine distance", "search", "success", detail="public")
        # recall is content-scope: the business memory never comes back, even queried by its token
        biz = memory.recall(c, "zqxbizprobe", k=10)
        assert not any("zqxbizprobe" in (r.get("task") or "") for r in biz), \
            "PRIVACY LEAK: deal memory returned by recall()"
        con = memory.recall(c, "zqxconprobe", k=10)
        assert any("zqxconprobe" in (r.get("task") or "") for r in con), "content memory not recalled"
        tasks = " ".join(r.get("task") or "" for r in memory.list_recent(c, k=50))
        assert "zqxconprobe" in tasks and "zqxbizprobe" not in tasks, \
            "PRIVACY LEAK: list_recent surfaced a business memory"
        # stored, just tagged — structural privacy, not a delete
        cur.execute("SELECT visibility FROM agent_memory WHERE task LIKE 'zqxbizprobe%'")
        assert (cur.fetchone() or [None])[0] == "business", "deal memory was not tagged business"
    finally:
        cur.execute("DELETE FROM agent_memory WHERE run_id = 'test-priv'")
        c.commit()
        c.close()


def test_conversation_privacy_filter():
    """A dialogue turn mentioning a rate must be tagged business and kept out of both the
    working-memory window (recent_turns) and the Memory view list (list_recent_turns)."""
    import conversation
    c = db.connect()
    cur = c.cursor()
    sess = "test-conv-priv"
    try:
        conversation.record_turn(c, sess, "user", "zqxconvbiz our rate is $2,000 per post")
        conversation.record_turn(c, sess, "user", "zqxconvok what topics do I cover")
        window = " ".join(t["content"] for t in conversation.recent_turns(c, sess, n=10))
        assert "zqxconvok" in window and "zqxconvbiz" not in window, \
            "PRIVACY LEAK: business turn entered the working-memory window"
        listed = " ".join(t["content"] for t in conversation.list_recent_turns(c, k=100))
        assert "zqxconvbiz" not in listed, "PRIVACY LEAK: business turn in list_recent_turns"
    finally:
        cur.execute("DELETE FROM conversations WHERE session_id = :s", s=sess)
        c.commit()
        c.close()


def test_registry_public_file_is_generic():
    """The committed public catalog (web/registry.json, auto-generated by build_registry.py)
    must contain ONLY generic items — private agents live in a separate private JSON that ships
    only on a private deploy. This pins that the public repo never leaks a personal-agent entry."""
    import json as _json
    reg = _json.loads((ROOT / "web" / "registry.json").read_text())
    cats = reg["categories"]
    keys = {c["key"] for c in cats}
    assert {"agents", "tools", "jobs", "sources", "integrations"} <= keys, keys
    for c in cats:
        assert c["items"], "empty category " + c["key"]
        for it in c["items"]:
            assert it.get("name") and "desc" in it and it.get("where"), it
            assert it.get("scope") == "generic", "PUBLIC LEAK: non-generic item in web/registry.json: " + str(it)
            assert "—" not in (it.get("desc") or ""), "em dash in registry copy: " + it["name"]


def test_registry_merges_private_when_present():
    """registry.registry() folds a private JSON into the matching categories (a private deploy)."""
    import registry
    r = registry.registry()
    assert r["categories"] and sum(len(c["items"]) for c in r["categories"]) >= 1


def test_memory_read_functions():
    """The Memory view's read helpers return the expected shapes over all four memory kinds."""
    import memory
    import procedural
    c = db.connect()
    try:
        assert isinstance(memory.list_recent(c, k=3), list)
        counts = memory.memory_counts(c)
        assert set(counts) == {"episodic", "semantic", "conversational", "procedural"}, counts
        assert all(isinstance(v, int) for v in counts.values()), counts
        assert isinstance(semantic_memory.list_facts(c, k=5), list)
        assert isinstance(procedural.list_tools(c), list)
    finally:
        c.close()


def test_mcp_tools_registered():
    async def names():
        tm = getattr(mcp_server.mcp, "_tool_manager", None)
        tools = await (tm.list_tools() if tm else mcp_server.mcp.list_tools())
        return {t.name for t in tools}
    got = asyncio.run(names())
    assert {"search", "fetch", "wiki", "topics", "recent", "related",
            "ingest_note"} <= got, got


def test_related_tool_registered_readonly():
    """related is a READ tool — it must survive MCP_READONLY=1 (which unregisters writes)."""
    import subprocess
    import sys as _sys
    code = (
        "import os, sys, asyncio; os.environ['MCP_READONLY']='1'\n"
        "sys.path.insert(0, 'oracle/agent')\n"
        "import mcp_server\n"
        "tools = sorted(t.name for t in asyncio.run(mcp_server.mcp._list_tools()))\n"
        "print(','.join(tools))\n")
    out = subprocess.run([_sys.executable, "-c", code], capture_output=True, text=True,
                         cwd=str(pathlib.Path(__file__).resolve().parent.parent))
    tools = out.stdout.strip().split(",")
    assert "related" in tools, tools
    assert "ingest_note" not in tools and "save_chat" not in tools, tools


# ---- unit: pure functions -----------------------------------------------------------------

def test_terms_filters_short_tokens():
    assert content._terms("How does AI Inference work?") == ["how", "does", "inference", "work"]


def test_rid_scheme():
    assert content._rid({"lvl": "wiki", "title": "X"}) == "wiki:X"
    assert content._rid({"lvl": "item", "post_id": 5}) == "item:5"


def test_schema_statement_split():
    sys.path.insert(0, str(ROOT / "scripts"))
    import apply_schema
    stmts = apply_schema.statements(
        "-- c\nCREATE TABLE t (a NUMBER);\nINSERT INTO t VALUES (1); -- inline\n")
    assert stmts == ["CREATE TABLE t (a NUMBER)", "INSERT INTO t VALUES (1)"], stmts


def test_schema_rerun_tolerates_seed_duplicate():
    """Re-applying the schema must report 0 errors. Seed rows (wiki_meta) hit ORA-00001
    on a second run, so it belongs in TOLERATE alongside the "already exists" codes.
    ORA-01430 ("column being added already exists") must be tolerated too — the memory
    layer's idempotent `ALTER TABLE agent_memory/conversations ADD (visibility …)` relies
    on it being swallowed on re-apply."""
    sys.path.insert(0, str(ROOT / "scripts"))
    import apply_schema
    assert "ORA-00001" in apply_schema.TOLERATE
    assert "ORA-01430" in apply_schema.TOLERATE


def test_oamp_privacy_deny_patterns():
    """The structural sweep's deny-list (pure — no DB, no LLM, no package import needed):
    private business detail must match; ordinary tech-content phrasing — including '$0'
    and 'pricing' talk with no numbers — must not. Extend the list? Extend this first."""
    from oamp_memory import violates_privacy
    for leak in ("my rate for the deal is $9,876,543",
                 "the fee of 5000 was agreed by email",
                 "their contract has a 999-day exclusivity clause",
                 "four deliverables per quarter",
                 "wire it to the account number on the invoice"):
        assert violates_privacy(leak), f"should flag: {leak!r}"
    for fine in ("the Always Free tier includes two full databases",
                 "this build runs at $0 with no accounts anywhere",
                 "a video about pricing strategies in tech",
                 "published a tutorial about database constraints"):
        assert not violates_privacy(fine), f"false positive: {fine!r}"
    # OAMP_DENY_EXTRA extends the list without code edits — and must not break the defaults
    os.environ["OAMP_DENY_EXTRA"] = r"\bproject codename\b"
    try:
        assert violates_privacy("the project codename is nightingale")
        assert violates_privacy("my rate for the deal is $9,876,543")
        assert not violates_privacy("a video about tech careers")
    finally:
        del os.environ["OAMP_DENY_EXTRA"]


def test_memory_backend_resolver():
    """Default = the package (the honest recommendation); ollama auto-selects the
    hand-built track (its extraction fails silently on small local models); an
    explicit MEMORY_BACKEND always wins, both ways."""
    from research_agent import _resolve_backend
    assert _resolve_backend(None, "anthropic") == "oamp"
    assert _resolve_backend(None, "openai") == "oamp"
    assert _resolve_backend(None, "ollama") == "custom"     # the guard
    assert _resolve_backend("custom", "anthropic") == "custom"   # explicit wins
    assert _resolve_backend("oamp", "ollama") == "oamp"          # explicit wins
    assert _resolve_backend("OAMP", "anthropic") == "oamp"       # case-insensitive


def test_shipped_env_guard_hook():
    """The checked-in .claude/settings.json hook must block *.env edits and allow
    everything else — including .env.example, which is where agents SHOULD write."""
    import json as _json
    import subprocess
    cfg = _json.loads((ROOT / ".claude" / "settings.json").read_text())
    cmd = cfg["hooks"]["PreToolUse"][0]["hooks"][0]["command"]
    for path, want in [("oracle/.env", 2), ("/anywhere/.env", 2),
                       ("oracle/.env.example", 0), ("scripts/sync.py", 0)]:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                           input=_json.dumps({"tool_input": {"file_path": path}}))
        assert r.returncode == want, (path, r.returncode, r.stderr)


def test_loop_ledger_records():
    """record_usage appends a tagged JSONL line and never raises (cost visibility
    must not break a loop)."""
    import json as _json
    import tempfile
    import llm
    old = llm.LEDGER
    try:
        with tempfile.TemporaryDirectory() as td:
            llm.LEDGER = str(pathlib.Path(td) / "ledger.jsonl")
            llm.record_usage("test-model", 10, 20, label="test-loop")
            line = _json.loads(pathlib.Path(llm.LEDGER).read_text().splitlines()[0])
            assert line["label"] == "test-loop" and line["tokens_in"] == 10 \
                and line["tokens_out"] == 20 and line["model"] == "test-model"
            llm.LEDGER = "/nonexistent-dir-that-cannot-be-created\0/x"
            llm.record_usage("m", 1, 1)   # must not raise
    finally:
        llm.LEDGER = old


def test_memory_stale_detector():
    """The forgetting audit flags OLD memories in time-bound present tense — not new
    ones, and not durable facts of any age."""
    sys.path.insert(0, str(ROOT / "scripts"))
    from memory_review import is_stale_candidate
    assert is_stale_candidate("She is currently preparing the video launch", 90)
    assert is_stale_candidate("Working on the deal this month", 61)
    assert not is_stale_candidate("She is currently preparing the launch", 10)  # too new
    assert not is_stale_candidate("Her content centers on AI education", 400)   # durable
    assert not is_stale_candidate("", 400)


def test_backend_resolution_parity():
    """sync.py and oamp_sweep.py must resolve the backend exactly like the agent does,
    or the daily privacy sweep silently skips on configs where extraction runs."""
    from research_agent import _resolve_backend
    sys.path.insert(0, str(ROOT / "scripts"))
    import oamp_sweep
    import sync
    cases = [({}, "anthropic"), ({}, "openai"), ({}, "ollama"),
             ({"MEMORY_BACKEND": "custom"}, "anthropic"),
             ({"MEMORY_BACKEND": "oamp"}, "ollama"),
             ({"MEMORY_BACKEND": "OAMP"}, "anthropic")]
    for env, provider in cases:
        e = dict(env)
        if provider != "anthropic":     # anthropic is both defaults' fallback
            e["LLM_PROVIDER"] = provider
        want = _resolve_backend(env.get("MEMORY_BACKEND"), provider)
        assert sync.resolve_memory_backend(e) == want, (env, provider)
        assert oamp_sweep.resolve_memory_backend(e) == want, (env, provider)


# --- regression tests for the 2026-07 code-review remediation --------------------------------

def test_record_clamps_long_values():
    """A question longer than VARCHAR2(500) must not crash the save (ORA-12899 regression)."""
    c = db.connect()
    cur = c.cursor()
    run_id = "test-clamp"
    try:
        memory.record(c, run_id + "x" * 60, "Q" * 900, "answered", "tool-name" * 30, "success",
                      detail="d")
        cur.execute("SELECT LENGTH(task), LENGTH(run_id), LENGTH(tool) "
                    "FROM agent_memory WHERE run_id LIKE 'test-clamp%'")
        task_len, rid_len, tool_len = cur.fetchone()
        assert task_len <= 500 and rid_len <= 40 and tool_len <= 80
    finally:
        cur.execute("DELETE FROM agent_memory WHERE run_id LIKE 'test-clamp%'")
        c.commit()
        c.close()


def test_clamp_bytes_is_byte_aware():
    """Byte clamp must respect VARCHAR2 byte semantics without splitting a character."""
    f = semantic_memory._clamp_bytes
    emoji = "x" * 998 + "🧠"          # 998 + 4 bytes = 1002 bytes
    out = f(emoji, 1000)
    assert len(out.encode()) <= 1000
    assert not out.endswith("\ufffd") and "🧠" not in out
    assert f("short", 1000) == "short"


def test_set_hwm_survives_missing_seed_row():
    """_set_hwm must MERGE: after the seed row disappears (e.g. a data reset), the
    high-water mark must still advance instead of silently updating 0 rows."""
    import wiki
    c = db.connect()
    cur = c.cursor()
    try:
        # Match the production write paths: disable parallel DML before any DML so the
        # small-table MERGE in _set_hwm doesn't self-deadlock on the Autonomous DB.
        cur.execute("alter session disable parallel dml")
        cur.execute("SELECT last_max_post_id FROM wiki_meta WHERE id = 1")
        before = (cur.fetchone() or [0])[0]
        cur.execute("DELETE FROM wiki_meta")
        wiki._set_hwm(cur, 12345)
        cur.execute("SELECT last_max_post_id FROM wiki_meta WHERE id = 1")
        assert int(cur.fetchone()[0]) == 12345, "MERGE did not re-create the seed row"
    finally:
        c.rollback()   # leave the real row untouched
        c.close()


def test_fetch_title_fallback_keeps_whole_string():
    """Colon-containing titles must fall back to an exact lookup on the WHOLE string."""
    src = open(pathlib.Path(__file__).resolve().parent.parent
               / "oracle" / "agent" / "mcp_server.py").read()
    assert 'title_fallback = str(id).strip()' in src, \
        "fetch fallback regressed to splitting on ':'"


def test_note_chunks_paragraphs():
    """Notes must chunk by paragraph so they get passage-level search like chats do."""
    from content import note_chunks
    body = "How to use: fetch this.\n\nSTEP 1 - do a thing\nwith detail\n\n\nSTEP 2 - more"
    chunks = note_chunks(body)
    assert chunks == ["How to use: fetch this.", "STEP 1 - do a thing\nwith detail",
                      "STEP 2 - more"]
    assert note_chunks("") == [] and note_chunks(None) == []
    long = "\n\n".join(f"p{i}" for i in range(60))
    assert len(note_chunks(long)) == 40          # cap
    assert len(note_chunks("x" * 5000)[0]) == 2000   # per-chunk byte-safe clamp


def test_mcp_public_layout_is_generic():
    """The PUBLIC server must expose exactly the teaching tools — no private workflow tools.
    (Private deploys layer server_ext in; this pins the boundary for forks and wrong builds.)"""
    import asyncio
    import subprocess
    import sys as _sys
    code = (
        "import sys, asyncio; sys.path.insert(0, 'oracle/agent')\n"
        "import mcp_server\n"
        "tools = sorted(t.name for t in asyncio.run(mcp_server.mcp._list_tools()))\n"
        "print(','.join(tools))\n")
    out = subprocess.run([_sys.executable, "-c", code], capture_output=True, text=True,
                         cwd=str(pathlib.Path(__file__).resolve().parent.parent))
    tools = out.stdout.strip().split(",")
    assert tools == ["by_series", "fetch", "ingest_note", "overview", "recent",
                     "related", "save_chat", "search", "source_status", "topics",
                     "wiki"], tools


def _reload_webui(**env):
    """Reload webui.py under a controlled env (it reads UI_* at import). Returns the module."""
    import importlib
    import os as _os
    for k in ("UI_ENABLED", "UI_AUTH_TOKEN", "UI_PUBLIC_READ", "UI_TITLE"):
        _os.environ.pop(k, None)
    _os.environ.update(env)
    import webui
    return importlib.reload(webui)


class _FakeReq:
    def __init__(self, auth=None):
        self.headers = {"authorization": auth} if auth else {}


def test_webui_auth_fails_closed():
    """The /api gate must reject a missing/wrong bearer, accept the exact one, and honor the
    explicit public-read escape hatch. The static server must block path traversal."""
    tok = "x" * 40
    w = _reload_webui(UI_ENABLED="1", UI_AUTH_TOKEN=tok)
    assert w._authorized(_FakeReq(f"Bearer {tok}")) is True
    assert w._authorized(_FakeReq("Bearer wrong")) is False
    assert w._authorized(_FakeReq(None)) is False
    assert w._authorized(_FakeReq(tok)) is False          # missing "Bearer " prefix
    # traversal: a crafted asset path must never escape WEB_DIR
    assert w._static("/assets/../../oracle/.env") is None
    assert w._static("/assets/../mcp_server.py") is None
    # public-read mode: anonymous allowed, but still fail-closed by default above
    wp = _reload_webui(UI_ENABLED="1", UI_PUBLIC_READ="1")
    assert wp._authorized(_FakeReq(None)) is True
    _reload_webui()   # leave webui disabled for the rest of the suite


def test_webui_enable_requires_a_gate():
    """UI_ENABLED with neither a token nor explicit public-read must refuse to start."""
    try:
        _reload_webui(UI_ENABLED="1")
        assert False, "UI_ENABLED with no gate must raise SystemExit"
    except SystemExit:
        pass
    finally:
        _reload_webui()


def test_webui_api_routes_live():
    """End-to-end over the real ASGI app: static shell open, /api gated (401->200), the graph
    endpoint returns {nodes,links}, /health still open, and the UI is dark when UI_ENABLED unset."""
    import importlib
    import os as _os
    from starlette.testclient import TestClient
    _os.environ["MCP_ALLOW_ANON"] = "1"
    tok = "t" * 40
    _reload_webui(UI_ENABLED="1", UI_AUTH_TOKEN=tok)
    import mcp_http
    importlib.reload(mcp_http)
    with TestClient(mcp_http.app) as client:
        assert client.get("/health").status_code == 200           # probe stays open
        assert client.get("/").status_code == 200                 # static shell, no auth
        assert client.get("/api/graph").status_code == 401        # gated without token
        # security headers are structural: on the shell AND on api responses, 200 or 401 alike
        for resp in (client.get("/"), client.get("/api/graph")):
            csp = resp.headers.get("content-security-policy", "")
            assert "script-src 'self'" in csp and "frame-ancestors 'none'" in csp, resp.headers
            assert resp.headers.get("x-content-type-options") == "nosniff", resp.headers
        r = client.get("/api/graph", headers={"authorization": f"Bearer {tok}"})
        assert r.status_code == 200, r.text
        body = r.json()
        assert "nodes" in body and "links" in body, body
        assert client.get("/api/ping",
                          headers={"authorization": f"Bearer {tok}"}).json()["auth"] == "token"
        mem = client.get("/api/memory", headers={"authorization": f"Bearer {tok}"})
        assert mem.status_code == 200, mem.text
        mb = mem.json()
        assert set(mb["counts"]) == {"episodic", "semantic", "conversational", "procedural"}, mb
        assert all(k in mb for k in ("facts", "episodic", "tools", "conversational")), mb
        assert client.get("/api/memory").status_code == 401   # gated like every /api route
        # end-to-end privacy pin: a fee-mentioning memory must not escape via the endpoint
        # (write-tag -> read-filter -> API wiring, all in one assertion)
        import memory as _mem
        _c = db.connect(); _cur = _c.cursor()
        try:
            _mem.record(_c, "test-api-priv", "zqxapibiz our fee is $9,000 for the campaign",
                        "logged", "none", "success", detail="private")
            leak = client.get("/api/memory", headers={"authorization": f"Bearer {tok}"}).text
            assert "zqxapibiz" not in leak, "PRIVACY LEAK: business memory reached /api/memory"
        finally:
            _cur.execute("DELETE FROM agent_memory WHERE run_id = 'test-api-priv'")
            _c.commit(); _c.close()
        # smoke: every no-arg read route answers 200 (catches a route that 500s on wiring)
        for route in ("/api/graph", "/api/topics", "/api/recent", "/api/overview",
                      "/api/status", "/api/memory", "/api/series", "/api/search", "/api/agents"):
            rr = client.get(route, headers={"authorization": f"Bearer {tok}"})
            assert rr.status_code == 200, route + " -> " + str(rr.status_code) + " " + rr.text[:120]
    # dark when disabled: /api 404s, app otherwise unchanged
    _reload_webui()
    importlib.reload(mcp_http)
    with TestClient(mcp_http.app) as client:
        assert client.get("/api/graph").status_code == 404
        assert client.get("/health").status_code == 200


def test_rate_limiter_per_ip_isolation():
    """One noisy IP must not throttle another; the global backstop must still trip."""
    import importlib
    import os as _os
    _os.environ["MCP_ALLOW_ANON"] = "1"
    _os.environ["RATE_BURST"] = "5"
    _os.environ["RATE_PER_SEC"] = "0.001"
    import mcp_http
    importlib.reload(mcp_http)
    b = mcp_http._Bucket()
    assert sum(b.allow("1.1.1.1") for _ in range(10)) == 5
    assert sum(b.allow("2.2.2.2") for _ in range(10)) == 5   # unaffected by IP 1
    assert sum(b.allow("3.3.3.3") for _ in range(10)) == 5
    assert sum(b.allow("4.4.4.4") for _ in range(10)) == 5
    assert sum(b.allow("5.5.5.5") for _ in range(10)) == 0   # global backstop (4x burst) hit
    for k in ("RATE_BURST", "RATE_PER_SEC"):
        del _os.environ[k]


def test_search_cursor_roundtrip():
    """Cursors must survive the round trip and ERROR on a mismatched query (silent page-1
    restarts hand the model duplicates with no signal)."""
    import mcp_server
    tok = mcp_server._encode_cursor("my query", 16)
    assert mcp_server._decode_cursor(tok, "my query") == 16
    try:
        mcp_server._decode_cursor(tok, "different query")
        assert False, "mismatched cursor must raise"
    except Exception:
        pass


def test_output_cap_is_explicit():
    """Truncation must announce itself — silent truncation reads as 'that was everything'."""
    import mcp_server
    big = "x" * (mcp_server._TEXT_CAP + 500)
    capped = mcp_server._cap(big)
    assert len(capped) < len(big) and "truncated" in capped


def test_research_verify_gate_is_wired():
    """The verification pass must sit BEFORE record() (wrong claims must not be remembered),
    default ON, with a graceful fallback if the check itself fails."""
    import research_agent
    src = open(pathlib.Path(__file__).resolve().parent.parent
               / "oracle" / "agent" / "research_agent.py").read()
    assert callable(research_agent.verify_answer)
    assert 'os.environ.get("RESEARCH_VERIFY", "1")' in src, "verify gate no longer default-on"
    assert src.index('verify_answer(client, messages, answer)') < src.index('record(conn, "research"'), \
        "verify pass must run before the answer is recorded to memory"
    for verdict in ("supported", "unsupported", "contradicted"):
        assert verdict in research_agent.VERIFY_SCHEMA["properties"]["claims"]["items"][
            "properties"]["verdict"]["enum"]


def test_research_tool_errors_are_recoverable():
    """Malformed model tool input must return an error RESULT, not raise."""
    import research_agent
    c = db.connect()
    out = research_agent._run_tool(c, "get_post", {"post_id": None})
    assert isinstance(out, dict) and "error" in out
    out = research_agent._run_tool(c, "search_content", {})
    assert isinstance(out, dict) and "error" in out
    c.close()


def test_doc_chunks_covers_long_documents():
    """A book-sized wall of text must chunk with near-full coverage — not truncate
    to the first block (the e-book regression)."""
    text = ("Agents consolidate memory. " * 60 + "\n\n") * 20   # ~34k chars
    blocks = content.doc_chunks(text)
    covered = sum(len(b) for b in blocks)
    assert len(blocks) > 10 and covered > len(text) * 0.9, (len(blocks), covered)


def test_gdrive_routing_skips_media():
    sys.path.insert(0, str(ROOT / "scripts"))
    from gdrive import route
    assert route("application/vnd.google-apps.document", "Editing notes") == ("export", "note")
    assert route("application/pdf", "book.pdf") == ("pdf", "reference")
    assert route("application/epub+zip", "book.epub") == ("epub", "reference")
    assert route("text/plain", "note.txt") == ("text", "note")
    assert route("application/octet-stream", "notes.md") == ("text", "note")
    for mime, name in (("video/mp4", "footage.mp4"), ("image/png", "thumb.png"),
                       ("application/vnd.google-apps.spreadsheet", "tracker"),
                       ("application/vnd.google-apps.folder", "sub")):
        assert route(mime, name) is None, (mime, name)


def test_obsidian_extract_epub():
    import io
    import zipfile
    sys.path.insert(0, str(ROOT / "scripts"))
    from obsidian import extract_epub
    import tempfile, pathlib as pl
    with tempfile.TemporaryDirectory() as d:
        p = pl.Path(d) / "b.epub"
        with zipfile.ZipFile(p, "w") as z:
            z.writestr("OEBPS/c.xhtml",
                       "<html><body><h1>T</h1><p>First para.</p><p>Second para.</p>"
                       "<script>bad()</script></body></html>")
        text = extract_epub(p)
    assert "First para." in text and "Second para." in text
    assert "bad()" not in text and "<" not in text


def test_obsidian_parse_note():
    sys.path.insert(0, str(ROOT / "scripts"))
    from obsidian import parse_note
    meta, body = parse_note("""---
title: My Course Notes
tags: ml, course
visibility: private
---
# Heading
Text with a [[Wiki Link]] and an [[page|aliased link]].""")
    assert meta["title"] == "My Course Notes"
    assert meta["visibility"] == "private"
    assert "Wiki Link" in body and "aliased link" in body
    assert "[[" not in body and "# " not in body
    meta2, body2 = parse_note("no frontmatter at all")
    assert meta2 == {} and body2 == "no frontmatter at all"


# --- pipeline health (heartbeat + verdict): the closed-laptop / silent-skip alarm ------------

def test_health_verdict_states():
    """Pure verdict logic: no heartbeat, fresh-ok, fresh-with-trouble, and too-old runs."""
    import datetime
    import health
    now = datetime.datetime(2026, 7, 11, 12, 0)
    fresh = now - datetime.timedelta(hours=3)
    old = now - datetime.timedelta(hours=50)
    ok_steps = [{"label": "Instagram", "status": "ok", "seconds": 4}]
    bad_steps = [{"label": "Instagram", "status": "skip", "seconds": 0},
                 {"label": "Notion", "status": "ok", "seconds": 2}]
    assert health.verdict(None)["state"] == "no-heartbeat"
    assert health.verdict({"run_at": fresh, "steps": ok_steps}, now)["state"] == "ok"
    v = health.verdict({"run_at": fresh, "steps": bad_steps}, now)
    assert v["state"] == "degraded" and v["trouble"] == ["Instagram: skip"]
    # a step that recorded WHY it skipped/failed carries the reason into the panel
    v = health.verdict({"run_at": fresh, "steps": [
        {"label": "Instagram", "status": "skip",
         "why": "no IG_ACCESS_TOKEN configured"}]}, now)
    assert v["trouble"] == ["Instagram: skip (no IG_ACCESS_TOKEN configured)"]
    assert health.verdict({"run_at": old, "steps": ok_steps}, now)["state"] == "down"
    # expected window is configurable: 50h old is fine on a 72h cadence
    assert health.verdict({"run_at": old, "steps": ok_steps}, now,
                          expected_hours=72)["state"] == "ok"


def test_health_panel_lines():
    """DOWN must say plainly that local capabilities are unavailable; trouble steps listed."""
    import health
    down = health.panel_lines({"state": "down", "hours_since": 49.5,
                               "trouble": ["Instagram: skip"]})
    assert "DOWN" in down[0] and "49.5h" in down[0]
    assert any("unavailable" in ln for ln in down)
    assert any("Instagram: skip" in ln for ln in down)
    assert health.panel_lines({"state": "no-heartbeat", "hours_since": None,
                               "trouble": []})[0].startswith("LOCAL PIPELINE: no heartbeat")


def test_health_heartbeat_roundtrip_live():
    """Live DB: record_run writes a heartbeat that last_heartbeat reads back; the test row
    is removed afterwards so the real panel is untouched."""
    import health
    c = db.connect()
    try:
        try:
            probe = health.last_heartbeat(c)
            with c.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM sync_runs")
        except Exception:
            raise unittest.SkipTest("sync_runs table not applied yet (scripts/apply_schema.py)")
        steps = [{"label": "unit-test", "status": "ok", "seconds": 0}]
        health.record_run(c, steps, host="unit-test")
        hb = health.last_heartbeat(c)
        assert hb is not None and hb["host"] == "unit-test"
        assert hb["steps"] == steps
        assert health.verdict(hb)["state"] == "ok"
        with c.cursor() as cur:   # leave no trace: the panel must reflect real runs only
            cur.execute("DELETE FROM sync_runs WHERE host = 'unit-test'")
        c.commit()
        assert health.last_heartbeat(c) == probe
    finally:
        c.close()
# --- linkedin_apify guards: the self-scrape must never ingest someone else's posts --------

def test_linkedin_apify_parse_guards():
    """Pure parse: foreign authors, short text, and missing URLs are dropped; good
    items come through with allowlisted fields only and a parsed date."""
    sys.path.insert(0, str(ROOT / "scripts"))
    import linkedin_apify as la
    assert la.handle_of("https://www.linkedin.com/in/lindahaviv/") == "lindahaviv"
    assert la.handle_of("https://www.linkedin.com/in/LindaHaviv?x=1") == "lindahaviv"
    assert la.handle_of("https://example.com/nope") == ""
    good = {"author": {"publicIdentifier": "lindahaviv"},
            "linkedinUrl": "https://www.linkedin.com/posts/lindahaviv_abc?utm=x",
            "content": "A real post with plenty of text to pass the minimum bar.",
            "postedAt": {"date": "2026-07-11T16:58:53.581Z"},
            "reactions": ["dropped"], "comments": ["dropped"]}
    foreign = dict(good, author={"publicIdentifier": "someone-else"})
    short = dict(good, content="too short")
    nourl = dict(good, linkedinUrl="")
    out = la.parse_items([good, foreign, short, nourl, "junk"], "lindahaviv")
    assert len(out) == 1
    row = out[0]
    assert sorted(row.keys()) == ["published_at", "text", "title", "url"]
    assert row["url"] == "https://www.linkedin.com/posts/lindahaviv_abc"  # ?utm stripped
    assert row["published_at"].year == 2026
    # all-foreign payload -> parse yields nothing (main() turns that into a hard FAIL)
    assert la.parse_items([foreign], "lindahaviv") == []


if __name__ == "__main__":
    tests = [(n, f) for n, f in sorted(globals().items())
             if n.startswith("test_") and callable(f)]
    passed = failed = skipped = 0
    for n, f in tests:
        try:
            f()
            print(f"  PASS  {n}")
            passed += 1
        except unittest.SkipTest as e:
            print(f"  SKIP  {n}: {e}")
            skipped += 1
        except Exception as e:
            print(f"  FAIL  {n}: {str(e).splitlines()[0]}")
            failed += 1
    tail = f", {skipped} skipped (fine on a fresh brain)" if skipped else ""
    print(f"\n{passed} passed, {failed} failed{tail}")
    sys.exit(1 if failed else 0)
