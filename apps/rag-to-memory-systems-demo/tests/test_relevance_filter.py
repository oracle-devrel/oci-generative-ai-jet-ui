"""Unit tests for the tier-based relevance filter on PromptContext assembly.

These don't touch the database; they exercise MemoryManager._passes_tier and
the filter logic directly by monkeypatching memory.manager.assemble with a
fake RetrievalResult.
"""
from __future__ import annotations
import asyncio
import pytest

from memory.agent_session import AgentSession
from memory.extraction import RuleBasedExtractor
from memory.manager import MemoryManager
from memory.model import SimulatedModel
from memory.retrieval import RetrievalResult, RetrievedRow


def _fake_result() -> RetrievalResult:
    """A mixed bag covering every tier and kind we care about."""
    return RetrievalResult(
        rows=[
            RetrievedRow(kind="policy", rank_score=None,
                         payload={"policy_key": "refund_threshold", "policy_value": {}}),
            RetrievedRow(kind="preference", rank_score=None,
                         payload={"pref_key": "verbosity", "pref_value": "terse"}),
            RetrievedRow(kind="fact", rank_score=0.85,    # tier=high
                         payload={"fact_id": "f1", "content": "high-fact"}),
            RetrievedRow(kind="fact", rank_score=0.55,    # tier=standard
                         payload={"fact_id": "f2", "content": "std-fact"}),
            RetrievedRow(kind="fact", rank_score=0.30,    # tier=low
                         payload={"fact_id": "f3", "content": "low-fact"}),
            RetrievedRow(kind="episodic", rank_score=0.45,  # tier=low
                         payload={"episode_id": "e1", "summary": "low-ep"}),
            RetrievedRow(kind="trace", rank_score=None,
                         payload={"turn_index": 0, "event_type": "user_msg"}),
        ],
        mode="hybrid",
    )


@pytest.mark.parametrize(
    "floor,expected_fact_ids,expected_episode_ids",
    [
        ("low",      ["f1", "f2", "f3"], ["e1"]),     # no filtering
        ("standard", ["f1", "f2"],       []),         # drop tier=low
        ("high",     ["f1"],             []),         # keep only tier=high
    ],
)
def test_tier_filter_drops_below_floor(monkeypatch, floor, expected_fact_ids, expected_episode_ids):
    async def fake_assemble(*args, **kwargs):
        return _fake_result()
    monkeypatch.setattr("memory.manager.assemble", fake_assemble)

    manager = MemoryManager(
        conn=None,  # never used because assemble is faked
        model=SimulatedModel(),
        extractor=RuleBasedExtractor(),
        min_relevance_tier=floor,
    )
    session = AgentSession(tenant_id="t", user_id="u", agent_id="a")

    ctx = asyncio.run(manager.assemble_context(session, "any query"))

    # Path A and recent trace are never filtered.
    assert [p["policy_key"] for p in ctx.policies] == ["refund_threshold"]
    assert [p["pref_key"] for p in ctx.preferences] == ["verbosity"]
    assert [r["turn_index"] for r in ctx.recent] == [0]

    # Facts and episodes follow the configured floor.
    assert [f["fact_id"] for f in ctx.facts] == expected_fact_ids
    assert [e["episode_id"] for e in ctx.episodes] == expected_episode_ids


def test_invalid_tier_raises():
    with pytest.raises(ValueError, match="min_relevance_tier"):
        MemoryManager(
            conn=None,
            model=SimulatedModel(),
            extractor=RuleBasedExtractor(),
            min_relevance_tier="medium",  # not a valid tier
        )
