import secrets
import pytest
from memory.retrieval import assemble
from memory.stores.policy import PolicyStore
from memory.stores.preference import PreferenceStore
from memory.stores.fact import FactStore
from memory.stores.episodic import EpisodicStore
from memory.stores.trace import TraceStore
from memory.hashing import content_hash


@pytest.fixture
async def seeded(db):
    """Seed a small tenant with unique IDs for retrieval tests."""
    suffix = secrets.token_hex(3)
    tenant = f"retr-test-{suffix}"
    user = f"u-{suffix}"
    run = f"run-{suffix}"

    await PolicyStore(db).set_policy(
        tenant, "refund_threshold", {"max_auto_approve_usd": 500}, "approval"
    )
    await PreferenceStore(db).set(
        user, tenant, "verbosity", "terse", "user_stated", 1.0
    )
    c1 = "Stripe webhook URL is https://api.acme.com/v1/stripe"
    await FactStore(db)._write_unchecked(
        tenant, "customer:jane", "infrastructure", c1, content_hash(c1),
        run, 0.95, status="active", user_id=user,
    )
    await EpisodicStore(db).write(
        tenant, "support_case",
        "Stripe webhook signature mismatch", "Resolved by updating env var.",
        "resolved", ["confirmed signature failure", "updated env var"],
        run,
    )
    await TraceStore(db).write(
        run, tenant, user, 0, "user_msg", {"text": "hi"}
    )
    yield {"tenant": tenant, "user": user, "run": run}


@pytest.mark.asyncio
async def test_unified_retrieval_returns_all_kinds(db, seeded):
    result = await assemble(
        db, tenant_id=seeded["tenant"], user_id=seeded["user"],
        run_id=seeded["run"], query_text="stripe webhook",
    )
    counts = result.counts()
    assert counts.get("policy", 0) >= 1
    assert counts.get("preference", 0) >= 1
    assert counts.get("fact", 0) >= 1
    assert counts.get("episodic", 0) >= 1
    assert counts.get("trace", 0) >= 1


@pytest.mark.asyncio
async def test_unified_retrieval_scope_filters_out_other_tenants(db, seeded):
    other = f"other-{secrets.token_hex(3)}"
    c = "Webhook URL is https://other.example.com"
    await FactStore(db)._write_unchecked(
        other, "customer:x", "infrastructure", c, content_hash(c),
        "run_other", 0.95,
    )
    result = await assemble(db, seeded["tenant"], seeded["user"], seeded["run"], "webhook URL")
    contents = [r.payload.get("content", "") for r in result.by_kind("fact")]
    assert all("other.example.com" not in (c or "") for c in contents)


@pytest.mark.asyncio
async def test_episode_hybrid_picks_up_lexical_term_in_summary(db):
    """Hybrid retrieval on episode summaries: a verbatim ticket-style
    token that vector similarity might not surface should still hit
    via the lexical CTE. Mirrors the fact-memory hybrid pattern."""
    suffix = secrets.token_hex(3)
    tenant = f"ep-hybrid-{suffix}"
    user = f"u-{suffix}"
    run = f"run-{suffix}"

    # A distinctive identifier the user will search for verbatim. Vector
    # similarity on a generic phrase like "STRIPE-1247" is weak; lexical
    # match should rescue the result.
    await EpisodicStore(db).write(
        tenant, "support_case",
        "Escalation on STRIPE-1247 webhook signature",
        "Customer rotated webhook secret; ticket STRIPE-1247 routed to tier 2 and resolved by env-var redeploy.",
        "resolved",
        ["compared dashboard secret to env var", "redeployed", "verified delivery"],
        run,
    )

    result = await assemble(
        db, tenant_id=tenant, user_id=user, run_id=run,
        query_text="STRIPE-1247",
    )
    episodes = result.by_kind("episodic")
    assert len(episodes) >= 1
    # The fused rank score should be populated (not None) — lexical hit
    # alone is enough to put a score on the row.
    assert episodes[0].rank_score is not None
