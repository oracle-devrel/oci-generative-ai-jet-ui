import secrets
import pytest
from memory.retrieval import assemble
from memory.stores.policy import PolicyStore
from memory.stores.fact import FactStore
from memory.hashing import content_hash
from memory.startup import lexical_available, schema_ready


@pytest.mark.asyncio
async def test_lexical_available_probe(db):
    # Just check the probe runs without error and returns a bool.
    # The actual value depends on the environment.
    result = await lexical_available(db)
    assert isinstance(result, bool)


@pytest.mark.asyncio
async def test_schema_ready_returns_true_when_tables_exist(db):
    """The conftest fixture provisions the schema; schema_ready should
    confirm all six demo tables are present."""
    ok, missing = await schema_ready(db)
    assert ok is True
    assert missing == []


@pytest.mark.asyncio
async def test_vector_only_mode_still_returns_facts(db):
    suffix = secrets.token_hex(3)
    tenant = f"vo-test-{suffix}"
    user = f"u-{suffix}"

    await PolicyStore(db).set_policy(tenant, "k", {"v": 1}, "approval")
    c = "Customer prefers asynchronous notifications via webhook"
    await FactStore(db)._write_unchecked(
        tenant, "customer:jane", "preference_signal", c, content_hash(c),
        "run_seed", 0.9, user_id=user,
    )

    result = await assemble(
        db, tenant_id=tenant, user_id=user, run_id=f"run-{suffix}",
        query_text="webhook", mode="vector",
    )
    assert result.mode == "vector"
    facts = result.by_kind("fact")
    assert len(facts) >= 1


@pytest.mark.asyncio
async def test_like_mode_returns_facts_with_substring_match(db):
    """The last-resort tier: pure INSTR substring match. Works even when
    neither Oracle Text nor the embedding model is available, so this
    test should pass regardless of the test environment's index state."""
    suffix = secrets.token_hex(3)
    tenant = f"like-test-{suffix}"
    user = f"u-{suffix}"

    c = "Customer rotated their Stripe webhook secret last Tuesday"
    await FactStore(db)._write_unchecked(
        tenant, "customer:jane", "infrastructure", c, content_hash(c),
        "run_seed", 0.9, user_id=user,
    )

    # The LIKE heuristic picks the longest word ≥3 chars as the
    # substring; "webhook" appears verbatim in the seeded fact above.
    result = await assemble(
        db, tenant_id=tenant, user_id=user, run_id=f"run-{suffix}",
        query_text="webhook", mode="like",
    )
    assert result.mode == "like"
    facts = result.by_kind("fact")
    assert len(facts) >= 1
    # rank_score is NULL in like mode → tier "standard"
    assert all(f.rank_score is None for f in facts)
