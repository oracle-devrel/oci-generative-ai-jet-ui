import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
import pytest

from memory.extraction import LLMExtractor, RuleBasedExtractor, extractor_from_env
from memory.model import OpenAIModel, SimulatedModel, model_from_env


@pytest.mark.asyncio
async def test_simulated_model_responds_with_user_message():
    m = SimulatedModel()
    resp = await m.complete("system context here", "hello there")
    assert "hello there" in resp.text


@pytest.mark.asyncio
async def test_simulated_model_shortens_when_terse_in_context():
    m = SimulatedModel()
    resp = await m.complete("verbosity:terse, be brief", "user message")
    assert resp.text.startswith("Acknowledged")


@pytest.mark.asyncio
async def test_simulated_model_accepts_combined_call_kwargs():
    """Interface parity with OpenAIModel: SimulatedModel takes the identity
    kwargs and returns candidates=None (signalling 'no inline extraction —
    run the configured extractor separately')."""
    m = SimulatedModel()
    resp = await m.complete(
        "system", "user msg",
        tenant_id="t", user_id="u", run_id="r", source_turn_id="0",
    )
    assert resp.candidates is None
    assert "user msg" in resp.text


def test_model_from_env_picks_simulated_without_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("FORCE_SIMULATED", raising=False)
    assert isinstance(model_from_env(), SimulatedModel)


def test_force_simulated_overrides_openai_key(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("FORCE_SIMULATED", "1")
    assert isinstance(model_from_env(), SimulatedModel)
    assert isinstance(extractor_from_env(), RuleBasedExtractor)


# --- OpenAIModel combined-call tests (mocked OpenAI client) -----------------


def _mock_openai_response(reply: str, facts=None, preferences=None):
    """Build a SimpleNamespace shaped like an OpenAI chat completion."""
    body = json.dumps({
        "reply": reply,
        "facts": facts or [],
        "preferences": preferences or [],
    })
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=body))],
        usage=SimpleNamespace(prompt_tokens=100, completion_tokens=20),
    )


def _make_mocked_openai_model(mock_response):
    m = OpenAIModel.__new__(OpenAIModel)
    m.model = "gpt-4.1-mini"
    m.client = MagicMock()
    m.client.chat = MagicMock()
    m.client.chat.completions = MagicMock()
    m.client.chat.completions.create = AsyncMock(return_value=mock_response)
    return m


@pytest.mark.asyncio
async def test_openai_combined_call_returns_reply_and_candidates():
    """With all identity kwargs provided, OpenAIModel does ONE structured-
    output API call and the response carries both the reply text AND
    pre-parsed MemoryCandidate objects. The manager then bypasses the
    separate extractor invocation."""
    m = _make_mocked_openai_model(_mock_openai_response(
        reply="Got it — terse mode noted.",
        preferences=[{"pref_key": "verbosity", "pref_value": "terse", "confidence": 0.95}],
    ))
    resp = await m.complete(
        "<system context>", "I prefer terse answers",
        tenant_id="acme", user_id="u1", run_id="run_1", source_turn_id="0",
    )
    assert resp.text == "Got it — terse mode noted."
    assert resp.candidates is not None and len(resp.candidates) == 1
    cand = resp.candidates[0]
    assert cand.memory_type == "preference"
    assert cand.pref_key == "verbosity"
    assert cand.pref_value == "terse"
    # The OpenAI client was called exactly once (combined path = 1 call).
    assert m.client.chat.completions.create.call_count == 1


@pytest.mark.asyncio
async def test_openai_combined_call_handles_empty_candidates():
    """The common case — most turns produce no extraction candidates.
    candidates must still be a (possibly-empty) LIST, not None, so the
    manager treats it as 'combined call completed' and skips the
    extractor."""
    m = _make_mocked_openai_model(_mock_openai_response(reply="Hello there!"))
    resp = await m.complete(
        "<system>", "hi",
        tenant_id="t", user_id="u", run_id="r", source_turn_id="0",
    )
    assert resp.candidates == []
    assert resp.text == "Hello there!"


@pytest.mark.asyncio
async def test_openai_falls_back_to_reply_only_without_identity_kwargs():
    """If any identity kwarg is missing, OpenAIModel runs the reply-only
    path (no extraction brief, candidates=None). This keeps the model
    safely usable from callers that don't pass session identity."""
    plain_response = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="just a reply"))],
        usage=SimpleNamespace(prompt_tokens=50, completion_tokens=5),
    )
    m = _make_mocked_openai_model(plain_response)
    resp = await m.complete("<system>", "hi")  # no identity kwargs
    assert resp.text == "just a reply"
    assert resp.candidates is None


@pytest.mark.asyncio
async def test_openai_combined_call_survives_malformed_json():
    """If the structured-output JSON is malformed, the model returns an
    empty reply with an empty candidates list rather than crashing."""
    malformed = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="not json"))],
        usage=SimpleNamespace(prompt_tokens=50, completion_tokens=5),
    )
    m = _make_mocked_openai_model(malformed)
    resp = await m.complete(
        "<system>", "hi",
        tenant_id="t", user_id="u", run_id="r", source_turn_id="0",
    )
    assert resp.text == ""
    assert resp.candidates == []
