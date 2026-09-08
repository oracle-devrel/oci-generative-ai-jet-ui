"""Tests for AgentChain."""

from unittest.mock import MagicMock, patch

import pytest

from agent_reasoning.chain import AgentChain, ChainResult, ChainStep


class TestAgentChain:
    def test_init_validates_strategies(self):
        """Should raise ValueError for unknown strategies."""
        with pytest.raises(ValueError, match="Unknown strategy"):
            AgentChain(["nonexistent_strategy"])

    def test_init_accepts_valid_strategies(self):
        chain = AgentChain(["cot", "reflection"])
        assert chain.strategies == ["cot", "reflection"]
        assert chain.model == "gemma3:270m"

    def test_run_returns_chain_result(self):
        """Run should return a ChainResult with steps."""
        with patch("agent_reasoning.chain.AGENT_MAP") as mock_map:
            mock_agent = MagicMock()
            mock_agent.stream.return_value = iter(["result text"])
            mock_class = MagicMock(return_value=mock_agent)
            mock_map.__getitem__ = MagicMock(return_value=mock_class)
            mock_map.__contains__ = MagicMock(return_value=True)

            chain = AgentChain.__new__(AgentChain)
            chain.strategies = ["cot"]
            chain.model = "test"

            result = chain.run("test query")
            assert isinstance(result, ChainResult)
            assert result.step_count == 1
            assert result.final_output == "result text"

    def test_run_chains_two_strategies(self):
        """Output of first strategy should feed into second."""
        with patch("agent_reasoning.chain.AGENT_MAP") as mock_map:
            call_count = [0]

            def make_agent(*args, **kwargs):
                agent = MagicMock()
                call_count[0] += 1
                n = call_count[0]
                agent.stream.return_value = iter([f"output_{n}"])
                return agent

            mock_map.__getitem__ = MagicMock(return_value=make_agent)
            mock_map.__contains__ = MagicMock(return_value=True)

            chain = AgentChain.__new__(AgentChain)
            chain.strategies = ["cot", "reflection"]
            chain.model = "test"

            result = chain.run("test query")
            assert result.step_count == 2
            assert result.final_output == "output_2"

    def test_stream_yields_strategy_chunk_tuples(self):
        """Stream should yield (strategy_name, chunk) tuples."""
        with patch("agent_reasoning.chain.AGENT_MAP") as mock_map:
            mock_agent = MagicMock()
            mock_agent.stream.return_value = iter(["c1", "c2"])
            mock_map.__getitem__ = MagicMock(return_value=MagicMock(return_value=mock_agent))
            mock_map.__contains__ = MagicMock(return_value=True)

            chain = AgentChain.__new__(AgentChain)
            chain.strategies = ["cot"]
            chain.model = "test"

            chunks = list(chain.stream("test"))
            assert chunks == [("cot", "c1"), ("cot", "c2")]

    def test_chain_result_properties(self):
        result = ChainResult()
        assert result.step_count == 0
        result.steps.append(ChainStep(strategy="cot", output="test"))
        assert result.step_count == 1

    def test_chain_step_defaults(self):
        step = ChainStep(strategy="tot")
        assert step.output == ""
        assert step.elapsed_ms == 0.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
