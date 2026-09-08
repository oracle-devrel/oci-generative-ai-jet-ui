"""Tests for SelfReflectionAgent."""

from unittest.mock import MagicMock, patch

import pytest


def _make_agent():
    """Create a SelfReflectionAgent with mocked internals."""
    with patch("agent_reasoning.agents.self_reflection.BaseAgent.__init__", return_value=None):
        from agent_reasoning.agents.self_reflection import SelfReflectionAgent

        agent = SelfReflectionAgent.__new__(SelfReflectionAgent)
        agent.name = "SelfReflectionAgent"
        agent.color = "green"
        agent._debug_event = None
        agent._debug_cancelled = False
        agent.client = MagicMock()
        agent.client.generate = MagicMock(side_effect=lambda *a, **kw: iter(["CORRECT"]))
        return agent


def test_reflection_emits_iterations():
    """SelfReflectionAgent should emit iteration events."""
    agent = _make_agent()

    # First call: initial draft. Second call: critique passes immediately.
    call_count = [0]

    def mock_generate(*a, **kw):
        call_count[0] += 1
        if call_count[0] == 1:
            return iter(["Draft answer"])
        else:
            return iter(["CORRECT"])

    agent.client.generate = MagicMock(side_effect=mock_generate)

    events = list(agent.stream_structured("test"))
    iteration_events = [e for e in events if e.event_type == "iteration"]
    assert len(iteration_events) > 0


def test_reflection_stops_on_correct():
    """SelfReflectionAgent should stop when critique says CORRECT."""
    agent = _make_agent()

    call_count = [0]

    def mock_generate(*a, **kw):
        call_count[0] += 1
        if call_count[0] == 1:
            return iter(["My answer is 42"])
        else:
            return iter(["CORRECT"])

    agent.client.generate = MagicMock(side_effect=mock_generate)

    events = list(agent.stream_structured("test"))

    # Should have a final event
    final_events = [e for e in events if e.event_type == "final"]
    assert len(final_events) == 1

    # The iteration should be marked as correct
    correct_iterations = [
        e
        for e in events
        if e.event_type == "iteration" and hasattr(e.data, "is_correct") and e.data.is_correct
    ]
    assert len(correct_iterations) >= 1

    # Should only have 2 LLM calls: draft + critique (no improvement needed)
    assert call_count[0] == 2


def test_reflection_multiple_turns():
    """SelfReflectionAgent should iterate through critique/improvement cycles."""
    agent = _make_agent()

    call_count = [0]

    def mock_generate(*a, **kw):
        call_count[0] += 1
        if call_count[0] == 1:
            # Initial draft
            return iter(["First draft"])
        elif call_count[0] == 2:
            # First critique: errors found
            return iter(["Error: the answer is incomplete and needs more detail"])
        elif call_count[0] == 3:
            # First improvement
            return iter(["Improved answer with more detail"])
        elif call_count[0] == 4:
            # Second critique: passes
            return iter(["CORRECT"])
        else:
            return iter(["fallback"])

    agent.client.generate = MagicMock(side_effect=mock_generate)

    events = list(agent.stream_structured("test"))

    # Should have gone through draft -> critique (fail) -> improvement -> critique (pass)
    assert call_count[0] == 4

    final_events = [e for e in events if e.event_type == "final"]
    assert len(final_events) == 1
    assert "Improved answer" in final_events[0].data


def test_reflection_stream_yields_text():
    """SelfReflectionAgent.stream() should yield text strings."""
    agent = _make_agent()

    call_count = [0]

    def mock_generate(*a, **kw):
        call_count[0] += 1
        if call_count[0] == 1:
            return iter(["Draft"])
        else:
            return iter(["CORRECT"])

    agent.client.generate = MagicMock(side_effect=mock_generate)

    chunks = list(agent.stream("test"))
    assert len(chunks) > 0
    assert all(isinstance(c, str) for c in chunks)


def test_reflection_run_returns_string(capsys):
    """SelfReflectionAgent.run() should return a non-empty string."""
    agent = _make_agent()

    call_count = [0]

    def mock_generate(*a, **kw):
        call_count[0] += 1
        if call_count[0] == 1:
            return iter(["The answer is 42"])
        else:
            return iter(["CORRECT"])

    agent.client.generate = MagicMock(side_effect=mock_generate)

    result = agent.run("test query")
    assert isinstance(result, str)
    assert len(result) > 0


def test_reflection_emits_phases():
    """SelfReflectionAgent should emit phase events for draft, critique, and improvement."""
    agent = _make_agent()

    call_count = [0]

    def mock_generate(*a, **kw):
        call_count[0] += 1
        if call_count[0] == 1:
            return iter(["Draft answer"])
        elif call_count[0] == 2:
            return iter(["Error: needs improvement, the logic is flawed"])
        elif call_count[0] == 3:
            return iter(["Better answer"])
        elif call_count[0] == 4:
            return iter(["CORRECT"])
        else:
            return iter(["fallback"])

    agent.client.generate = MagicMock(side_effect=mock_generate)

    events = list(agent.stream_structured("test"))
    phase_events = [e for e in events if e.event_type == "phase"]

    phase_values = [e.data for e in phase_events]
    assert "draft" in phase_values
    assert "critique" in phase_values
    assert "improvement" in phase_values


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
