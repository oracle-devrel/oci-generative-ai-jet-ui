"""Tests for RefinementLoopAgent."""

from unittest.mock import MagicMock, patch

import pytest


def _make_agent(score_threshold=0.9, max_iterations=3):
    """Create a RefinementLoopAgent with mocked internals."""
    with patch("agent_reasoning.agents.refinement_loop.BaseAgent.__init__", return_value=None):
        from agent_reasoning.agents.refinement_loop import RefinementLoopAgent

        agent = RefinementLoopAgent.__new__(RefinementLoopAgent)
        agent.name = "RefinementLoopAgent"
        agent.color = "yellow"
        agent.score_threshold = score_threshold
        agent.max_iterations = max_iterations
        agent._debug_event = None
        agent._debug_cancelled = False
        agent.client = MagicMock()
        agent.client.generate = MagicMock(
            side_effect=lambda *args, **kwargs: iter(["Test response"])
        )
        return agent


def test_refinement_emits_events():
    """stream_structured should emit query, refinement, text, and final events."""
    agent = _make_agent(max_iterations=1)

    call_count = [0]

    def mock_generate(*args, **kwargs):
        call_count[0] += 1
        if call_count[0] == 1:
            # Generator: initial draft
            return iter(["Initial draft content"])
        elif call_count[0] == 2:
            # Critic: high score so it stops
            return iter(["SCORE: 0.95\nFEEDBACK: Looks good"])
        else:
            return iter(["Refined content"])

    agent.client.generate = MagicMock(side_effect=mock_generate)

    events = list(agent.stream_structured("test query"))
    event_types = [e.event_type for e in events]

    assert "query" in event_types
    assert "refinement" in event_types
    assert "text" in event_types
    assert "final" in event_types


def test_refinement_stops_on_high_score():
    """Agent should stop when critic returns score >= threshold."""
    agent = _make_agent(score_threshold=0.9, max_iterations=3)

    call_count = [0]

    def mock_generate(*args, **kwargs):
        call_count[0] += 1
        if call_count[0] == 1:
            return iter(["Initial draft"])
        elif call_count[0] == 2:
            # Critic: high score on first iteration
            return iter(["SCORE: 0.95\nFEEDBACK: Looks good"])
        else:
            return iter(["Should not reach here"])

    agent.client.generate = MagicMock(side_effect=mock_generate)

    events = list(agent.stream_structured("test"))

    # Should have accepted: find refinement event with is_accepted=True
    refinement_events = [e for e in events if e.event_type == "refinement"]
    accepted = [e for e in refinement_events if e.data.is_accepted]
    assert len(accepted) == 1

    # Only 2 LLM calls: generator + critic (no refiner needed)
    assert agent.client.generate.call_count == 2


def test_refinement_continues_on_low_score():
    """Agent should continue refining when score is below threshold."""
    agent = _make_agent(score_threshold=0.9, max_iterations=2)

    call_count = [0]

    def mock_generate(*args, **kwargs):
        call_count[0] += 1
        if call_count[0] == 1:
            return iter(["Initial draft"])
        elif call_count[0] == 2:
            # Critic: low score
            return iter(["SCORE: 0.3\nFEEDBACK: Needs work on accuracy"])
        elif call_count[0] == 3:
            # Refiner
            return iter(["Improved draft"])
        elif call_count[0] == 4:
            # Second critic: high score
            return iter(["SCORE: 0.95\nFEEDBACK: Much better"])
        else:
            return iter(["Extra"])

    agent.client.generate = MagicMock(side_effect=mock_generate)

    events = list(agent.stream_structured("test"))

    # Should have at least one refinement event with low score
    refinement_events = [e for e in events if e.event_type == "refinement"]
    low_score = [e for e in refinement_events if not e.data.is_accepted and e.data.score < 0.9]
    assert len(low_score) >= 1

    # Should eventually accept
    accepted = [e for e in refinement_events if e.data.is_accepted]
    assert len(accepted) == 1

    # 4 LLM calls: generator + critic + refiner + critic
    assert agent.client.generate.call_count == 4


def test_refinement_max_iterations():
    """Agent should stop at max_iterations even with consistently low scores."""
    agent = _make_agent(score_threshold=0.9, max_iterations=2)

    call_count = [0]

    def mock_generate(*args, **kwargs):
        call_count[0] += 1
        if call_count[0] == 1:
            return iter(["Initial draft"])
        elif call_count[0] % 2 == 0:
            # All critic calls return low score
            return iter(["SCORE: 0.3\nFEEDBACK: Still needs work"])
        else:
            # All refiner calls
            return iter(["Slightly improved draft"])

    agent.client.generate = MagicMock(side_effect=mock_generate)

    events = list(agent.stream_structured("test"))
    event_types = [e.event_type for e in events]

    # Should still emit a final event
    assert "final" in event_types

    # Should NOT have any accepted refinement
    refinement_events = [e for e in events if e.event_type == "refinement"]
    accepted = [e for e in refinement_events if e.data.is_accepted]
    assert len(accepted) == 0


def test_refinement_extract_score():
    """_extract_score should parse scores from various formats."""
    agent = _make_agent()

    # Standard format
    assert agent._extract_score("SCORE: 0.85\nFEEDBACK: Good") == 0.85
    # Score of 1.0
    assert agent._extract_score("SCORE: 1.0\nFEEDBACK: Perfect") == 1.0
    # Score of 0
    assert agent._extract_score("SCORE: 0\nFEEDBACK: Bad") == 0.0
    # Fallback to any decimal
    assert agent._extract_score("The quality is 0.7 overall") == 0.7
    # No parseable score: default to 0.5
    assert agent._extract_score("This is unparseable") == 0.5


def test_refinement_extract_feedback():
    """_extract_feedback should parse feedback from critique responses."""
    agent = _make_agent()

    # Standard format
    result = agent._extract_feedback("SCORE: 0.8\nFEEDBACK: Needs more detail")
    assert "Needs more detail" in result

    # No FEEDBACK label: should return the entire critique
    result = agent._extract_feedback("Some general critique text")
    assert result == "Some general critique text"


def test_refinement_stream_yields_text():
    """stream() should yield text strings."""
    agent = _make_agent(max_iterations=1)

    call_count = [0]

    def mock_generate(*args, **kwargs):
        call_count[0] += 1
        if call_count[0] == 1:
            return iter(["Draft content"])
        else:
            return iter(["SCORE: 0.95\nFEEDBACK: Good"])

    agent.client.generate = MagicMock(side_effect=mock_generate)

    chunks = list(agent.stream("test"))
    assert len(chunks) > 0
    assert all(isinstance(c, str) for c in chunks)


def test_refinement_configurable_threshold():
    """score_threshold and max_iterations should be configurable."""
    agent = _make_agent(score_threshold=0.7, max_iterations=5)
    assert agent.score_threshold == 0.7
    assert agent.max_iterations == 5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
