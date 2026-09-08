"""Tests for ReasoningInterceptor."""

from unittest.mock import MagicMock, patch

import pytest


class TestReasoningInterceptor:
    def test_parse_model_strategy(self):
        """Should parse 'model+strategy' format and route to correct agent."""
        from agent_reasoning.interceptor import ReasoningInterceptor

        interceptor = ReasoningInterceptor(host="http://localhost:11434")

        with patch("agent_reasoning.interceptor.AGENT_MAP") as mock_map:
            mock_agent_class = MagicMock()
            mock_agent_instance = MagicMock()
            mock_agent_instance.stream.return_value = iter(["result"])
            mock_agent_class.return_value = mock_agent_instance

            # Make the patched AGENT_MAP behave like a real dict for key lookups
            mock_map.__contains__ = lambda self, key: key in {"cot", "standard"}
            mock_map.__getitem__ = lambda self, key: mock_agent_class

            result = interceptor.generate(model="gemma3+cot", prompt="test", stream=False)

            assert result["done"] is True
            assert result["response"] == "result"

    def test_no_strategy_defaults_to_standard(self):
        """Model name without '+' should use standard strategy."""
        from agent_reasoning.interceptor import ReasoningInterceptor

        interceptor = ReasoningInterceptor(host="http://localhost:11434")

        with patch("agent_reasoning.interceptor.AGENT_MAP") as mock_map:
            mock_agent_class = MagicMock()
            mock_agent_instance = MagicMock()
            mock_agent_instance.stream.return_value = iter(["ok"])
            mock_agent_class.return_value = mock_agent_instance

            mock_map.__contains__ = lambda self, key: True
            mock_map.__getitem__ = lambda self, key: mock_agent_class

            result = interceptor.generate(model="gemma3", prompt="test", stream=False)

            # Should have used "standard" as strategy
            assert result["done"] is True

    def test_unknown_strategy_falls_back_to_standard(self):
        """Unknown strategy should fall back to standard."""
        from agent_reasoning.interceptor import AGENT_MAP

        assert "standard" in AGENT_MAP
        assert "nonexistent_strategy_xyz" not in AGENT_MAP

    def test_agent_map_has_all_strategies(self):
        """AGENT_MAP should contain all expected strategies."""
        from agent_reasoning.interceptor import AGENT_MAP

        required = [
            "standard",
            "cot",
            "tot",
            "react",
            "reflection",
            "consistency",
            "decomposed",
            "least_to_most",
            "refinement",
            "recursive",
            "debate",
            "mcts",
            "analogical",
            "socratic",
            "meta",
        ]
        for strategy in required:
            assert strategy in AGENT_MAP, f"Missing strategy: {strategy}"

    def test_agent_map_aliases(self):
        """AGENT_MAP aliases should resolve to correct classes."""
        from agent_reasoning.interceptor import AGENT_MAP

        assert AGENT_MAP["chain_of_thought"] is AGENT_MAP["cot"]
        assert AGENT_MAP["tree_of_thoughts"] is AGENT_MAP["tot"]
        assert AGENT_MAP["self_reflection"] is AGENT_MAP["reflection"]
        assert AGENT_MAP["auto"] is AGENT_MAP["meta"]
        assert AGENT_MAP["rlm"] is AGENT_MAP["recursive"]
        assert AGENT_MAP["self_consistency"] is AGENT_MAP["consistency"]
        assert AGENT_MAP["ltm"] is AGENT_MAP["least_to_most"]
        assert AGENT_MAP["refinement_loop"] is AGENT_MAP["refinement"]
        assert AGENT_MAP["iterative_refinement"] is AGENT_MAP["refinement"]
        assert AGENT_MAP["adversarial"] is AGENT_MAP["debate"]
        assert AGENT_MAP["monte_carlo"] is AGENT_MAP["mcts"]
        assert AGENT_MAP["analogy"] is AGENT_MAP["analogical"]
        assert AGENT_MAP["questioning"] is AGENT_MAP["socratic"]
        assert AGENT_MAP["pipeline"] is AGENT_MAP["complex_refinement"]
        assert AGENT_MAP["pipeline_refinement"] is AGENT_MAP["complex_refinement"]

    def test_chat_flattens_messages(self):
        """chat() should flatten messages into a prompt string and call generate."""
        from agent_reasoning.interceptor import ReasoningInterceptor

        interceptor = ReasoningInterceptor(host="http://localhost:11434")

        with patch.object(
            interceptor, "generate", return_value={"response": "ok", "done": True}
        ) as mock_gen:
            messages = [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi"},
                {"role": "user", "content": "Question"},
            ]
            interceptor.chat(model="gemma3+cot", messages=messages, stream=False)

            assert mock_gen.called
            call_kwargs = mock_gen.call_args[1]
            prompt = call_kwargs["prompt"]
            # Flattened prompt should contain all message contents
            assert "Hello" in prompt
            assert "Hi" in prompt
            assert "Question" in prompt
            # Should have role labels uppercased
            assert "USER:" in prompt
            assert "ASSISTANT:" in prompt

    def test_chat_appends_assistant_suffix(self):
        """chat() should append 'ASSISTANT: ' at the end of the flattened prompt."""
        from agent_reasoning.interceptor import ReasoningInterceptor

        interceptor = ReasoningInterceptor(host="http://localhost:11434")

        with patch.object(
            interceptor, "generate", return_value={"response": "ok", "done": True}
        ) as mock_gen:
            messages = [{"role": "user", "content": "Hi"}]
            interceptor.chat(model="gemma3+cot", messages=messages, stream=False)

            prompt = mock_gen.call_args[1]["prompt"]
            assert prompt.endswith("ASSISTANT: ")

    def test_stream_generator_yields_dicts(self):
        """_stream_generator should yield dicts with response and done keys."""
        from agent_reasoning.interceptor import ReasoningInterceptor

        interceptor = ReasoningInterceptor(host="http://localhost:11434")

        mock_agent = MagicMock()
        mock_agent.stream.return_value = iter(["chunk1", "chunk2"])
        mock_agent.name = "TestAgent"

        chunks = list(interceptor._stream_generator(mock_agent, "test"))
        assert len(chunks) == 3  # 2 content chunks + 1 done
        assert chunks[0]["response"] == "chunk1"
        assert chunks[0]["done"] is False
        assert chunks[0]["model"] == "TestAgent"
        assert chunks[1]["response"] == "chunk2"
        assert chunks[1]["done"] is False
        assert chunks[2]["done"] is True
        assert chunks[2]["response"] == ""

    def test_generate_stream_true_returns_generator(self):
        """generate() with stream=True should return a generator, not a dict."""
        from agent_reasoning.interceptor import ReasoningInterceptor

        interceptor = ReasoningInterceptor(host="http://localhost:11434")

        with patch("agent_reasoning.interceptor.AGENT_MAP") as mock_map:
            mock_agent_class = MagicMock()
            mock_agent_instance = MagicMock()
            mock_agent_instance.stream.return_value = iter(["hello"])
            mock_agent_instance.name = "TestAgent"
            mock_agent_class.return_value = mock_agent_instance

            mock_map.__contains__ = lambda self, key: True
            mock_map.__getitem__ = lambda self, key: mock_agent_class

            result = interceptor.generate(model="gemma3+cot", prompt="test", stream=True)
            # Should be a generator, not a dict
            import types

            assert isinstance(result, types.GeneratorType)
            chunks = list(result)
            assert any(c["done"] is True for c in chunks)

    def test_generate_non_stream_returns_dict(self):
        """generate() with stream=False should return a dict with model, response, done."""
        from agent_reasoning.interceptor import ReasoningInterceptor

        interceptor = ReasoningInterceptor(host="http://localhost:11434")

        with patch("agent_reasoning.interceptor.AGENT_MAP") as mock_map:
            mock_agent_class = MagicMock()
            mock_agent_instance = MagicMock()
            mock_agent_instance.stream.return_value = iter(["part1", "part2"])
            mock_agent_class.return_value = mock_agent_instance

            mock_map.__contains__ = lambda self, key: True
            mock_map.__getitem__ = lambda self, key: mock_agent_class

            result = interceptor.generate(model="gemma3+cot", prompt="test", stream=False)
            assert isinstance(result, dict)
            assert result["response"] == "part1part2"
            assert result["done"] is True
            assert result["model"] == "gemma3+cot"

    def test_client_alias_exists(self):
        """Client class should be an alias for ReasoningInterceptor."""
        from agent_reasoning.interceptor import Client, ReasoningInterceptor

        assert issubclass(Client, ReasoningInterceptor)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
