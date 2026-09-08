"""Tests for DebateAgent."""

from unittest.mock import MagicMock, patch

import pytest


def _make_judge_response(pro_score=7, con_score=5, winner="PRO"):
    """Helper to create a well-formatted judge response."""
    return (
        f"PRO_SCORE: {pro_score}\n"
        f"CON_SCORE: {con_score}\n"
        f"WINNER: {winner}\n"
        f"COMMENTARY: The PRO side presented stronger evidence."
    )


def _make_agent(rounds=2):
    """Create a DebateAgent with mocked internals."""
    with patch("agent_reasoning.agents.debate.BaseAgent.__init__", return_value=None):
        from agent_reasoning.agents.debate import DebateAgent

        agent = DebateAgent.__new__(DebateAgent)
        agent.name = "DebateAgent"
        agent.color = "red"
        agent.rounds = rounds
        agent.client = MagicMock()
        return agent


def test_debate_agent_emits_correct_events():
    """DebateAgent should emit debate_round events for each round plus a final."""
    agent = _make_agent(rounds=2)

    call_count = [0]

    def mock_generate(prompt, stream=True, **kwargs):
        call_count[0] += 1
        if not stream:
            # Judge call (non-streaming)
            return iter([_make_judge_response()])
        else:
            # PRO, CON, or synthesis (streaming)
            return iter(["Test response"])

    agent.client.generate = MagicMock(side_effect=mock_generate)

    events = list(agent.stream_structured("Is AI conscious?"))
    event_types = [e.event_type for e in events]

    assert "query" in event_types
    assert "debate_round" in event_types
    assert "final" in event_types

    # Should have debate_round events for each round
    debate_events = [e for e in events if e.event_type == "debate_round"]
    assert len(debate_events) > 0

    # Final event should contain a string
    final_events = [e for e in events if e.event_type == "final"]
    assert len(final_events) == 1
    assert isinstance(final_events[0].data, str)


def test_debate_agent_run_returns_string():
    """DebateAgent.run() should return a string."""
    agent = _make_agent(rounds=1)

    def mock_generate(prompt, stream=True, **kwargs):
        if not stream:
            return iter([_make_judge_response()])
        return iter(["Test"])

    agent.client.generate = MagicMock(side_effect=mock_generate)

    result = agent.run("test query")
    assert isinstance(result, str)
    assert len(result) > 0


def test_debate_agent_parses_judge_scores():
    """DebateAgent should correctly parse judge scores from response."""
    agent = _make_agent(rounds=1)

    def mock_generate(prompt, stream=True, **kwargs):
        if not stream:
            return iter([_make_judge_response(pro_score=8, con_score=6, winner="PRO")])
        return iter(["Argument text"])

    agent.client.generate = MagicMock(side_effect=mock_generate)

    events = list(agent.stream_structured("test"))
    debate_rounds = [
        e
        for e in events
        if e.event_type == "debate_round"
        and hasattr(e.data, "winner")
        and e.data.winner is not None
    ]

    assert len(debate_rounds) > 0
    rnd = debate_rounds[0].data
    assert rnd.judge_score_pro == 8.0
    assert rnd.judge_score_con == 6.0
    assert rnd.winner == "pro"


def test_debate_agent_handles_malformed_judge_response():
    """DebateAgent should handle judge responses that don't match expected format."""
    agent = _make_agent(rounds=1)

    def mock_generate(prompt, stream=True, **kwargs):
        if not stream:
            # Malformed judge response with no parseable format
            return iter(["The PRO side did better overall."])
        return iter(["Argument text"])

    agent.client.generate = MagicMock(side_effect=mock_generate)

    events = list(agent.stream_structured("test"))
    debate_rounds = [
        e
        for e in events
        if e.event_type == "debate_round"
        and hasattr(e.data, "winner")
        and e.data.winner is not None
    ]

    assert len(debate_rounds) > 0
    rnd = debate_rounds[0].data
    # Should fall back to defaults
    assert rnd.judge_score_pro == 5.0
    assert rnd.judge_score_con == 5.0
    # Winner should be "pro" since scores are equal (>= comparison)
    assert rnd.winner == "pro"


def test_debate_agent_multiple_rounds():
    """DebateAgent should run the correct number of rounds."""
    num_rounds = 3
    agent = _make_agent(rounds=num_rounds)

    def mock_generate(prompt, stream=True, **kwargs):
        if not stream:
            return iter([_make_judge_response()])
        return iter(["Response chunk"])

    agent.client.generate = MagicMock(side_effect=mock_generate)

    events = list(agent.stream_structured("test"))

    # Count non-update debate_round events (initial + final per round)
    non_update_rounds = [e for e in events if e.event_type == "debate_round" and not e.is_update]
    # Each round emits 2 non-update debate_round events: one at start, one at end
    assert len(non_update_rounds) == num_rounds * 2


def test_debate_stream_yields_text():
    """DebateAgent.stream() should yield text strings."""
    agent = _make_agent(rounds=1)

    def mock_generate(prompt, stream=True, **kwargs):
        if not stream:
            return iter([_make_judge_response()])
        return iter(["chunk1", "chunk2"])

    agent.client.generate = MagicMock(side_effect=mock_generate)

    chunks = list(agent.stream("test"))
    assert len(chunks) > 0
    assert all(isinstance(c, str) for c in chunks)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
