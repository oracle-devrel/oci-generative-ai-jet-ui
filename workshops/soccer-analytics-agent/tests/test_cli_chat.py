from unittest.mock import patch

import pytest
from soccer_agent.agent.grok_client import GrokReply


@pytest.mark.integration
def test_cli_one_round(memory_schema_ready, onnx_model_loaded, monkeypatch, capsys):
    inputs = iter(["hi", "exit"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))
    with patch("soccer_agent.agent.loop.grok_chat") as mock:
        mock.return_value = GrokReply(text="hello!", tool_calls=[], raw=None)
        from soccer_agent.cli import chat as cli
        rc = cli.main()
    assert rc == 0
    out = capsys.readouterr().out
    assert "hello!" in out
