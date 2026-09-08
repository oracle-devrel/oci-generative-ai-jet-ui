import pytest
from memory.stores.policy import PolicyStore
from memory.stores.preference import PreferenceStore


@pytest.mark.asyncio
async def test_policy_store_set_and_get(db):
    store = PolicyStore(db)
    await store.set_policy(
        tenant_id="acme",
        policy_key="refund_threshold",
        policy_value={"max_auto_approve_usd": 500},
        policy_type="approval",
    )
    got = await store.get("acme", "refund_threshold")
    assert got["value"] == {"max_auto_approve_usd": 500}
    assert got["type"] == "approval"


@pytest.mark.asyncio
async def test_policy_store_list_for_tenant(db):
    store = PolicyStore(db)
    await store.set_policy("acme", "k1", {"a": 1}, "compliance")
    await store.set_policy("acme", "k2", {"b": 2}, "guardrail")
    rows = await store.list_for_tenant("acme")
    keys = {r["key"] for r in rows}
    assert {"k1", "k2"}.issubset(keys)


@pytest.mark.asyncio
async def test_preference_store_upsert(db):
    store = PreferenceStore(db)
    await store.set("u1", "acme", "verbosity", "terse", "user_stated", 1.0)
    got = await store.get("u1", "acme", "verbosity")
    assert got["value"] == "terse"

    # Upsert overwrites
    await store.set("u1", "acme", "verbosity", "verbose", "user_stated", 0.9)
    got = await store.get("u1", "acme", "verbosity")
    assert got["value"] == "verbose"
    assert got["confidence"] == 0.9
