import pytest
from memory.promotion import compute_status, resolve_scope, PromotionGate
from memory.records import MemoryCandidate
from memory.stores.fact import FactStore
from memory.stores.preference import PreferenceStore
from memory.stores.episodic import EpisodicStore


# Pure-logic tests
def test_compute_status_user_scoped_preference_is_active():
    assert compute_status("user", "preference") == "active"

def test_compute_status_tenant_scoped_fact_is_provisional():
    assert compute_status("tenant", "fact") == "provisional"

def test_compute_status_agent_scoped_fact_is_active():
    assert compute_status("agent", "fact") == "active"

def test_compute_status_episodic_is_active_regardless_of_scope():
    assert compute_status("tenant", "episodic") == "active"
    assert compute_status("user", "episodic") == "active"


# Integration tests
@pytest.mark.asyncio
async def test_gate_writes_fact_with_provisional_status(db):
    gate = PromotionGate(FactStore(db), PreferenceStore(db), EpisodicStore(db))
    cand = MemoryCandidate(
        memory_type="fact", tenant_id="acme", content="Customer uses Snowflake.",
        confidence=0.9, source_run_id="run_x",
        subject="customer:jane", predicate="tooling",
    )
    result = await gate.promote(cand)
    assert result.outcome == "written"
    got = await FactStore(db).get(result.record_id)
    assert got["status"] == "provisional"  # tenant-scoped fact


@pytest.mark.asyncio
async def test_gate_dedups_identical_content_in_same_scope(db):
    gate = PromotionGate(FactStore(db), PreferenceStore(db), EpisodicStore(db))
    cand = MemoryCandidate(
        memory_type="fact", tenant_id="acme", content="Customer uses BigQuery.",
        confidence=0.9, source_run_id="run_a",
        subject="customer:bob", predicate="tooling",
    )
    r1 = await gate.promote(cand)
    r2 = await gate.promote(cand)
    assert r1.outcome == "written"
    assert r2.outcome == "deduplicated"
    assert r2.record_id == r1.record_id


@pytest.mark.asyncio
async def test_gate_rejects_low_confidence_fact(db):
    gate = PromotionGate(FactStore(db), PreferenceStore(db), EpisodicStore(db))
    cand = MemoryCandidate(
        memory_type="fact", tenant_id="acme", content="Probably uses Redis.",
        confidence=0.3, source_run_id="run_b",
        subject="customer:bob_low", predicate="tooling",
    )
    result = await gate.promote(cand)
    assert result.outcome == "rejected"
    assert result.reason == "low_confidence"


@pytest.mark.asyncio
async def test_gate_writes_preference_as_active_immediately(db):
    gate = PromotionGate(FactStore(db), PreferenceStore(db), EpisodicStore(db))
    cand = MemoryCandidate(
        memory_type="preference", tenant_id="acme",
        user_id="customer:jane@example.com",
        content="user wants terse",
        confidence=1.0, source_run_id="run_p",
        pref_key="verbosity", pref_value="terse", source="user_stated",
    )
    result = await gate.promote(cand)
    assert result.outcome == "written"
    pref = await PreferenceStore(db).get("customer:jane@example.com", "acme", "verbosity")
    assert pref["value"] == "terse"


