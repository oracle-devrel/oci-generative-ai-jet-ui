"""Tests for AnalogicalAgent."""

from unittest.mock import MagicMock, patch

import pytest


def _make_agent(num_analogies=2):
    """Create an AnalogicalAgent with mocked internals."""
    with patch("agent_reasoning.agents.analogical.BaseAgent.__init__", return_value=None):
        from agent_reasoning.agents.analogical import AnalogicalAgent

        agent = AnalogicalAgent.__new__(AnalogicalAgent)
        agent.name = "AnalogicalAgent"
        agent.color = "yellow"
        agent.num_analogies = num_analogies
        agent.client = MagicMock()
        # Return a fresh iterator for each call to generate()
        agent.client.generate = MagicMock(
            side_effect=lambda *args, **kwargs: iter(["Test response"])
        )
        return agent


def test_analogical_emits_phases():
    agent = _make_agent()
    events = list(agent.stream_structured("How do neural networks learn?"))
    event_types = [e.event_type for e in events]
    assert "analogy" in event_types
    assert "final" in event_types


def test_analogical_run_returns_string():
    agent = _make_agent()
    result = agent.run("test query")
    assert isinstance(result, str)
    assert len(result) > 0


def test_analogical_three_phases():
    """Should go through identify, generate, transfer phases."""
    agent = _make_agent()
    events = list(agent.stream_structured("test"))

    # Track phases as they are emitted by looking at text markers
    text_events = [e.data for e in events if e.event_type == "text"]
    text_blob = "".join(text_events)
    assert "Phase 1: Identifying problem structure" in text_blob
    assert "Phase 2: Generating" in text_blob
    assert "Phase 3: Transferring solution" in text_blob

    # Also verify analogy events exist with non-update for identify and transfer
    analogy_events = [e for e in events if e.event_type == "analogy"]
    assert len(analogy_events) > 0

    # The non-update analogy events mark phase transitions
    non_update = [e for e in analogy_events if not e.is_update]
    # Should have at least 2 non-update analogy events (identify start, transfer start)
    assert len(non_update) >= 2


def test_analogical_stream_yields_text():
    """stream() should yield only text strings."""
    agent = _make_agent()
    chunks = list(agent.stream("test"))
    assert len(chunks) > 0
    assert all(isinstance(c, str) for c in chunks)


def test_analogical_final_event_contains_string():
    """The final event should contain a non-empty string."""
    agent = _make_agent()
    events = list(agent.stream_structured("test"))
    final_events = [e for e in events if e.event_type == "final"]
    assert len(final_events) == 1
    assert isinstance(final_events[0].data, str)
    assert len(final_events[0].data) > 0


def test_analogical_query_event_first():
    """First event should be the query event."""
    agent = _make_agent()
    events = list(agent.stream_structured("my question"))
    assert events[0].event_type == "query"
    assert events[0].data == "my question"


def test_analogical_mapping_fields_populated():
    """AnalogyMapping fields should be populated during streaming."""
    agent = _make_agent()
    events = list(agent.stream_structured("How does gravity work?"))
    analogy_updates = [e for e in events if e.event_type == "analogy" and e.is_update]
    assert len(analogy_updates) > 0
    # At least one update should have abstract_structure populated
    has_structure = any(e.data.abstract_structure for e in analogy_updates)
    assert has_structure


def test_analogical_configurable_num_analogies():
    """num_analogies should be configurable."""
    agent = _make_agent(num_analogies=5)
    assert agent.num_analogies == 5


def test_analogical_four_llm_calls():
    """Should make 4 LLM calls: structure, analogies, transfer, synthesis."""
    agent = _make_agent()
    list(agent.stream_structured("test"))
    assert agent.client.generate.call_count == 4


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
