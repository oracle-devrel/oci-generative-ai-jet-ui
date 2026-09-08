"""Unit tests for the behavioral preamble prepended to every assembled prompt.

The preamble teaches the model how to handle contradictions with stored
facts and how to refuse policy-violating requests. It lives at the top of
the prompt so it joins the cached prefix on the OpenAI side.
"""
from memory.manager import PromptContext, _PROMPT_PREAMBLE


def test_preamble_contains_contradiction_phrasing():
    """The exact phrasing the user asked for must be in the preamble — the
    model copies this verbatim, so the wording matters. Whitespace-normalize
    so a line wrap doesn't cause a false negative."""
    flat = " ".join(_PROMPT_PREAMBLE.split())
    assert "According to my records" in flat
    assert "If you know this to be incorrect" in flat


def test_preamble_contains_policy_refusal_rules():
    """Policy violations must result in REFUSAL, not soft-comply or work-around."""
    assert "REFUSE" in _PROMPT_PREAMBLE or "refuse" in _PROMPT_PREAMBLE.lower()
    assert "violates a policy" in _PROMPT_PREAMBLE.lower() or "violate" in _PROMPT_PREAMBLE.lower()


def test_preamble_is_prepended_to_prompt_text():
    """to_prompt_text() must start with the preamble, then the <context> block."""
    ctx = PromptContext(
        policies=[{"policy_key": "p", "policy_value": {"v": 1}}],
        facts=[{"predicate": "x", "content": "y", "relevance": "high"}],
    )
    text = ctx.to_prompt_text()
    assert text.startswith(_PROMPT_PREAMBLE)
    assert "<context>" in text
    # Preamble comes before <context>.
    assert text.index(_PROMPT_PREAMBLE) < text.index("<context>")


def test_preamble_uses_response_format_not_terse_for_example():
    """The preamble must not contain the word 'terse' anywhere; SimulatedModel
    triggers terse-mode on substring match, so an example using 'terse' would
    break every non-terse turn in tests and demos."""
    assert "terse" not in _PROMPT_PREAMBLE.lower()


def test_preamble_warns_against_doubling_down_on_prior_replies():
    """The model should not treat its own prior replies as ground truth."""
    text = _PROMPT_PREAMBLE.lower()
    assert "prior replies" in text or "prior reply" in text


def test_preamble_has_topic_switch_rule():
    """When the user pivots to a new topic, the model must answer fresh
    instead of reproducing the most recent reply from <recent>. Without
    this rule, gpt-4.1-mini will parrot its prior model_msg verbatim on
    short follow-ups that change subject."""
    flat = " ".join(_PROMPT_PREAMBLE.split())
    # An explicit topic-switch / different-topic clause.
    assert "different topic" in flat.lower() or "topic switch" in flat.lower()
    # And the prohibition on reusing the prior reply.
    assert "do not reuse" in flat.lower() or "do not reuse, paraphrase" in flat.lower()


def test_hedge_markers_are_synchronized_across_preamble_and_regex():
    """The preamble's hedge enumeration, the _HEDGE_RE regex, and the
    extractor brief MUST agree on which phrases count as hedges.

    If they disagree, the model and the extractor disagree about which
    stage they're in — producing the failure mode where the agent says
    'Got it, I'll update that' while no supersession actually fires
    (because the extractor's hedge rule still drops the candidate, or
    the regex doesn't fire so the bare-confirmation synthesizer never
    rewrites the next 'yes' into a fresh statement).

    This test pins the minimum vocabulary that must appear in BOTH the
    preamble text AND the regex. The extractor brief lives in a
    different module; we don't import it here to avoid coupling, but
    the comment block above _HEDGE_RE references it as the third
    location to keep in sync.
    """
    from memory.manager import _HEDGE_RE

    flat = " ".join(_PROMPT_PREAMBLE.split())
    # Phrases that the preamble must call out as hedges.
    for marker in ('"I think X"', '"I thought X"', '"I believe X"', '"maybe X"'):
        assert marker in flat, f"preamble missing hedge marker: {marker}"

    # Phrases the regex must fire on (case-insensitively).
    for utterance in (
        "I think the URL is /v3",
        "I thought we updated that to /v3/stripe",
        "I believe we changed it",
        "maybe it's /v3 now",
    ):
        assert _HEDGE_RE.search(utterance), f"_HEDGE_RE missed: {utterance!r}"

    # Confirmations must NOT match the hedge regex.
    for utterance in ("yes", "I just checked, /v3", "the URL is now /v3/stripe"):
        assert not _HEDGE_RE.search(utterance), (
            f"_HEDGE_RE wrongly matched confirmation: {utterance!r}"
        )


def test_preamble_describes_stage_2_after_confirmation():
    """Once the user confirms, the model must stop reciting 'According to my
    records'. The preamble has to teach this explicitly because gpt-4o-mini
    will otherwise lock onto the template."""
    flat = " ".join(_PROMPT_PREAMBLE.split())
    assert "Stage 2" in flat or "STAGE 2" in flat or "stage 2" in flat
    # Confirmation phrases the user might use.
    for phrase in ("yes", "yep", "I just checked", "please update"):
        assert phrase in flat, f"missing confirmation phrase: {phrase}"
    # Explicit "stop repeating".
    assert "stop" in flat.lower() or "do not" in flat.lower() or "Do NOT" in flat


def test_to_prompt_text_renders_subject_for_facts():
    """The fact line must expose the subject so the LLM extractor can copy it
    verbatim into a contradicting candidate. Without this the gate's
    contradiction check misses and supersession never fires."""
    ctx = PromptContext(
        facts=[{
            "subject": "customer:jane_doe@example.com",
            "predicate": "infrastructure",
            "content": "Stripe webhook URL is https://api.acme.com/v1/stripe",
            "relevance": "high",
        }],
    )
    text = ctx.to_prompt_text()
    assert "subject=customer:jane_doe@example.com" in text
    assert "predicate=infrastructure" in text
    assert "Stripe webhook URL is https://api.acme.com/v1/stripe" in text
