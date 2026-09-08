"""Tests for RecursiveAgent."""

from unittest.mock import MagicMock, patch

import pytest


def _make_agent():
    """Create a RecursiveAgent with mocked internals."""
    with patch("agent_reasoning.agents.recursive.BaseAgent.__init__", return_value=None):
        from agent_reasoning.agents.recursive import RecursiveAgent

        agent = RecursiveAgent.__new__(RecursiveAgent)
        agent.name = "RecursiveAgent"
        agent.color = "cyan"
        agent._debug_event = None
        agent._debug_cancelled = False
        agent.client = MagicMock()
        agent.client.generate = MagicMock(
            side_effect=lambda *args, **kwargs: iter(["Test response"])
        )
        return agent


def test_recursive_stream_yields_text():
    """stream() should yield text strings."""
    agent = _make_agent()
    # Return a code block that sets FINAL_ANSWER
    agent.client.generate = MagicMock(
        side_effect=lambda *args, **kwargs: iter(
            ['Thought: Simple question.\n```python\nFINAL_ANSWER = "hello"\n```']
        )
    )

    chunks = list(agent.stream("say hello"))
    assert len(chunks) > 0
    assert all(isinstance(c, str) for c in chunks)


def test_recursive_executes_code():
    """RecursiveAgent should execute code blocks and find FINAL_ANSWER."""
    agent = _make_agent()
    agent.client.generate = MagicMock(
        side_effect=lambda *args, **kwargs: iter(
            ['Thought: Calculate it.\n```python\nFINAL_ANSWER = "hello"\n```']
        )
    )

    chunks = list(agent.stream("say hello"))
    combined = "".join(chunks)
    # Should contain the final answer
    assert "hello" in combined
    # Should contain the "FINAL ANSWER FOUND" marker
    assert "FINAL ANSWER FOUND" in combined


def test_recursive_handles_no_code_block():
    """RecursiveAgent should handle LLM responses with no code block."""
    agent = _make_agent()
    # First call: no code block. Subsequent calls: also no code block.
    # Agent should continue through steps and eventually hit max.
    agent.client.generate = MagicMock(
        side_effect=lambda *args, **kwargs: iter(["Just some plain text thinking, no code here."])
    )

    chunks = list(agent.stream("test"))
    combined = "".join(chunks)
    # Should indicate no code block was found
    assert "No code block found" in combined


def test_recursive_max_steps():
    """RecursiveAgent should stop after max_steps (8) without FINAL_ANSWER."""
    agent = _make_agent()
    # Return code that never sets FINAL_ANSWER
    agent.client.generate = MagicMock(
        side_effect=lambda *args, **kwargs: iter(
            ["Thought: Working on it.\n```python\nx = 42\n```"]
        )
    )

    chunks = list(agent.stream("unsolvable"))
    combined = "".join(chunks)
    # Should hit the max steps message
    assert "Max steps reached" in combined
    # Should have gone through multiple steps
    assert "Step 8" in combined


def test_recursive_sub_llm():
    """_sub_llm should call client.generate and return the concatenated response."""
    agent = _make_agent()
    agent.client.generate = MagicMock(side_effect=lambda *args, **kwargs: iter(["part1", "part2"]))

    result = agent._sub_llm("test prompt")
    assert result == "part1part2"
    agent.client.generate.assert_called_once_with("test prompt", stream=True)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
