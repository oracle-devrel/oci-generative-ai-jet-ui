"""Tests for ReActAgent."""

from unittest.mock import MagicMock, patch

import pytest


def _make_agent():
    """Create a ReActAgent with mocked internals."""
    with patch("agent_reasoning.agents.react.BaseAgent.__init__", return_value=None):
        from agent_reasoning.agents.react import ReActAgent

        agent = ReActAgent.__new__(ReActAgent)
        agent.name = "ReActAgent"
        agent.color = "magenta"
        agent._debug_event = None
        agent._debug_cancelled = False
        agent.client = MagicMock()
        agent.client.generate = MagicMock(
            side_effect=lambda *args, **kwargs: iter(["Test response"])
        )
        return agent


def test_react_emits_query_event():
    """First event from stream_structured should be a query event."""
    agent = _make_agent()
    # Mock a response with Final Answer so it terminates quickly
    agent.client.generate = MagicMock(
        side_effect=lambda *args, **kwargs: iter(["Thought: thinking\nFinal Answer: 42"])
    )

    events = list(agent.stream_structured("What is 6*7?"))
    assert events[0].event_type == "query"
    assert events[0].data == "What is 6*7?"


def test_react_detects_final_answer():
    """ReActAgent should detect 'Final Answer:' and emit a final event."""
    agent = _make_agent()
    agent.client.generate = MagicMock(
        side_effect=lambda *args, **kwargs: iter(["Thought: thinking\nFinal Answer: 42"])
    )

    events = list(agent.stream_structured("What is 6*7?"))
    event_types = [e.event_type for e in events]

    assert "final" in event_types
    final_events = [e for e in events if e.event_type == "final"]
    assert len(final_events) == 1
    assert "42" in final_events[0].data


def test_react_parses_action():
    """ReActAgent should parse 'Action: tool[input]' from LLM response."""
    agent = _make_agent()

    call_count = [0]

    def mock_generate(*args, **kwargs):
        call_count[0] += 1
        if call_count[0] == 1:
            return iter(["Thought: need calc\nAction: calculate[2+2]"])
        else:
            return iter(["Thought: got result\nFinal Answer: 4"])

    agent.client.generate = MagicMock(side_effect=mock_generate)

    events = list(agent.stream_structured("What is 2+2?"))
    event_types = [e.event_type for e in events]

    assert "react_step" in event_types
    # Should have called the tool and gotten an observation
    react_steps = [e for e in events if e.event_type == "react_step"]
    # Find a step with an action set
    steps_with_action = [e for e in react_steps if e.data.action == "calculate"]
    assert len(steps_with_action) > 0
    assert steps_with_action[0].data.action_input == "2+2"


def test_react_calculate_tool():
    """perform_tool_call('calculate', '2+2') should return '4'."""
    agent = _make_agent()
    result = agent.perform_tool_call("calculate", "2+2")
    assert result == "4"


def test_react_calculate_safe():
    """perform_tool_call('calculate', ...) should block dangerous expressions."""
    agent = _make_agent()
    result = agent.perform_tool_call("calculate", "__import__('os')")
    assert "Error" in result


def test_react_unknown_tool():
    """perform_tool_call with an unknown tool should return 'Unknown tool'."""
    agent = _make_agent()
    result = agent.perform_tool_call("unknown_tool", "x")
    assert result == "Unknown tool"


def test_react_stream_yields_text():
    """stream() should yield only text strings."""
    agent = _make_agent()
    agent.client.generate = MagicMock(
        side_effect=lambda *args, **kwargs: iter(["Thought: done\nFinal Answer: yes"])
    )

    chunks = list(agent.stream("test"))
    assert len(chunks) > 0
    assert all(isinstance(c, str) for c in chunks)


def test_react_max_steps():
    """ReActAgent should stop after max_steps (5) even without a Final Answer."""
    agent = _make_agent()
    # Always return a response with no Final Answer and no Action
    agent.client.generate = MagicMock(
        side_effect=lambda *args, **kwargs: iter(["Thought: still thinking, no conclusion yet"])
    )

    events = list(agent.stream_structured("unsolvable question"))
    event_types = [e.event_type for e in events]

    # Should still emit a final event (the fallback at end of loop)
    assert "final" in event_types

    # Count the react_step events that are not updates (one per step)
    non_update_steps = [e for e in events if e.event_type == "react_step" and not e.is_update]
    assert len(non_update_steps) == 5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
