"""Tests for ConsistencyAgent."""

from unittest.mock import MagicMock, patch

import pytest


def _make_agent(samples=3):
    """Create a ConsistencyAgent with mocked internals."""
    with patch("agent_reasoning.agents.consistency.BaseAgent.__init__", return_value=None):
        from agent_reasoning.agents.consistency import ConsistencyAgent

        agent = ConsistencyAgent.__new__(ConsistencyAgent)
        agent.name = "ConsistencyAgent"
        agent.color = "cyan"
        agent.samples = samples
        agent._debug_event = None
        agent._debug_cancelled = False
        agent.client = MagicMock()
        agent.client.generate = MagicMock(
            side_effect=lambda *a, **kw: iter(["Reasoning steps... Final Answer: test answer"])
        )
        return agent


def test_consistency_emits_samples():
    """ConsistencyAgent should emit one sample event per sample."""
    agent = _make_agent(samples=3)
    events = list(agent.stream_structured("What is 2+2?"))

    # Non-update sample events (initial creation of each sample)
    sample_events = [e for e in events if e.event_type == "sample" and not e.is_update]
    # Each sample gets an initial event when RUNNING
    assert len(sample_events) == 3


def test_consistency_voting():
    """When all samples produce the same answer, the vote should be unanimous."""
    agent = _make_agent(samples=3)
    # All samples return the same final answer
    agent.client.generate = MagicMock(
        side_effect=lambda *a, **kw: iter(["Step by step... Final Answer: 42"])
    )

    events = list(agent.stream_structured("What is the meaning of life?"))

    # Check voting_complete event exists
    voting_events = [e for e in events if e.event_type == "voting_complete"]
    assert len(voting_events) == 1

    # Check final answer
    final_events = [e for e in events if e.event_type == "final"]
    assert len(final_events) == 1
    assert final_events[0].data == "42"

    # All 3 unique samples should be winners (objects are mutated in place,
    # so we check the final state of each unique sample id)
    winner_ids = set()
    for e in events:
        if (
            e.event_type == "sample"
            and e.is_update
            and hasattr(e.data, "is_winner")
            and e.data.is_winner
        ):
            winner_ids.add(e.data.id)
    assert len(winner_ids) == 3


def test_consistency_split_vote():
    """When samples disagree, the majority answer should win."""
    agent = _make_agent(samples=3)

    call_count = [0]

    def mock_generate(*a, **kw):
        call_count[0] += 1
        if call_count[0] <= 2:
            return iter(["Reasoning... Final Answer: Paris"])
        else:
            return iter(["Different reasoning... Final Answer: London"])

    agent.client.generate = MagicMock(side_effect=mock_generate)

    events = list(agent.stream_structured("Capital of France?"))

    final_events = [e for e in events if e.event_type == "final"]
    assert len(final_events) == 1
    assert final_events[0].data == "Paris"


def test_consistency_stream_yields_text():
    """ConsistencyAgent.stream() should yield text strings."""
    agent = _make_agent(samples=3)
    chunks = list(agent.stream("test"))
    assert len(chunks) > 0
    assert all(isinstance(c, str) for c in chunks)


def test_consistency_run_returns_string():
    """ConsistencyAgent.run() should return a non-empty string."""
    agent = _make_agent(samples=3)
    result = agent.run("test query")
    assert isinstance(result, str)
    assert len(result) > 0


def test_consistency_configurable_samples():
    """ConsistencyAgent should respect the configured sample count."""
    for n in [2, 4, 5]:
        agent = _make_agent(samples=n)
        events = list(agent.stream_structured("test"))
        sample_starts = [e for e in events if e.event_type == "sample" and not e.is_update]
        assert len(sample_starts) == n


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
