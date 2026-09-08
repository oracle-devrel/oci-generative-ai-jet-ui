from unittest.mock import MagicMock, patch


def test_meta_classifies_and_routes():
    with patch("agent_reasoning.agents.meta.BaseAgent.__init__", return_value=None):
        from agent_reasoning.agents.meta import MetaReasoningAgent

        agent = MetaReasoningAgent.__new__(MetaReasoningAgent)
        agent.name = "MetaReasoningAgent"
        agent.color = "white"
        agent.client = MagicMock()
        agent.client.model = "gemma3:270m"
        agent.client.generate = MagicMock(
            return_value=iter(["CATEGORY: math\nCONFIDENCE: 0.9\nREASON: arithmetic"])
        )

        classification = agent._classify_query("What is 2+2?")
        assert classification["query_type"] == "math"
        assert classification["confidence"] == 0.9


def test_meta_routing_table_completeness():
    from agent_reasoning.agents.meta import MetaReasoningAgent

    assert "math" in MetaReasoningAgent.ROUTING_TABLE
    assert "creative" in MetaReasoningAgent.ROUTING_TABLE
    assert "debate_worthy" in MetaReasoningAgent.ROUTING_TABLE
    assert "general" in MetaReasoningAgent.ROUTING_TABLE


def test_meta_unknown_category_defaults_to_general():
    with patch("agent_reasoning.agents.meta.BaseAgent.__init__", return_value=None):
        from agent_reasoning.agents.meta import MetaReasoningAgent

        agent = MetaReasoningAgent.__new__(MetaReasoningAgent)
        agent.name = "MetaReasoningAgent"
        agent.color = "white"
        agent.client = MagicMock()
        agent.client.generate = MagicMock(return_value=iter(["CATEGORY: banana\nCONFIDENCE: 0.3"]))
        classification = agent._classify_query("test")
        assert classification["query_type"] == "general"


def test_meta_emits_classification_event():
    with patch("agent_reasoning.agents.meta.BaseAgent.__init__", return_value=None):
        from agent_reasoning.agents.meta import MetaReasoningAgent

        agent = MetaReasoningAgent.__new__(MetaReasoningAgent)
        agent.name = "MetaReasoningAgent"
        agent.color = "white"
        agent.client = MagicMock()
        agent.client.model = "gemma3:270m"
        agent.client.generate = MagicMock(
            return_value=iter(["CATEGORY: math\nCONFIDENCE: 0.9\nREASON: arithmetic"])
        )

        # We need to mock the AGENT_MAP import inside stream_structured
        # Just test _classify_query works correctly
        events = []
        try:
            for event in agent.stream_structured("What is 2+2?"):
                events.append(event)
                if event.event_type == "meta_classification":
                    break
        except Exception:
            pass  # May fail when trying to instantiate delegated agent

        meta_events = [e for e in events if e.event_type == "meta_classification"]
        assert len(meta_events) >= 1
        assert meta_events[0].data.query_type == "math"
