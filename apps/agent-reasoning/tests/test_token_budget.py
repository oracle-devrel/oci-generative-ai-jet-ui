"""Tests for token budget system."""

from unittest.mock import MagicMock, patch

import pytest

from agent_reasoning.agents.base import BaseAgent


class _ConcreteAgent(BaseAgent):
    """Minimal concrete subclass for testing BaseAgent methods."""

    def run(self, query):
        return query


def _make_base_agent(max_calls):
    """Create a concrete BaseAgent with budget settings, bypassing OllamaClient."""
    with patch("agent_reasoning.agents.base.OllamaClient"):
        agent = _ConcreteAgent(model="test")
        agent.max_calls = max_calls
        agent._call_count = 0
        return agent


def _make_agent_with_budget(module, class_name, max_calls, **extra):
    with patch(f"agent_reasoning.agents.{module}.BaseAgent.__init__", return_value=None):
        mod = __import__(f"agent_reasoning.agents.{module}", fromlist=[class_name])
        cls = getattr(mod, class_name)
        agent = cls.__new__(cls)
        agent.name = class_name
        agent.color = "white"
        agent._debug_event = None
        agent._debug_cancelled = False
        agent.max_calls = max_calls
        agent._call_count = 0
        agent.client = MagicMock()
        agent.client.generate = MagicMock(side_effect=lambda *a, **kw: iter(["response"]))
        for k, v in extra.items():
            setattr(agent, k, v)
        return agent


class TestBudgetSystem:
    def test_base_check_budget_unlimited(self):
        """None max_calls means unlimited."""
        agent = _make_base_agent(max_calls=None)
        for _ in range(100):
            assert agent._check_budget() is True

    def test_base_check_budget_limited(self):
        """Should return False after exceeding max_calls."""
        agent = _make_base_agent(max_calls=3)
        assert agent._check_budget() is True  # 1
        assert agent._check_budget() is True  # 2
        assert agent._check_budget() is True  # 3
        assert agent._check_budget() is False  # 4 - exceeded

    def test_budget_exceeded_msg(self):
        agent = _make_base_agent(max_calls=5)
        agent._call_count = 6
        assert "6/5" in agent._budget_exceeded_msg

    def test_consistency_respects_budget(self):
        """ConsistencyAgent should stop sampling when budget exceeded."""
        agent = _make_agent_with_budget("consistency", "ConsistencyAgent", max_calls=2, samples=5)
        agent.client.generate = MagicMock(side_effect=lambda *a, **kw: iter(["Final Answer: test"]))
        events = list(agent.stream_structured("test"))
        # With budget of 2, should not complete all 5 samples
        sample_events = [e for e in events if e.event_type == "sample" and not e.is_update]
        assert len(sample_events) < 5

    def test_react_respects_budget(self):
        """ReActAgent should stop after budget exceeded."""
        agent = _make_agent_with_budget("react", "ReActAgent", max_calls=1)
        agent.client.generate = MagicMock(
            side_effect=lambda *a, **kw: iter(["Thought: thinking\nFinal Answer: done"])
        )
        # Consume the generator to trigger budget checks
        list(agent.stream_structured("test"))
        # Should have at most 1 step worth of events
        assert agent._call_count <= 2  # 1 allowed + 1 that triggers exceeded

    def test_unlimited_budget_no_interference(self):
        """None budget should not interfere with agent operation."""
        agent = _make_agent_with_budget(
            "consistency", "ConsistencyAgent", max_calls=None, samples=3
        )
        agent.client.generate = MagicMock(side_effect=lambda *a, **kw: iter(["Final Answer: test"]))
        events = list(agent.stream_structured("test"))
        final = [e for e in events if e.event_type == "final"]
        assert len(final) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
