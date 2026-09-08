"""Tests for SocraticAgent."""

from unittest.mock import MagicMock, patch

import pytest


def _make_agent(max_questions=3):
    """Create a SocraticAgent with mocked internals."""
    with patch("agent_reasoning.agents.socratic.BaseAgent.__init__", return_value=None):
        from agent_reasoning.agents.socratic import SocraticAgent

        agent = SocraticAgent.__new__(SocraticAgent)
        agent.name = "SocraticAgent"
        agent.color = "cyan"
        agent.max_questions = max_questions
        agent.client = MagicMock()
        # Return a fresh iterator for each call to generate()
        agent.client.generate = MagicMock(
            side_effect=lambda *args, **kwargs: iter(["Test response"])
        )
        return agent


def test_socratic_emits_events():
    """Should emit socratic and final event types."""
    agent = _make_agent()
    events = list(agent.stream_structured("What is justice?"))
    event_types = [e.event_type for e in events]
    assert "socratic" in event_types
    assert "final" in event_types


def test_socratic_run_returns_string():
    """run() should return a non-empty string."""
    agent = _make_agent()
    result = agent.run("test query")
    assert isinstance(result, str)
    assert len(result) > 0


def test_socratic_correct_number_of_question_rounds():
    """Should have exactly max_questions question rounds."""
    agent = _make_agent(max_questions=3)
    events = list(agent.stream_structured("test"))

    # Non-update socratic events mark the start of each round + final synthesis
    non_update_socratic = [e for e in events if e.event_type == "socratic" and not e.is_update]
    # 3 question rounds + 1 synthesis = 4 non-update socratic events
    assert len(non_update_socratic) == 4


def test_socratic_final_synthesis_flag():
    """Final synthesis exchange should have is_final_synthesis=True."""
    agent = _make_agent(max_questions=2)
    events = list(agent.stream_structured("test"))

    socratic_events = [e for e in events if e.event_type == "socratic"]
    # Find the synthesis exchange (non-update with is_final_synthesis)
    synthesis_events = [e for e in socratic_events if not e.is_update and e.data.is_final_synthesis]
    assert len(synthesis_events) == 1
    assert synthesis_events[0].data.question_num == 3  # max_questions + 1


def test_socratic_stream_yields_text():
    """stream() should yield only text strings."""
    agent = _make_agent()
    chunks = list(agent.stream("test"))
    assert len(chunks) > 0
    assert all(isinstance(c, str) for c in chunks)


def test_socratic_query_event_first():
    """First event should be the query event."""
    agent = _make_agent()
    events = list(agent.stream_structured("my question"))
    assert events[0].event_type == "query"
    assert events[0].data == "my question"


def test_socratic_question_text_markers():
    """Should have question round markers in text output."""
    agent = _make_agent(max_questions=2)
    events = list(agent.stream_structured("test"))
    text_events = [e.data for e in events if e.event_type == "text"]
    text_blob = "".join(text_events)
    assert "Question 1/2" in text_blob
    assert "Question 2/2" in text_blob
    assert "Synthesis" in text_blob


def test_socratic_exchange_fields_populated():
    """SocraticExchange fields should be populated during streaming."""
    agent = _make_agent(max_questions=2)
    events = list(agent.stream_structured("What is truth?"))
    socratic_updates = [e for e in events if e.event_type == "socratic" and e.is_update]
    assert len(socratic_updates) > 0
    # At least one update should have question populated
    has_question = any(e.data.question for e in socratic_updates)
    assert has_question
    # At least one update should have answer populated
    has_answer = any(e.data.answer for e in socratic_updates)
    assert has_answer


def test_socratic_narrows_to_populated():
    """Each question round should produce a narrows_to value."""
    agent = _make_agent(max_questions=2)
    events = list(agent.stream_structured("test"))
    # Get the last update for each non-synthesis round
    socratic_updates = [e for e in events if e.event_type == "socratic" and e.is_update]
    # Filter to exchanges that have narrows_to set (from question rounds, not synthesis)
    narrows_updates = [
        e for e in socratic_updates if e.data.narrows_to and not e.data.is_final_synthesis
    ]
    # Should have at least one per question round
    assert len(narrows_updates) >= 2


def test_socratic_configurable_max_questions():
    """max_questions should be configurable."""
    agent = _make_agent(max_questions=7)
    assert agent.max_questions == 7


def test_socratic_llm_calls():
    """Should make 3 LLM calls per question round + 1 for synthesis."""
    agent = _make_agent(max_questions=2)
    list(agent.stream_structured("test"))
    # Per round: question (stream=True) + answer (stream=True) + narrowing (stream=False)
    # Final: synthesis (stream=True)
    # Total: 2 * 3 + 1 = 7
    assert agent.client.generate.call_count == 7


def test_socratic_final_event_contains_string():
    """The final event should contain a non-empty string."""
    agent = _make_agent()
    events = list(agent.stream_structured("test"))
    final_events = [e for e in events if e.event_type == "final"]
    assert len(final_events) == 1
    assert isinstance(final_events[0].data, str)
    assert len(final_events[0].data) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
