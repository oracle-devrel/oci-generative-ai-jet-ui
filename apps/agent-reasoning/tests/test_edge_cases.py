"""Edge case and battle-hardening tests."""

from unittest.mock import MagicMock, patch

import pytest


class TestEmptyInputs:
    """Test all agents handle empty/None inputs gracefully."""

    def _make_generic_agent(self, agent_module, agent_class_name, **extra_fields):
        with patch(
            f"agent_reasoning.agents.{agent_module}.BaseAgent.__init__",
            return_value=None,
        ):
            mod = __import__(f"agent_reasoning.agents.{agent_module}", fromlist=[agent_class_name])
            cls = getattr(mod, agent_class_name)
            agent = cls.__new__(cls)
            agent.name = agent_class_name
            agent.color = "white"
            agent._debug_event = None
            agent._debug_cancelled = False
            agent.client = MagicMock()
            agent.client.generate = MagicMock(side_effect=lambda *a, **kw: iter(["response"]))
            for k, v in extra_fields.items():
                setattr(agent, k, v)
            return agent

    def test_cot_empty_query(self):
        agent = self._make_generic_agent("cot", "CoTAgent")
        events = list(agent.stream_structured(""))
        assert any(e.event_type == "final" for e in events)

    def test_consistency_empty_query(self):
        agent = self._make_generic_agent("consistency", "ConsistencyAgent", samples=2)
        agent.client.generate = MagicMock(
            side_effect=lambda *a, **kw: iter(["Final Answer: empty"])
        )
        events = list(agent.stream_structured(""))
        assert any(e.event_type == "final" for e in events)

    def test_decomposed_empty_query(self):
        agent = self._make_generic_agent("decomposed", "DecomposedAgent")
        events = list(agent.stream_structured(""))
        assert any(e.event_type == "final" for e in events)

    def test_standard_empty_query(self):
        agent = self._make_generic_agent("standard", "StandardAgent")
        chunks = list(agent.stream(""))
        assert len(chunks) >= 0  # Should not crash

    def test_least_to_most_empty_query(self):
        agent = self._make_generic_agent("least_to_most", "LeastToMostAgent")
        chunks = list(agent.stream(""))
        assert len(chunks) >= 0

    def test_tot_empty_query(self):
        agent = self._make_generic_agent("tot", "ToTAgent", width=1, depth=1)
        events = list(agent.stream_structured(""))
        assert any(e.event_type == "final" for e in events)

    def test_self_reflection_empty_query(self):
        agent = self._make_generic_agent("self_reflection", "SelfReflectionAgent")
        # Make the critique say CORRECT so it terminates fast
        agent.client.generate = MagicMock(side_effect=lambda *a, **kw: iter(["CORRECT"]))
        events = list(agent.stream_structured(""))
        assert any(e.event_type == "final" for e in events)

    def test_refinement_empty_query(self):
        agent = self._make_generic_agent(
            "refinement_loop",
            "RefinementLoopAgent",
            score_threshold=0.9,
            max_iterations=1,
        )
        # Return a high score so it accepts on first pass
        agent.client.generate = MagicMock(
            side_effect=lambda *a, **kw: iter(["SCORE: 0.95\nFEEDBACK: Good"])
        )
        events = list(agent.stream_structured(""))
        assert any(e.event_type == "final" for e in events)

    def test_react_empty_query(self):
        agent = self._make_generic_agent("react", "ReActAgent")
        agent.client.generate = MagicMock(
            side_effect=lambda *a, **kw: iter(["Final Answer: nothing"])
        )
        events = list(agent.stream_structured(""))
        assert any(e.event_type == "final" for e in events)


