import inspect
from unittest.mock import patch

import pytest


def test_base_agent_accepts_kwargs():
    """BaseAgent should accept arbitrary kwargs without crashing."""
    with patch("agent_reasoning.client.OllamaClient"):
        from agent_reasoning.agents.base import BaseAgent

        sig = inspect.signature(BaseAgent.__init__)
        assert any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()), (
            "BaseAgent.__init__ should accept **kwargs"
        )


def test_agent_with_unknown_params_doesnt_crash():
    """Passing unknown params to an agent should not raise TypeError."""
    with patch("agent_reasoning.client.OllamaClient"):
        from agent_reasoning.agents.cot import CoTAgent

        try:
            CoTAgent(model="test", unknown_param=42, another_param="hello")
        except TypeError:
            pytest.fail("Agent should accept unknown kwargs via BaseAgent.__init__ **kwargs")


def test_tot_agent_accepts_width_depth():
    """ToTAgent should accept width and depth kwargs."""
    with patch("agent_reasoning.client.OllamaClient"):
        from agent_reasoning.agents.tot import ToTAgent

        try:
            ToTAgent(model="test", width=3, depth=4)
        except TypeError:
            pytest.fail("ToTAgent should accept width and depth via **kwargs")


def test_standard_agent_accepts_unknown_params():
    """StandardAgent should silently absorb unknown kwargs."""
    with patch("agent_reasoning.client.OllamaClient"):
        from agent_reasoning.agents.standard import StandardAgent

        try:
            StandardAgent(model="test", some_future_param=True)
        except TypeError:
            pytest.fail(
                "StandardAgent should accept unknown kwargs via BaseAgent.__init__ **kwargs"
            )
