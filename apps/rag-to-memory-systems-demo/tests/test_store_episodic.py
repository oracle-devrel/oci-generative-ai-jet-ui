import pytest
from memory.stores.episodic import EpisodicStore


@pytest.mark.asyncio
async def test_episode_write_and_get(db):
    store = EpisodicStore(db)
    eid = await store.write(
        tenant_id="acme",
        task_type="support_case",
        title="Stripe webhook signature mismatch after secret rotation",
        summary="User rotated webhook secret in dashboard but kept old secret in env "
                "var. Resolved by updating env var and redeploying.",
        outcome="resolved",
        key_steps=[
            "Confirmed signature verification was failing for all events",
            "Compared dashboard secret to env var",
            "Updated env var, redeployed, verified delivery",
        ],
        source_run_id="run_seed",
    )
    got = await store.get(eid)
    assert got["outcome"] == "resolved"
    assert "secret rotation" in got["title"]
    assert len(got["key_steps"]) == 3