class TestMalformedLLMResponses:
    """Test agents handle garbage LLM outputs gracefully."""

    def _make_agent_with_response(
        self, agent_module, agent_class_name, response_text, **extra_fields
    ):
        with patch(
            f"agent_reasoning.agents.{agent_module}.BaseAgent.__init__",
            return_value=None,
        ):
            mod = __import__(f"agent_reasoning.agents.{agent_module}", fromlist=[agent_class_name])
            cls = getattr(mod, agent_class_name)
            agent = cls.__new__(cls)
            agent.name = agent_class_name
            agent.color = "white"
            agent._debug_event = None
            agent._debug_cancelled = False
            agent.client = MagicMock()
            agent.client.generate = MagicMock(side_effect=lambda *a, **kw: iter([response_text]))
            for k, v in extra_fields.items():
                setattr(agent, k, v)
            return agent

    def test_tot_garbage_score(self):
        """ToT should handle unparseable scores gracefully."""
        agent = self._make_agent_with_response(
            "tot", "ToTAgent", "garbage no score here !!!", width=2, depth=1
        )
        events = list(agent.stream_structured("test"))
        # Should fall back to 0.1 score, not crash
        node_events = [e for e in events if e.event_type == "node"]
        assert len(node_events) > 0
        for e in node_events:
            assert e.data.score == 0.1  # Default fallback score

    def test_consistency_no_final_answer(self):
        """Consistency should handle responses without 'Final Answer:' line."""
        agent = self._make_agent_with_response(
            "consistency",
            "ConsistencyAgent",
            "Just some text without final answer marker",
            samples=2,
        )
        events = list(agent.stream_structured("test"))
        final_events = [e for e in events if e.event_type == "final"]
        assert len(final_events) == 1
        assert final_events[0].data == "Unknown"  # Fallback

    def test_refinement_unparseable_score(self):
        """RefinementLoop should handle critiques without parseable scores."""
        agent = self._make_agent_with_response(
            "refinement_loop",
            "RefinementLoopAgent",
            "This is terrible, no score provided",
            score_threshold=0.9,
            max_iterations=2,
        )
        events = list(agent.stream_structured("test"))
        # Should not crash, should fall back to 0.5 score
        assert any(e.event_type == "final" for e in events)

    def test_react_malformed_action(self):
        """ReAct should handle malformed action syntax."""
        # First call returns malformed action, which won't match the regex.
        # Second call returns Final Answer to terminate.
        call_count = [0]

        def side_effect(*a, **kw):
            call_count[0] += 1
            if call_count[0] == 1:
                text = (
                    "Thought: I need to do something\n"
                    "Action: badformat without brackets\n"
                    "Final Answer: fallback"
                )
                return iter([text])
            return iter(["Final Answer: done"])

        agent = self._make_agent_with_response(
            "react",
            "ReActAgent",
            "",  # Will be overridden
        )
        agent.client.generate = MagicMock(side_effect=side_effect)
        events = list(agent.stream_structured("test"))
        # Should find Final Answer on the first step (it's in the same response)
        final_events = [e for e in events if e.event_type == "final"]
        assert len(final_events) == 1

    def test_self_reflection_never_correct(self):
        """SelfReflection should stop after max_turns even if never CORRECT."""
        agent = self._make_agent_with_response(
            "self_reflection",
            "SelfReflectionAgent",
            "This needs improvement, errors found everywhere",
        )
        events = list(agent.stream_structured("test"))
        # Should emit a final event even after exhausting turns
        assert any(e.event_type == "final" for e in events)

    def test_react_no_action_no_final_answer(self):
        """ReAct should handle responses with neither Action nor Final Answer."""
        agent = self._make_agent_with_response(
            "react",
            "ReActAgent",
            "Just rambling text with no structure at all",
        )
        events = list(agent.stream_structured("test"))
        # Should still produce a final event after max_steps exhausted
        final_events = [e for e in events if e.event_type == "final"]
        assert len(final_events) == 1

    def test_consistency_all_different_answers(self):
        """Consistency should handle when every sample gives a different answer."""
        call_count = [0]

        def side_effect(*a, **kw):
            call_count[0] += 1
            return iter([f"Final Answer: answer_{call_count[0]}"])

        with patch(
            "agent_reasoning.agents.consistency.BaseAgent.__init__",
            return_value=None,
        ):
            from agent_reasoning.agents.consistency import ConsistencyAgent

            agent = ConsistencyAgent.__new__(ConsistencyAgent)
            agent.name = "ConsistencyAgent"
            agent.color = "cyan"
            agent.samples = 3
            agent._debug_event = None
            agent._debug_cancelled = False
            agent.client = MagicMock()
            agent.client.generate = MagicMock(side_effect=side_effect)

        events = list(agent.stream_structured("test"))
        final_events = [e for e in events if e.event_type == "final"]
        assert len(final_events) == 1
        # Each answer got 1 vote, Counter.most_common picks one
        assert final_events[0].data.startswith("answer_")

    def test_tot_single_option_response(self):
        """ToT should handle when LLM doesn't split into multiple options."""
        agent = self._make_agent_with_response(
            "tot",
            "ToTAgent",
            "Just one single thought without Option markers",
            width=2,
            depth=1,
        )
        events = list(agent.stream_structured("test"))
        # Should still produce nodes and a final event
        assert any(e.event_type == "final" for e in events)
        node_events = [e for e in events if e.event_type == "node"]
        assert len(node_events) >= 1


