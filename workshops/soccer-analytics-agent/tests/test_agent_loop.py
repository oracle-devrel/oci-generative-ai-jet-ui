import uuid
from unittest.mock import patch

import pytest

from soccer_agent.agent.grok_client import GrokReply
from soccer_agent.agent.loop import AssistantReply, run_turn


@pytest.mark.integration
def test_run_turn_no_tools(memory_schema_ready, onnx_model_loaded):
    with patch("soccer_agent.agent.loop.grok_chat") as mock_chat:
        mock_chat.return_value = GrokReply(text="hello back", tool_calls=[], raw=None)
        reply = run_turn(f"s-{uuid.uuid4()}", "hello")
    assert isinstance(reply, AssistantReply)
    assert reply.text == "hello back"
    assert reply.tool_trace == []


@pytest.mark.integration
def test_run_turn_with_tool_call(predictions_loaded, memory_schema_ready, onnx_model_loaded):
    seq = [
        GrokReply(text="", tool_calls=[
            {"name": "lookup_prediction",
             "arguments": '{"home_team":"Spain","away_team":"Brazil"}',
             "id": "c1"}
        ], raw=None),
        GrokReply(text="Spain win is 45%.", tool_calls=[], raw=None),
    ]
    with patch("soccer_agent.agent.loop.grok_chat", side_effect=seq):
        reply = run_turn(f"s-{uuid.uuid4()}", "Spain vs Brazil?")
    assert "45" in reply.text
    assert len(reply.tool_trace) == 1
    assert reply.tool_trace[0]["name"] == "lookup_prediction"
    assert reply.tool_trace[0]["result"]["prob_home_win"] == pytest.approx(0.45)
