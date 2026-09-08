"""Tests for CoTAgent."""

from unittest.mock import MagicMock, patch

import pytest


def _make_agent():
    """Create a CoTAgent with mocked internals."""
    with patch("agent_reasoning.agents.cot.BaseAgent.__init__", return_value=None):
        from agent_reasoning.agents.cot import CoTAgent

        agent = CoTAgent.__new__(CoTAgent)
        agent.name = "CoTAgent"
        agent.color = "blue"
        agent._debug_event = None
        agent._debug_cancelled = False
        agent.client = MagicMock()
        agent.client.generate = MagicMock(side_effect=lambda *a, **kw: iter(["Test response"]))
        return agent


def test_cot_emits_query_event_first():
    """First event from stream_structured should be a query event."""
    agent = _make_agent()
    events = list(agent.stream_structured("What is 2+2?"))
    assert events[0].event_type == "query"
    assert events[0].data == "What is 2+2?"


def test_cot_emits_chain_step_events():
    """CoTAgent should emit chain_step events."""
    agent = _make_agent()
    events = list(agent.stream_structured("test"))
    chain_steps = [e for e in events if e.event_type == "chain_step"]
    assert len(chain_steps) > 0


def test_cot_emits_final_event():
    """CoTAgent should emit a final event with the full response."""
    agent = _make_agent()
    events = list(agent.stream_structured("test"))
    final_events = [e for e in events if e.event_type == "final"]
    assert len(final_events) == 1
    assert isinstance(final_events[0].data, str)
    assert len(final_events[0].data) > 0


def test_cot_stream_yields_text():
    """CoTAgent.stream() should yield text strings."""
    agent = _make_agent()
    chunks = list(agent.stream("test"))
    assert len(chunks) > 0
    assert all(isinstance(c, str) for c in chunks)


def test_cot_run_returns_string(capsys):
    """CoTAgent.run() should return a non-empty string."""
    agent = _make_agent()
    result = agent.run("test query")
    assert isinstance(result, str)
    assert len(result) > 0


def test_cot_step_detection():
    """CoTAgent should detect multiple steps in the response and emit new chain_step events."""
    agent = _make_agent()

    # Mock a response containing numbered steps
    response_text = (
        "Step 1: First we analyze the problem. Step 2: Then we solve it. Step 3: Finally we verify."
    )
    agent.client.generate = MagicMock(side_effect=lambda *a, **kw: iter([response_text]))

    events = list(agent.stream_structured("test"))
    chain_steps = [e for e in events if e.event_type == "chain_step" and not e.is_update]
    # Should have at least the initial step plus new steps detected
    assert len(chain_steps) >= 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