class TestRefinementScoreParsing:
    """Detailed tests for score extraction edge cases."""

    def _make_refinement_agent(self):
        with patch(
            "agent_reasoning.agents.refinement_loop.BaseAgent.__init__",
            return_value=None,
        ):
            from agent_reasoning.agents.refinement_loop import RefinementLoopAgent

            agent = RefinementLoopAgent.__new__(RefinementLoopAgent)
            agent.name = "RefinementLoopAgent"
            agent.color = "yellow"
            agent.score_threshold = 0.9
            agent.max_iterations = 3
            agent._debug_event = None
            agent._debug_cancelled = False
            agent.client = MagicMock()
            return agent

    def test_extract_score_standard_format(self):
        agent = self._make_refinement_agent()
        assert agent._extract_score("SCORE: 0.85\nFEEDBACK: Good") == 0.85

    def test_extract_score_integer_one(self):
        agent = self._make_refinement_agent()
        assert agent._extract_score("SCORE: 1\nFEEDBACK: Perfect") == 1.0

    def test_extract_score_integer_zero(self):
        agent = self._make_refinement_agent()
        assert agent._extract_score("SCORE: 0\nFEEDBACK: Bad") == 0.0

    def test_extract_score_no_match(self):
        agent = self._make_refinement_agent()
        assert agent._extract_score("No score here at all") == 0.5

    def test_extract_score_embedded_decimal(self):
        """Should find a decimal number even without SCORE: prefix."""
        agent = self._make_refinement_agent()
        assert agent._extract_score("The quality is 0.75 out of 1.0") == 0.75

    def test_extract_score_leading_dot(self):
        """Should handle scores like '.85' via the regex pattern."""
        agent = self._make_refinement_agent()
        result = agent._extract_score("SCORE: .85\nFEEDBACK: Ok")
        assert result == 0.85

    def test_extract_score_case_insensitive(self):
        """Score: label matching should be case insensitive."""
        agent = self._make_refinement_agent()
        assert agent._extract_score("score: 0.6\nfeedback: meh") == 0.6

    def test_extract_feedback_standard(self):
        agent = self._make_refinement_agent()
        result = agent._extract_feedback("SCORE: 0.5\nFEEDBACK: Needs more detail")
        assert "Needs more detail" in result

    def test_extract_feedback_fallback(self):
        """When no FEEDBACK: label found, return the entire critique."""
        agent = self._make_refinement_agent()
        result = agent._extract_feedback("Just some critique text")
        assert result == "Just some critique text"

    def test_extract_feedback_multiline(self):
        """FEEDBACK: should capture multiline content (DOTALL)."""
        agent = self._make_refinement_agent()
        critique = "SCORE: 0.5\nFEEDBACK: First issue\nSecond issue\nThird issue"
        result = agent._extract_feedback(critique)
        assert "First issue" in result
        assert "Second issue" in result
        assert "Third issue" in result

    def test_extract_score_1_0_format(self):
        """Should parse '1.0' correctly."""
        agent = self._make_refinement_agent()
        assert agent._extract_score("SCORE: 1.0\nFEEDBACK: Perfect") == 1.0


class TestReActToolSafety:
    """Test ReAct tool execution safety."""

    def _make_react_agent(self):
        with patch("agent_reasoning.agents.react.BaseAgent.__init__", return_value=None):
            from agent_reasoning.agents.react import ReActAgent

            agent = ReActAgent.__new__(ReActAgent)
            agent.name = "ReActAgent"
            agent.color = "magenta"
            agent._debug_event = None
            agent._debug_cancelled = False
            agent.client = MagicMock()
            return agent

    def test_calculate_safe_eval(self):
        agent = self._make_react_agent()
        assert agent.perform_tool_call("calculate", "2 + 3") == "5"

    def test_calculate_blocks_builtins(self):
        """Should prevent access to __builtins__ for code injection."""
        agent = self._make_react_agent()
        result = agent.perform_tool_call("calculate", "__import__('os').system('echo pwned')")
        assert "Error" in result

    def test_calculate_math_expressions(self):
        agent = self._make_react_agent()
        assert agent.perform_tool_call("calculate", "abs(-5)") == "5"
        assert agent.perform_tool_call("calculate", "max(1, 2, 3)") == "3"
        assert agent.perform_tool_call("calculate", "round(3.14159, 2)") == "3.14"

    def test_calculate_min(self):
        agent = self._make_react_agent()
        assert agent.perform_tool_call("calculate", "min(10, 5, 8)") == "5"

    def test_unknown_tool(self):
        agent = self._make_react_agent()
        assert agent.perform_tool_call("delete_everything", "now") == "Unknown tool"

    def test_calculate_division(self):
        agent = self._make_react_agent()
        assert agent.perform_tool_call("calculate", "10 / 3") == str(10 / 3)

    def test_calculate_integer_division(self):
        agent = self._make_react_agent()
        assert agent.perform_tool_call("calculate", "10 // 3") == "3"

    def test_calculate_power(self):
        agent = self._make_react_agent()
        assert agent.perform_tool_call("calculate", "2 ** 10") == "1024"

    def test_calculate_blocks_open(self):
        """Should block file system access via open()."""
        agent = self._make_react_agent()
        result = agent.perform_tool_call("calculate", "open('/etc/passwd').read()")
        assert "Error" in result

    def test_calculate_blocks_eval(self):
        """Should block nested eval() calls."""
        agent = self._make_react_agent()
        result = agent.perform_tool_call("calculate", "eval('1+1')")
        assert "Error" in result

    def test_calculate_blocks_exec(self):
        """Should block exec() calls."""
        agent = self._make_react_agent()
        result = agent.perform_tool_call("calculate", "exec('x=1')")
        assert "Error" in result

    def test_calculate_division_by_zero(self):
        """Should return error message for division by zero, not crash."""
        agent = self._make_react_agent()
        result = agent.perform_tool_call("calculate", "1/0")
        assert "Error" in result

    def test_calculate_complex_expression(self):
        agent = self._make_react_agent()
        assert agent.perform_tool_call("calculate", "(2 + 3) * 4 - 1") == "19"

    def test_search_fallback_db(self):
        """search tool should fall back to local DB when Wikipedia fails."""
        agent = self._make_react_agent()
        # requests is imported locally inside perform_tool_call, so patch at module level
        with patch.dict("sys.modules", {"requests": MagicMock()}) as _:
            import sys

            mock_req = sys.modules["requests"]
            mock_req.get.side_effect = Exception("No network")
            result = agent.perform_tool_call("search", "python")
            assert "Python" in result or "python" in result.lower()


