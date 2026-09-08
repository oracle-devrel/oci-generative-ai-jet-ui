"""Tests for Reasoning Circuits."""

from unittest.mock import MagicMock, patch

import pytest


def test_circuit_definition():
    from agent_reasoning.circuits import ReasoningCircuit

    circuit = ReasoningCircuit(
        [
            {"step": "decompose", "agent": "decomposed"},
            {"step": "solve_each", "agent": "cot", "parallel": True},
            {"step": "synthesize", "agent": "reflection"},
        ]
    )
    assert len(circuit.steps) == 3
    assert circuit.steps[0]["agent"] == "decomposed"


def test_builtin_templates():
    from agent_reasoning.circuits import CIRCUIT_TEMPLATES

    assert "deep_analysis" in CIRCUIT_TEMPLATES
    assert "robust_answer" in CIRCUIT_TEMPLATES
    assert "creative_exploration" in CIRCUIT_TEMPLATES


def test_from_template():
    from agent_reasoning.circuits import ReasoningCircuit

    circuit = ReasoningCircuit.from_template("deep_analysis")
    assert len(circuit.steps) == 3


def test_from_template_unknown():
    from agent_reasoning.circuits import ReasoningCircuit

    with pytest.raises(ValueError, match="Unknown template"):
        ReasoningCircuit.from_template("nonexistent")


def test_circuit_emits_events():
    """Circuit should emit circuit_node and final events."""
    from agent_reasoning.circuits import ReasoningCircuit

    # Mock agent
    mock_agent = MagicMock()
    mock_agent.name = "MockAgent"
    mock_agent.run.return_value = "mock result"
    mock_agent.stream_structured.return_value = iter(
        [
            MagicMock(event_type="text", data="test"),
            MagicMock(event_type="final", data="mock result"),
        ]
    )

    mock_agent_class = MagicMock(return_value=mock_agent)

    with patch("agent_reasoning.agents.AGENT_MAP", {"cot": mock_agent_class}):
        circuit = ReasoningCircuit([{"step": "solve", "agent": "cot"}])
        events = list(circuit.stream_structured("test query"))
        event_types = [e.event_type for e in events]
        assert "circuit_node" in event_types
        assert "final" in event_types


def test_circuit_parallel_step():
    """Parallel steps should run multiple agents."""
    from agent_reasoning.circuits import ReasoningCircuit

    mock_agent = MagicMock()
    mock_agent.name = "Mock"
    mock_agent.run.return_value = "result"
    mock_agent_class = MagicMock(return_value=mock_agent)

    with patch(
        "agent_reasoning.agents.AGENT_MAP", {"cot": mock_agent_class, "tot": mock_agent_class}
    ):
        circuit = ReasoningCircuit(
            [{"step": "parallel", "agent": ["cot", "tot"], "parallel": True}]
        )
        list(circuit.stream_structured("test"))
        # Should have called run on 2 agents
        assert mock_agent.run.call_count == 2


def test_circuit_run_returns_string():
    from agent_reasoning.circuits import ReasoningCircuit

    mock_agent = MagicMock()
    mock_agent.name = "Mock"
    mock_agent.run.return_value = "final"
    mock_agent.stream_structured.return_value = iter(
        [
            MagicMock(event_type="final", data="final answer"),
        ]
    )
    mock_class = MagicMock(return_value=mock_agent)

    with patch("agent_reasoning.agents.AGENT_MAP", {"cot": mock_class}):
        circuit = ReasoningCircuit([{"step": "s", "agent": "cot"}])
        result = circuit.run("test")
        assert isinstance(result, str)
