import os
import pytest
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

pytestmark = pytest.mark.skipif(
    not os.getenv("OCI_GENAI_API_KEY") or "REPLACE_ME" in os.getenv("OCI_GENAI_API_KEY", ""),
    reason="OCI bearer key not configured",
)


def test_grok_says_paris():
    from soccer_agent.agent.grok_client import chat
    r = chat([
        {"role": "system", "content": "Reply with exactly one word."},
        {"role": "user", "content": "Capital of France?"},
    ])
    assert "paris" in r.text.lower()
