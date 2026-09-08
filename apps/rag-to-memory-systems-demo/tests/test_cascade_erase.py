import secrets
import pytest
from memory.hashing import content_hash
from memory.manager import MemoryManager
from memory.extraction import RuleBasedExtractor
from memory.model import SimulatedModel
from memory.stores.fact import FactStore
from memory.stores.preference import PreferenceStore


@pytest.mark.asyncio
async def test_cascade_erase_revokes_facts_deletes_prefs_writes_audit(db):
    suffix = secrets.token_hex(3)
    tenant = f"ce-{suffix}"
    user = f"u-{suffix}"

    manager = MemoryManager(db, SimulatedModel(), RuleBasedExtractor())
    await PreferenceStore(db).set(user, tenant, "verbosity", "terse", "user_stated", 1.0)
    c = "User uses BigQuery."
    fid = await FactStore(db)._write_unchecked(
        tenant, f"customer:{user}", "tooling", c, content_hash(c),
        "run_s", 0.9, user_id=user,
    )

    await manager.cascade_erase(user, tenant)

    assert await PreferenceStore(db).get(user, tenant, "verbosity") is None
    got = await FactStore(db).get(fid)
    assert got["status"] == "revoked"

    cur = db.cursor()
    await cur.execute(
        "SELECT COUNT(*) FROM deletion_events WHERE user_id = :u_id", u_id=user
    )
    (n,) = await cur.fetchone()
    assert n == 1
