import secrets
import pytest
from memory.extraction import RuleBasedExtractor
from memory.agent_session import AgentSession
from memory.manager import MemoryManager
from memory.model import ModelResponse, SimulatedModel
from memory.records import MemoryCandidate
from memory.stores.policy import PolicyStore


@pytest.mark.asyncio
async def test_handle_turn_writes_trace_and_responds(db):
    suffix = secrets.token_hex(3)
    tenant = f"ht-{suffix}"

    await PolicyStore(db).set_policy(
        tenant, "tone_guardrail", {"forbidden_phrases": []}, "guardrail"
    )

    manager = MemoryManager(db, SimulatedModel(), RuleBasedExtractor())
    session = AgentSession(tenant_id=tenant, user_id=f"u-{suffix}", agent_id="a1")
    response, context, promotions = await manager.handle_turn(session, "hello there")

    assert response.text
    assert any(p["policy_key"] == "tone_guardrail" for p in context.policies)
    events = await manager.trace.get_run(session.run_id)
    assert len(events) >= 2


@pytest.mark.asyncio
async def test_handle_turn_promotes_preference(db):
    """Simulated stack path: SimulatedModel returns candidates=None, so the
    configured extractor (RuleBasedExtractor) runs as a separate step and
    promotes the verbosity preference."""
    suffix = secrets.token_hex(3)
    tenant = f"ht-{suffix}"
    user = f"u-{suffix}"

    manager = MemoryManager(db, SimulatedModel(), RuleBasedExtractor())
    session = AgentSession(tenant_id=tenant, user_id=user, agent_id="a1")
    _, _, promotions = await manager.handle_turn(session, "I prefer terse answers")
    assert any(p.outcome == "written" for p in promotions)
    pref = await manager.preference.get(user, tenant, "verbosity")
    assert pref["value"] == "terse"
    # Provenance: candidates came from the extractor (no combined call here).
    assert manager.last_candidates_source == "extractor"


@pytest.mark.asyncio
async def test_handle_turn_envelope_has_all_six_promotion_fields(db):
    """The trace envelope's promotions[] entries carry the unified
    six-field shape — type, fact_id, confidence, status, outcome,
    reason — so replay can reconstruct both the gate verdict and the
    eventual record state without re-running extraction."""
    suffix = secrets.token_hex(3)
    tenant = f"ht-{suffix}"
    user = f"u-{suffix}"

    manager = MemoryManager(db, SimulatedModel(), RuleBasedExtractor())
    session = AgentSession(tenant_id=tenant, user_id=user, agent_id="a1")
    await manager.handle_turn(session, "I prefer terse answers")

    events = await manager.trace.get_run(session.run_id)
    envelopes = [e for e in events if e["event_type"] == "turn_envelope"]
    assert envelopes, "turn_envelope event was not written"
    promo_entries = envelopes[0]["payload"]["promotions"]
    assert promo_entries, "no promotion entries in envelope"
    entry = promo_entries[0]
    assert set(entry.keys()) == {
        "type", "fact_id", "confidence", "status", "outcome", "reason",
    }
    # Preferences are PK-upserted, always active; envelope reflects that
    # with status=None (no provisional/active distinction).
    assert entry["type"] == "preference"
    assert entry["outcome"] == "written"
    assert entry["fact_id"] is None
    assert entry["status"] is None


class _StubCombinedModel:
    """A stand-in for OpenAIModel that returns pre-baked candidates inline,
    simulating the combined structured-output call. Lets us prove the
    manager routes around the configured extractor when the model already
    produced candidates."""

    def __init__(self, reply: str, candidates: list[MemoryCandidate]):
        self._reply = reply
        self._candidates = candidates

    async def complete(self, prompt_text, user_message, **kwargs):
        return ModelResponse(
            text=self._reply, tool_calls=[],
            input_tokens=100, output_tokens=20,
            candidates=list(self._candidates),
        )


class _RecordingExtractor:
    """A fake extractor that just records whether it was called. Used to
    verify the manager bypasses extraction when the model returned
    candidates inline."""

    def __init__(self):
        self.calls = 0

    def extract(self, **kwargs):
        self.calls += 1
        return []


@pytest.mark.asyncio
async def test_handle_turn_uses_combined_candidates_and_skips_extractor(db):
    """When the model returns candidates inline (the combined-call path),
    MemoryManager.extract_and_promote MUST use them directly and MUST NOT
    invoke the configured extractor. The whole point of the combined call
    is to make exactly one API request per turn — invoking the extractor
    too would defeat it and could also disagree with the model's reply."""
    suffix = secrets.token_hex(3)
    tenant = f"ht-{suffix}"
    user = f"u-{suffix}"

    cand = MemoryCandidate(
        memory_type="preference", tenant_id=tenant, user_id=user,
        content="I prefer terse answers", confidence=0.95,
        source_run_id="run_stub", source_turn_id="0",
        pref_key="verbosity", pref_value="terse", source="inferred",
    )
    model = _StubCombinedModel(reply="Noted — terse mode on.", candidates=[cand])
    extractor = _RecordingExtractor()

    manager = MemoryManager(db, model, extractor)
    session = AgentSession(tenant_id=tenant, user_id=user, agent_id="a1")
    response, _, promotions = await manager.handle_turn(session, "I prefer terse answers")

    # The reply came straight from the model's combined output.
    assert response.text == "Noted — terse mode on."
    # The configured extractor was NOT called.
    assert extractor.calls == 0
    # The candidate from the model was promoted.
    assert any(p.outcome == "written" for p in promotions)
    pref = await manager.preference.get(user, tenant, "verbosity")
    assert pref["value"] == "terse"
    # Provenance: combined call, not separate extractor.
    assert manager.last_candidates_source == "combined"


@pytest.mark.asyncio
async def test_handle_turn_combined_with_empty_candidates_still_bypasses_extractor(db):
    """An empty candidates list is meaningful — it means 'the combined
    call ran, extraction produced nothing'. The extractor MUST still be
    skipped; otherwise we'd be paying for a duplicate API call."""
    suffix = secrets.token_hex(3)
    tenant = f"ht-{suffix}"
    user = f"u-{suffix}"

    model = _StubCombinedModel(reply="Hello!", candidates=[])
    extractor = _RecordingExtractor()
    manager = MemoryManager(db, model, extractor)
    session = AgentSession(tenant_id=tenant, user_id=user, agent_id="a1")
    _, _, promotions = await manager.handle_turn(session, "hi")

    assert promotions == []
    assert extractor.calls == 0
    assert manager.last_candidates_source == "combined"
