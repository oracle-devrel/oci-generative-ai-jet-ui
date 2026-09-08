"""Tests for StandardAgent."""

from unittest.mock import MagicMock, patch

import pytest


def _make_agent():
    """Create a StandardAgent with mocked internals."""
    with patch("agent_reasoning.agents.standard.BaseAgent.__init__", return_value=None):
        from agent_reasoning.agents.standard import StandardAgent

        agent = StandardAgent.__new__(StandardAgent)
        agent.name = "StandardAgent"
        agent.color = "cyan"
        agent._debug_event = None
        agent._debug_cancelled = False
        agent.client = MagicMock()
        agent.client.generate = MagicMock(
            side_effect=lambda *args, **kwargs: iter(["Test response"])
        )
        return agent


def test_standard_stream_yields_text():
    """stream() should yield text strings from the LLM."""
    agent = _make_agent()

    chunks = list(agent.stream("What is Python?"))
    assert len(chunks) > 0
    assert all(isinstance(c, str) for c in chunks)
    assert "Test response" in chunks


def test_standard_run_returns_string():
    """run() should return a concatenated string of all chunks."""
    agent = _make_agent()

    result = agent.run("test query")
    assert isinstance(result, str)
    assert "Test response" in result


def test_standard_multiple_chunks():
    """stream() should yield all chunks from the LLM client."""
    agent = _make_agent()
    agent.client.generate = MagicMock(
        side_effect=lambda *args, **kwargs: iter(["chunk1", "chunk2", "chunk3"])
    )

    chunks = list(agent.stream("test"))
    assert chunks == ["chunk1", "chunk2", "chunk3"]


def test_standard_empty_response():
    """stream() should handle an empty iterator from the LLM client."""
    agent = _make_agent()
    agent.client.generate = MagicMock(side_effect=lambda *args, **kwargs: iter([]))

    chunks = list(agent.stream("test"))
    assert chunks == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
