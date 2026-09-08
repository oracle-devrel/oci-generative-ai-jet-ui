import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
import pytest

from memory.extraction import LLMExtractor, RuleBasedExtractor, _EXTRACTION_BRIEF


def test_extracts_terse_preference():
    e = RuleBasedExtractor()
    cands = e.extract(
        "I prefer terse answers", "acme", "u1", "a1", "run_1",
    )
    pref = next(c for c in cands if c.memory_type == "preference")
    assert pref.pref_key == "verbosity"
    assert pref.pref_value == "terse"


def test_extracts_webhook_url_as_fact():
    e = RuleBasedExtractor()
    cands = e.extract(
        "Our webhook URL is https://api.acme.com/v2/stripe",
        "acme", "customer:jane", "a1", "run_1",
    )
    fact = next(c for c in cands if c.memory_type == "fact")
    assert "v2/stripe" in fact.content
    assert fact.predicate == "infrastructure"


def test_extracts_region_as_fact():
    e = RuleBasedExtractor()
    cands = e.extract(
        "We run our production in us-east-1.", "acme", "customer:jane", "a1", "run_1",
    )
    fact = next((c for c in cands if c.memory_type == "fact" and c.predicate == "deployment"), None)
    assert fact is not None
    assert "us-east-1" in fact.content


def test_no_extraction_when_message_has_nothing_extractable():
    e = RuleBasedExtractor()
    cands = e.extract("Hello!", "acme", "u1", "a1", "run_1")
    assert cands == []


def test_rule_based_extractor_accepts_new_kwargs_without_breaking():
    """assembled_prompt and model_response are accepted but ignored."""
    e = RuleBasedExtractor()
    cands = e.extract(
        "I prefer terse answers", "acme", "u1", "a1", "run_1",
        assembled_prompt="<irrelevant context>",
        model_response="any reply",
    )
    assert any(c.memory_type == "preference" for c in cands)


@pytest.mark.asyncio
async def test_llm_extractor_sends_assembled_prompt_as_system_message():
    """The system message must equal assembled_prompt verbatim so OpenAI's
    automatic prompt caching reuses the warmed prefix from the main model
    call. The extraction brief plus dialogue lives in the user message."""
    e = LLMExtractor.__new__(LLMExtractor)
    e.model = "gpt-4o-mini"

    mock_completion = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(
            content=json.dumps({"facts": [], "preferences": []})
        ))]
    )
    e.client = MagicMock()
    e.client.chat = MagicMock()
    e.client.chat.completions = MagicMock()
    e.client.chat.completions.create = AsyncMock(return_value=mock_completion)

    assembled = "<context>\n  <policies>refund_threshold=...</policies>\n</context>"
    await e.extract(
        user_message="hi",
        tenant_id="acme", user_id="u1", agent_id="a1", run_id="run_1",
        assembled_prompt=assembled,
        model_response="hello back",
    )

    call_kwargs = e.client.chat.completions.create.call_args.kwargs
    messages = call_kwargs["messages"]
    assert messages[0]["role"] == "system"
    assert messages[0]["content"] == assembled  # exact match for cache reuse
    assert messages[1]["role"] == "user"
    assert _EXTRACTION_BRIEF in messages[1]["content"]
    assert "User: hi" in messages[1]["content"]


@pytest.mark.asyncio
async def test_llm_extractor_excludes_agent_reply_from_dialogue():
    """The agent's reply must NOT appear in the dialogue payload; the brief
    forbids using model output as a fact source, and removing it from the
    prompt closes the loophole structurally too."""
    e = LLMExtractor.__new__(LLMExtractor)
    e.model = "gpt-4o-mini"
    mock_completion = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(
            content=json.dumps({"facts": [], "preferences": []})
        ))]
    )
    e.client = MagicMock()
    e.client.chat = MagicMock()
    e.client.chat.completions = MagicMock()
    e.client.chat.completions.create = AsyncMock(return_value=mock_completion)

    sensitive_reply = "Your Stripe webhook URL is https://api.acme.com/v1/stripe"
    await e.extract(
        user_message="I just checked it is actually /v3/stripe",
        tenant_id="acme", user_id="u1", agent_id="a1", run_id="run_1",
        assembled_prompt="<context>...</context>",
        model_response=sensitive_reply,
    )

    user_content = e.client.chat.completions.create.call_args.kwargs["messages"][1]["content"]
    assert "Agent:" not in user_content
    assert sensitive_reply not in user_content
    assert "User: I just checked it is actually /v3/stripe" in user_content


@pytest.mark.asyncio
async def test_llm_extractor_handles_malformed_json_per_candidate():
    """Missing fields on a single candidate should skip that candidate, not
    crash the whole extraction."""
    e = LLMExtractor.__new__(LLMExtractor)
    e.model = "gpt-4o-mini"
    mock_completion = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(
            content=json.dumps({
                "facts": [
                    {"subject": "customer:u1", "predicate": "deployment",
                     "content": "us-east-1", "confidence": 0.9},
                    {"content": "missing subject and confidence"},  # malformed
                ],
                "preferences": [{"pref_key": "verbosity",
                                 "pref_value": "terse", "confidence": 1.0}],
            })
        ))]
    )
    e.client = MagicMock()
    e.client.chat = MagicMock()
    e.client.chat.completions = MagicMock()
    e.client.chat.completions.create = AsyncMock(return_value=mock_completion)

    cands = await e.extract(
        user_message="we run in us-east-1; I prefer terse",
        tenant_id="acme", user_id="u1", agent_id="a1", run_id="run_1",
        assembled_prompt="ctx", model_response=None,
    )
    # 1 good fact + 1 good preference; the malformed fact is dropped silently.
    assert len([c for c in cands if c.memory_type == "fact"]) == 1
    assert len([c for c in cands if c.memory_type == "preference"]) == 1
