import pytest
from memory.extraction import RuleBasedExtractor
from memory.manager import MemoryManager
from memory.model import SimulatedModel
from memory.promotion import PromotionGate
from memory.records import MemoryCandidate
from memory.stores.fact import FactStore
from memory.stores.preference import PreferenceStore
from memory.stores.episodic import EpisodicStore


@pytest.mark.asyncio
async def test_supersession_writes_new_marks_old_in_one_tx(db):
    fact = FactStore(db)
    manager = MemoryManager(db, SimulatedModel(), RuleBasedExtractor())
    gate = PromotionGate(fact, PreferenceStore(db), EpisodicStore(db), manager)

    v1 = MemoryCandidate(
        memory_type="fact", tenant_id="acme", content="Webhook URL is https://api.acme.com/v1",
        confidence=0.95, source_run_id="run_old",
        subject="customer:jane_sup", predicate="infrastructure",
    )
    v1_result = await gate.promote(v1)
    assert v1_result.outcome == "written"
    old_id = v1_result.record_id

    v2 = MemoryCandidate(
        memory_type="fact", tenant_id="acme", content="Webhook URL is https://api.acme.com/v2",
        confidence=0.95, source_run_id="run_new",
        subject="customer:jane_sup", predicate="infrastructure",
    )
    v2_result = await gate.promote(v2)
    assert v2_result.outcome == "superseded"
    new_id = v2_result.record_id

    old = await fact.get(old_id)
    new = await fact.get(new_id)

    assert old["status"] == "revoked"
    assert old["superseded_by"] == new_id
    # Supersession produces 'active' because it's replacing an already-active
    # fact; the contradiction event itself is a confirmation signal, distinct
    # from a fresh untrusted assertion (which still enters as 'provisional').
    assert new["status"] == "active"
    assert "v2" in new["content"]
