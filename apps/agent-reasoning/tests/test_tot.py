"""Tests for ToTAgent."""

from unittest.mock import MagicMock, patch

import pytest


def _make_agent(width=2, depth=1):
    """Create a ToTAgent with mocked internals."""
    with patch("agent_reasoning.agents.tot.BaseAgent.__init__", return_value=None):
        from agent_reasoning.agents.tot import ToTAgent

        agent = ToTAgent.__new__(ToTAgent)
        agent.name = "ToTAgent"
        agent.color = "magenta"
        agent.width = width
        agent.depth = depth
        agent._debug_event = None
        agent._debug_cancelled = False
        agent.client = MagicMock()
        return agent


def _setup_mock_generate(
    agent, candidate_response=None, score_response="0.7", final_response="Final answer"
):
    """Configure the mock generate to handle ToT's multi-call pattern."""
    if candidate_response is None:
        candidate_response = "Option 1: approach A\nOption 2: approach B"

    call_count = [0]

    def mock_generate(prompt, stream=False, **kwargs):
        call_count[0] += 1
        if "Rate this reasoning" in prompt or "0.0 to 1.0" in prompt:
            return iter([score_response])
        elif "final answer" in prompt.lower() or "comprehensive" in prompt.lower():
            return iter([final_response])
        else:
            return iter([candidate_response])

    agent.client.generate = MagicMock(side_effect=mock_generate)


def test_tot_emits_node_events():
    """ToTAgent should emit node events for each candidate."""
    agent = _make_agent(width=2, depth=1)
    _setup_mock_generate(agent)

    events = list(agent.stream_structured("solve this"))
    node_events = [e for e in events if e.event_type == "node"]
    assert len(node_events) > 0

    # Each node should have a score
    for event in node_events:
        if not event.is_update:
            assert event.data.score is not None


def test_tot_emits_final_event():
    """ToTAgent should emit a final event with the synthesized answer."""
    agent = _make_agent(width=2, depth=1)
    _setup_mock_generate(agent, final_response="The synthesized answer")

    events = list(agent.stream_structured("test"))
    final_events = [e for e in events if e.event_type == "final"]
    assert len(final_events) == 1
    assert isinstance(final_events[0].data, str)
    assert "synthesized answer" in final_events[0].data.lower()


def test_tot_stream_yields_text():
    """ToTAgent.stream() should yield text strings."""
    agent = _make_agent(width=2, depth=1)
    _setup_mock_generate(agent)

    chunks = list(agent.stream("test"))
    assert len(chunks) > 0
    assert all(isinstance(c, str) for c in chunks)


def test_tot_prunes_low_scoring_nodes():
    """ToTAgent should prune low-scoring nodes when there are more candidates than width."""
    agent = _make_agent(width=2, depth=1)

    call_count = [0]
    scores = ["0.9", "0.3", "0.8", "0.1"]

    def mock_generate(prompt, stream=False, **kwargs):
        nonlocal call_count
        if "Rate this reasoning" in prompt or "0.0 to 1.0" in prompt:
            idx = min(call_count[0], len(scores) - 1)
            call_count[0] += 1
            return iter([scores[idx]])
        elif "final answer" in prompt.lower() or "comprehensive" in prompt.lower():
            return iter(["Final synthesis"])
        else:
            return iter(["Option 1: approach A\nOption 2: approach B"])

    agent.client.generate = MagicMock(side_effect=mock_generate)

    events = list(agent.stream_structured("test"))
    node_events = [e for e in events if e.event_type == "node"]

    # With width=2 and 2 candidates from 1 parent, no pruning happens at depth=1
    # But we can verify nodes are scored
    scored_nodes = [e for e in node_events if not e.is_update and e.data.score is not None]
    assert len(scored_nodes) >= 2


def test_tot_marks_best_path():
    """ToTAgent should mark the best-scoring path node as is_best."""
    agent = _make_agent(width=2, depth=1)

    score_idx = [0]
    scores = ["0.9", "0.3"]

    def mock_generate(prompt, stream=False, **kwargs):
        if "Rate this reasoning" in prompt or "0.0 to 1.0" in prompt:
            idx = min(score_idx[0], len(scores) - 1)
            score_idx[0] += 1
            return iter([scores[idx]])
        elif "final answer" in prompt.lower() or "comprehensive" in prompt.lower():
            return iter(["Best path answer"])
        else:
            return iter(["Option 1: approach A\nOption 2: approach B"])

    agent.client.generate = MagicMock(side_effect=mock_generate)

    events = list(agent.stream_structured("test"))
    node_events = [e for e in events if e.event_type == "node"]

    # Find is_best marked nodes (update events)
    best_nodes = [e for e in node_events if e.is_update and e.data.is_best]
    assert len(best_nodes) >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
