"""Tests for LeastToMostAgent."""

from unittest.mock import MagicMock, patch

import pytest


def _make_agent():
    """Create a LeastToMostAgent with mocked internals."""
    with patch("agent_reasoning.agents.least_to_most.BaseAgent.__init__", return_value=None):
        from agent_reasoning.agents.least_to_most import LeastToMostAgent

        agent = LeastToMostAgent.__new__(LeastToMostAgent)
        agent.name = "LeastToMostAgent"
        agent.color = "cyan"
        agent._debug_event = None
        agent._debug_cancelled = False
        agent.client = MagicMock()
        agent.client.generate = MagicMock(side_effect=lambda *a, **kw: iter(["Test response"]))
        return agent


def test_least_to_most_stream_yields_text():
    """LeastToMostAgent.stream() should yield text strings (no StreamEvent wrapping)."""
    agent = _make_agent()

    # Mock: first call is decomposition, subsequent calls solve sub-questions
    call_count = [0]

    def mock_generate(*a, **kw):
        call_count[0] += 1
        if call_count[0] == 1:
            return iter(["1. What is X?\n2. How does X relate to Y?"])
        else:
            return iter(["Answer to sub-question"])

    agent.client.generate = MagicMock(side_effect=mock_generate)

    chunks = list(agent.stream("complex question"))
    assert len(chunks) > 0
    assert all(isinstance(c, str) for c in chunks)

    # Should contain the decomposition header text
    full_text = "".join(chunks)
    assert "Least-to-Most" in full_text


def test_least_to_most_run_returns_string():
    """LeastToMostAgent.run() should return a non-empty string."""
    agent = _make_agent()

    call_count = [0]

    def mock_generate(*a, **kw):
        call_count[0] += 1
        if call_count[0] == 1:
            return iter(["1. Sub-question one"])
        else:
            return iter(["The answer"])

    agent.client.generate = MagicMock(side_effect=mock_generate)

    result = agent.run("test query")
    assert isinstance(result, str)
    assert len(result) > 0


def test_least_to_most_processes_subquestions():
    """LeastToMostAgent should call generate once for decomposition plus once per sub-question."""
    agent = _make_agent()

    call_count = [0]

    def mock_generate(*a, **kw):
        call_count[0] += 1
        if call_count[0] == 1:
            # Decomposition: 2 sub-questions
            return iter(["Q1: What is gravity?\nQ2: How does gravity affect tides?"])
        else:
            return iter(["Sub-answer"])

    agent.client.generate = MagicMock(side_effect=mock_generate)

    list(agent.stream("Explain tidal forces"))

    # 1 decomposition call + 2 sub-question calls = 3 total
    assert call_count[0] == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
