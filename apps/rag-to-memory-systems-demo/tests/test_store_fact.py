import pytest
from memory.stores.fact import FactStore
from memory.hashing import content_hash


@pytest.mark.asyncio
async def test_fact_store_write_and_get(db):
    store = FactStore(db)
    content = "Stripe webhook URL is https://api.acme.com/v1/stripe"
    fid = await store._write_unchecked(
        tenant_id="acme", subject="customer:jane", predicate="infrastructure",
        content=content, content_hash=content_hash(content),
        source_run_id="run_x", confidence=0.95, user_id="customer:jane",
    )
    got = await store.get(fid)
    assert got["subject"] == "customer:jane"
    assert "v1/stripe" in got["content"]
    assert got["status"] == "active"


@pytest.mark.asyncio
async def test_fact_store_find_dedup_in_scope(db):
    store = FactStore(db)
    content = "User runs on-prem in us-east-1"
    h = content_hash(content)
    fid = await store._write_unchecked("acme", "customer:jane", "deployment", content, h, "run_y", 0.9)

    found = await store.find_dedup(h, tenant_id="acme")
    assert found == fid

    not_found = await store.find_dedup(h, tenant_id="other-tenant")
    assert not_found is None


@pytest.mark.asyncio
async def test_fact_store_contradiction(db):
    store = FactStore(db)
    v1 = "Stripe webhook URL is https://api.acme.com/v1/stripe"
    v2 = "Stripe webhook URL is https://api.acme.com/v2/stripe"
    await store._write_unchecked("acme", "customer:jane", "infrastructure", v1, content_hash(v1), "run_a", 0.9)

    contra = await store.find_contradiction(
        "acme", "customer:jane", "infrastructure", content_hash(v2)
    )
    assert contra is not None


@pytest.mark.asyncio
async def test_fact_store_confirm_provisional_to_active(db):
    store = FactStore(db)
    content = "Test confirm"
    fid = await store._write_unchecked(
        "acme", "subj", "pred", content, content_hash(content),
        "run_z", 0.9, status="provisional",
    )
    got = await store.get(fid)
    assert got["status"] == "provisional"

    # confirm() returns True when a row was actually flipped.
    assert await store.confirm(fid) is True
    got = await store.get(fid)
    assert got["status"] == "active"

    # Re-confirming an already-active row is a no-op and returns False.
    assert await store.confirm(fid) is False


@pytest.mark.asyncio
async def test_fact_store_confirm_unknown_id_returns_false(db):
    """The CLI's /confirm used to silently report success on bogus
    ids (e.g., a truncated copy-paste). Now confirm() signals the no-op
    so the caller can surface a useful error."""
    store = FactStore(db)
    assert await store.confirm("fact_does_not_exist") is False
