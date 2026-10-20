"""The memory store: the package client, the configured model, and what importing memory loads."""

import subprocess
import sys
import uuid

import pytest

from golestan_code_mcp.memory import store


# --- the package client (T006) ---


def test_client_requires_the_migrated_store(conn):
    missing = f"ZZ{uuid.uuid4().hex[:8].upper()}"
    with pytest.raises(ValueError, match="ccctx db migrate"):
        store.client(conn, store_id=missing)
    with conn.cursor() as cur:
        assert cur.execute("select count(*) from user_tables where table_name like :p",
                           p=f"{missing}%").fetchone()[0] == 0


def test_client_writes_reads_and_searches_facts(conn):
    repo = f"t-{uuid.uuid4().hex[:8]}"
    mem = store.client(conn)
    try:
        fid = mem.add_memory("`spin_widget` spins a widget.", memory_type="fact", user_id=repo, agent_id=store.AGENT,
                             metadata={"subject_key": "k"}, ttl_days=None, autonomous_linking=False)
        assert [r.id for r in mem.list_memories(user_id=repo, agent_id=store.AGENT, limit=None)] == [fid]
        hits = mem.search("how do widgets spin", user_id=repo, agent_id=store.AGENT, record_types=["fact"],
                          max_results=5)
        assert [h.id for h in hits] == [fid]
    finally:
        mem.delete_user(repo, cascade=True)
    assert mem.list_memories(user_id=repo, limit=None) == []


def test_no_model_configured_means_no_llm():
    assert store.model({}) is None
    assert store.model({"CCCTX_MEMORY_MODEL": " "}) is None


def test_configured_model_gets_a_package_llm():
    llm, name = store.model({"CCCTX_MEMORY_MODEL": "ollama/qwen3"})
    assert name == "llm:ollama/qwen3"
    assert type(llm).__module__.startswith("oracleagentmemory")


def test_importing_memory_does_not_import_the_package():
    code = ("import sys, golestan_code_mcp.memory.consolidate, golestan_code_mcp.memory.recall, "
            "golestan_code_mcp.memory.recheck, golestan_code_mcp.memory.runs, golestan_code_mcp.server; "
            "print('oracleagentmemory' in sys.modules)")
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True).stdout.strip()
    assert out == "False"
