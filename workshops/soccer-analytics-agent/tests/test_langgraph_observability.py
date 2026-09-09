import uuid
from unittest.mock import patch

import pytest

from soccer_agent.agent.grok_client import GrokReply
from soccer_agent.agent.loop import run_turn
from soccer_agent.observability.langgraph_steps import list_steps


@pytest.mark.integration
def test_run_turn_persists_langgraph_oracledb_steps(
    predictions_loaded,
    memory_schema_ready,
    onnx_model_loaded,
):
    sid = f"obs-{uuid.uuid4()}"
    seq = [
        GrokReply(
            text="",
            tool_calls=[
                {
                    "name": "lookup_prediction",
                    "arguments": '{"home_team":"Spain","away_team":"Brazil"}',
                    "id": "c1",
                }
            ],
            raw=None,
        ),
        GrokReply(text="Spain has the edge.", tool_calls=[], raw=None),
    ]

    with patch("soccer_agent.agent.loop.grok_chat", side_effect=seq):
        reply = run_turn(sid, "Spain vs Brazil?")

    assert "Spain" in reply.text
    steps = list_steps(sid, limit=50)
    event_types = [step.value["event_type"] for step in steps]
    assert event_types == [
        "turn_start",
        "grounding_retrieved",
        "model_response",
        "tool_call",
        "tool_result",
        "model_response",
        "final_response",
    ]
    tool_steps = [step for step in steps if step.value.get("tool_name") == "lookup_prediction"]
    assert [step.value["event_type"] for step in tool_steps] == ["tool_call", "tool_result"]
    assert all(
        step.value["observability_backend"] == "langgraph-oracledb.OracleStore"
        for step in steps
    )