class TestRecursiveAgentSafety:
    """Test RecursiveAgent code execution edge cases."""

    def _make_recursive_agent(self, response_text):
        with patch("agent_reasoning.agents.recursive.BaseAgent.__init__", return_value=None):
            from agent_reasoning.agents.recursive import RecursiveAgent

            agent = RecursiveAgent.__new__(RecursiveAgent)
            agent.name = "RecursiveAgent"
            agent.color = "cyan"
            agent._debug_event = None
            agent._debug_cancelled = False
            agent.client = MagicMock()
            agent.client.generate = MagicMock(side_effect=lambda *a, **kw: iter([response_text]))
            return agent

    def test_no_code_block(self):
        """Should handle responses without any code block gracefully."""
        agent = self._make_recursive_agent("Thought: I don't know how to write code for this.")
        chunks = list(agent.stream("test"))
        text = "".join(chunks)
        assert "No code block found" in text

    def test_code_execution_error(self):
        """Should catch and report code execution errors."""
        agent = self._make_recursive_agent(
            'Thought: let me try\n```python\nraise ValueError("test error")\n```'
        )
        chunks = list(agent.stream("test"))
        text = "".join(chunks)
        assert "Error" in text or "error" in text.lower()

    def test_final_answer_found(self):
        """Should stop when FINAL_ANSWER is set."""
        agent = self._make_recursive_agent('Thought: easy\n```python\nFINAL_ANSWER = "42"\n```')
        chunks = list(agent.stream("What is the answer?"))
        text = "".join(chunks)
        assert "42" in text
        assert "FINAL ANSWER FOUND" in text

    def test_max_steps_exhausted(self):
        """Should stop after max_steps if FINAL_ANSWER never set."""
        agent = self._make_recursive_agent("Thought: still thinking\n```python\nx = 1\n```")
        chunks = list(agent.stream("test"))
        text = "".join(chunks)
        assert "Max steps reached" in text


class TestStreamEventSerialization:
    """Test StreamEvent.to_dict() for NDJSON streaming."""

    def test_text_event_serialization(self):
        from agent_reasoning.visualization.models import StreamEvent

        event = StreamEvent(event_type="text", data="hello")
        d = event.to_dict()
        assert d["event_type"] == "text"
        assert d["data"] == "hello"
        assert d["is_update"] is False

    def test_node_event_serialization(self):
        from agent_reasoning.visualization.models import StreamEvent, TreeNode

        node = TreeNode(id="A1", depth=1, content="test", score=0.8)
        event = StreamEvent(event_type="node", data=node)
        d = event.to_dict()
        assert d["event_type"] == "node"
        assert isinstance(d["data"], dict)
        assert d["data"]["id"] == "A1"
        assert d["data"]["score"] == 0.8

    def test_update_flag_serialization(self):
        from agent_reasoning.visualization.models import StreamEvent

        event = StreamEvent(event_type="text", data="update", is_update=True)
        d = event.to_dict()
        assert d["is_update"] is True

    def test_enum_field_serialization(self):
        from agent_reasoning.visualization.models import (
            ReActStep,
            StreamEvent,
            TaskStatus,
        )

        step = ReActStep(step=1, status=TaskStatus.RUNNING)
        event = StreamEvent(event_type="react_step", data=step)
        d = event.to_dict()
        # Enum values should be serialized as strings
        assert d["data"]["status"] == "running"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
