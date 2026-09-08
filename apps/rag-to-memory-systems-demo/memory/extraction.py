"""Extract MemoryCandidates from user messages.

Two implementations behind one interface:
  - RuleBasedExtractor: regex patterns. No API key required.
  - LLMExtractor: OpenAI with structured output. Used if OPENAI_API_KEY set.

Both produce a list of MemoryCandidate that the promotion gate consumes.

The LLMExtractor accepts the same assembled prompt the main model call saw
(via the assembled_prompt kwarg). Sending it as the system message lets
OpenAI's automatic prompt caching reuse the prefix that the main turn's
call just warmed; the extractor only pays for the appended extraction
brief and the latest dialogue.
"""
from __future__ import annotations
import os
import re
import json
from memory.records import MemoryCandidate


_EXTRACTION_BRIEF = """\
You are the memory-extraction subsystem for an AI agent. The system message
above is the agent's current assembled context: active policies, the user's
stored preferences, facts retrieved for this turn, episodic memory hits, and
the most recent trace events. Use that context — do not extract in a vacuum.

Your job: from the latest USER message, propose only memories that would
still be useful in a future, unrelated session. Be discerning. Most turns
produce zero candidates, and that is the correct answer.

== SOURCE OF TRUTH ==

The USER MESSAGE in "=== Latest turn ===" is the only source of new memory.

The <recent> section in the system message contains BOTH user_msg events
(things the user said) AND model_msg events / turn_envelope events (things
the agent produced). ONLY user_msg events are valid sources. The agent's
prior replies are NEVER sources — they may contain stale data,
hallucinations, or restatements of facts the user has already contradicted.
Treat agent text as informational context for understanding the
conversation, not as ground truth.

If a value appears ONLY in a model_msg / turn_envelope / agent reply and
NOT in any user statement, do NOT propose it. Wait for the user to
state it themselves.

== RULES ==

1. DEDUPLICATE against the assembled context. If a fact's content matches
   a fact already in <facts>, or a preference key is already in
   <preferences> with the same value, do not propose it.

2. DETECT CONTRADICTIONS PROPERLY. When the user states something that
   contradicts a fact in <facts>:
     a. Use the EXACT same subject AND predicate as the existing fact.
        Each fact line renders as:
          [<tier>] subject=<value> predicate=<value> :: <content>
        Copy the subject and predicate fields VERBATIM from that line.
        Do NOT use the placeholder strings from this brief's worked
        example below — those are illustrative; the real subject and
        predicate come from <facts>.
        Do NOT invent a new predicate like "stripe_webhook_url" when
        the existing fact uses "infrastructure".
     b. The content should reflect the NEW value the user gave.
     c. The promotion gate routes matching (subject, predicate) with
        different content through the supersession path. Wrong subject
        or wrong predicate = wrong path = duplicate active facts in
        memory.
     d. HEDGING REJECTS CONTRADICTION. If the user's contradicting
        statement is hedged with uncertainty ("I think X", "I thought
        X", "I believe X", "I recall X", "I remember X", "maybe X",
        "perhaps X", "I'm not sure but X", "I heard X", "it might be
        X", "could be X", "isn't it X?"), DO NOT propose a superseding
        fact. The
        user has not confirmed the new value — the main agent will ask
        them to confirm. Wait for the next turn. If they then re-assert
        with certainty ("yes, it's X", "I just checked, X is right"),
        the extractor on THAT turn proposes the supersession.

        Implicit preferences (rule 4) survive hedging at lower
        confidence — but facts do not, because the supersession path
        revokes the prior active fact and a hedged contradiction would
        silently retire valid memory.

     e. CONFIRMATION OF A PRIOR HEDGE. When the latest user message is
        a bare confirmation ("yes", "yep", "yeah", "correct", "right",
        "that's right", "ok"), look at the most recent user_msg event
        in <recent>. If that prior user_msg HEDGED a value that
        contradicts a fact in <facts>, the current confirmation
        AUTHORIZES extraction of that previously-hedged value. The
        source of the new content is the prior user_msg (a valid
        source per the "SOURCE OF TRUTH" rules), and the latest bare
        confirmation is what licenses extracting it now.

        EVEN A SINGLE-WORD confirmation triggers this rule when the
        prior user_msg was a clear hedged contradiction. "yes", "yep",
        "yeah", "correct", "right", and "ok" alone are sufficient
        signals when the immediately preceding user_msg in <recent>
        contained a value that contradicts an existing fact.

        Example 1 — bare confirmation:
          <recent> turn 0 user_msg: "I think the URL is /v3/stripe"
          <recent> turn 0 model_msg: "According to my records, /v1…"
          Latest turn user_msg: "yep"

          The bare "yep" by itself is not a source, but combined with
          the prior turn 0 user_msg ("I think the URL is /v3/stripe"),
          it confirms the previously-hedged /v3/stripe value. Propose
          ONE superseding fact candidate:
            subject = customer:jane_doe@example.com
            predicate = infrastructure
            content = "Stripe webhook URL is https://api.acme.com/v3/stripe"
            confidence = 0.85

        Example 2 — single word "correct":
          <recent> turn 0 user_msg: "I think we moved to us-west-2"
          Latest turn user_msg: "correct"

          Propose: deployment fact with content "Runs in us-west-2",
          confidence 0.85.

        Confidence is 0.85 — one rung below an explicit single-turn
        confirmation (which is 0.9-0.95) because the value's first
        mention was hedged, but well above the 0.7 gate threshold.

        If the latest user message is a re-assertion that itself
        contains the value ("yes, /v3/stripe is correct"), prefer
        that turn's value over reaching into <recent> — the user
        re-stated for a reason.

3. REJECT non-durable signals:
   - Greetings, acknowledgments, conversational filler
   - Pure one-off help requests where no stack / language / region /
     tooling choice is revealed ("explain quantum tunneling",
     "help me debug this null pointer")
   - Hypotheticals and speculation ("I might switch to X", "what if I…")
   - Hedged claims about FACTS ("I think X", "I thought X",
     "I believe X", "I recall X", "I remember X", "maybe X", "perhaps X",
     "I'm not sure but X", "I heard X", "it might be X", "could be X",
     "isn't it X?") — these need the user's next-turn confirmation
     before extraction; see rule 2d
   - Transient state or questions ("is the API up?")
   - Anything phrased as a test, debug query, or "just checking"

   IMPORTANT: a one-off request that INCIDENTALLY reveals a stable
   choice still warrants an implicit-preference candidate (see rule 4).
   "Show me an example in JavaScript" is a one-off ask AND a signal
   that the user works in JavaScript — propose the preference even
   though the underlying request is transient.

4. ACCEPT durable assertions AND implicit-but-likely-durable signals.
   Facts must be explicitly stated; preferences may be inferred from
   contextual hints because preference writes are PK-upserts (a wrong
   guess gets cleanly overwritten when the user states the real value).

   EXPLICIT preferences — propose at 0.85-0.95 confidence:
     "I prefer terse answers"        → verbosity=terse           (0.95)
     "Show responses in JSON"        → response_format=json      (0.95)
     "Respond in French"             → language=fr               (0.95)
     "I prefer JavaScript"           → code_language=javascript  (0.95)

   IMPLICIT preferences — propose at 0.7-0.8 confidence when the user's
   message reveals a stable choice indirectly through what language
   they use, what tools they reference, what region they work in:
     "show me an example in JavaScript" → code_language=javascript  (0.7)
     "fix this Python snippet"          → code_language=python      (0.7)
     "We use BigQuery for analytics"    → tooling=bigquery          (0.8)
     "We're in eu-west-2"               → region=eu-west-2          (0.85)

   Use this small, stable vocabulary of pref_keys — do NOT invent
   variants:
     response_format   json | markdown | plain | html
     verbosity         terse | brief | normal | verbose
     code_language     javascript | typescript | python | go | rust | …
     language          en | es | fr | de | …  (natural language)
     date_format       ISO | DD/MM/YYYY | …
     timezone          UTC | America/New_York | …
     locale            en-US | en-GB | …
     tooling           any stack name the user references in passing

   FACTS — explicit only (the gate writes facts as provisional unless
   contradicting an existing fact, so silent false positives cost
   real retrieval noise). Accept:
     - Identifiers, URLs, regions, account/customer IDs, named entities
     - Fixed configuration choices the user states as durable
     - Long-lived business attributes: fiscal year, currency, default
       payment method, primary contact

5. CALIBRATE confidence. The promotion gate rejects facts with
   confidence < 0.7. Use confidence to reflect how durable AND
   unambiguous the user's assertion is:
     0.95 — user stated it explicitly and clearly
     0.80 — user stated it; durability or scope inferred
     0.70 — minimum for promotion; some inference required
     < 0.70 — skip; do not include in output

6. PRESERVE PROVENANCE. The subject should be stable
   ("customer:<user_id>" for personal facts, an org name for tenant
   facts). REUSE EXISTING PREDICATES from <facts> verbatim when the new
   candidate is about the same kind of attribute. Predicate vocabulary
   should stay small and stable: "infrastructure", "deployment",
   "billing", "tooling", "ownership", "configuration".

== WORKED EXAMPLE ==

Latest turn user message:
  "I just checked, it's actually /v3/stripe."

<facts> in context shows (this is the rendered shape — copy values verbatim):
  [standard] subject=customer:jane@acme.com predicate=infrastructure :: Stripe webhook URL is https://api.acme.com/v1/stripe

Agent's prior reply (visible in <recent> as a model_msg):
  "Your Stripe webhook URL is set to https://api.acme.com/v1/stripe…"

CORRECT extraction — one candidate:
{
  "facts": [
    {"subject": "customer:jane@acme.com",
     "predicate": "infrastructure",
     "content": "Stripe webhook URL is https://api.acme.com/v3/stripe",
     "confidence": 0.9}
  ],
  "preferences": []
}

Why this is correct:
- Same subject and predicate as the existing fact, so the gate will
  route through supersession instead of creating a parallel fact.
- Content reflects the user's correction (/v3/stripe), not the agent's
  stale value (/v1/stripe).
- Single candidate; the agent's stale value is NOT also proposed.

INCORRECT extraction — DO NOT DO THIS:
{
  "facts": [
    {"subject": "customer:jane@acme.com",
     "predicate": "stripe_webhook_url",
     "content": "https://api.acme.com/v1/stripe",
     "confidence": 0.95},
    {"subject": "customer:jane@acme.com",
     "predicate": "stripe_webhook_endpoint",
     "content": "/v3/stripe",
     "confidence": 0.8}
  ]
}

Why this is wrong:
- "stripe_webhook_url" / "stripe_webhook_endpoint" are invented predicates;
  the existing fact uses "infrastructure", so these candidates bypass
  supersession and create duplicate active facts.
- The first candidate's content was pulled from the agent's reply, not
  from anything the user said — model_msg events are not sources.

== HEDGED CONTRADICTION — COUNTER-EXAMPLE ==

Latest turn user message:
  "I think our webhook was updated to /v3/stripe"

<facts> in context shows:
  [standard] subject=customer:jane@acme.com predicate=infrastructure :: Stripe webhook URL is https://api.acme.com/v1/stripe

CORRECT extraction — empty:
{"facts": [], "preferences": []}

Why empty:
- "I think" is a hedge. The user has not confirmed the new value.
- The main agent will surface the discrepancy and ask the user to
  confirm (Stage 1 of contradiction handling in the system prompt).
- If the user re-asserts with certainty on the NEXT turn ("yes, it
  was updated to /v3", "I just checked, /v3 is right"), the extractor
  proposes the supersession candidate THEN — not now.
- Extracting the supersession on the hedged message would revoke the
  active v1 fact based on something the user is unsure about,
  contradicting the very confirmation flow the main agent just asked
  for. Wait one turn.

INCORRECT — DO NOT DO THIS on a hedged statement:
{
  "facts": [
    {"subject": "customer:jane@acme.com", "predicate": "infrastructure",
     "content": "Stripe webhook URL is https://api.acme.com/v3/stripe",
     "confidence": 0.9}
  ]
}

== OUTPUT FORMAT ==

Return JSON only, matching this schema exactly:
{
  "facts": [
    {"subject": "...", "predicate": "...", "content": "...",
     "confidence": 0.7-1.0}
  ],
  "preferences": [
    {"pref_key": "...", "pref_value": <any>, "confidence": 0.7-1.0}
  ]
}

If nothing durable was stated by the user, return:
{"facts": [], "preferences": []}
"""


_PREF_PATTERN = re.compile(
    r"\bi\s+(?:prefer|like|want|need|use)\s+(?P<value>\w+)\s*(?:answers?|responses?|format)?",
    re.IGNORECASE,
)
_VERBOSITY_VALUES = {"terse", "brief", "verbose", "long", "short"}
_FORMAT_VALUES = {"json", "markdown", "plain", "text"}

_INFRA_URL_PATTERN = re.compile(
    r"(?P<role>(?:production|staging|webhook|api|url))[^a-z0-9]*"
    r"(?P<verb>is\s+now|changed\s+to|set\s+to|is|=|:)\s+"
    r"(?P<value>https?://\S+)",
    re.IGNORECASE,
)

_INFRA_REGION_PATTERN = re.compile(
    r"(?:we|our|production)[^.]*?(?:run|host|deploy|are)[^.]*?\b(us-east-\d|us-west-\d|eu-west-\d|on-prem)\b",
    re.IGNORECASE,
)


class RuleBasedExtractor:
    """Pattern-match preferences and facts. Crude on purpose.

    Accepts the same kwargs as LLMExtractor for interface parity, but
    ignores assembled_prompt and model_response — regexes don't read context.
    """

    def extract(
        self,
        user_message: str,
        tenant_id: str,
        user_id: str,
        agent_id: str,
        run_id: str,
        turn_id: str | None = None,
        assembled_prompt: str | None = None,
        model_response: str | None = None,
    ) -> list[MemoryCandidate]:
        out: list[MemoryCandidate] = []

        # Preferences.
        for m in _PREF_PATTERN.finditer(user_message):
            value = m.group("value").lower()
            if value in _VERBOSITY_VALUES:
                pref_value = "terse" if value in {"terse", "brief", "short"} else "verbose"
                out.append(MemoryCandidate(
                    memory_type="preference", tenant_id=tenant_id, user_id=user_id,
                    content=user_message, confidence=1.0,
                    source_run_id=run_id, source_turn_id=turn_id,
                    pref_key="verbosity", pref_value=pref_value, source="user_stated",
                ))
            elif value in _FORMAT_VALUES:
                out.append(MemoryCandidate(
                    memory_type="preference", tenant_id=tenant_id, user_id=user_id,
                    content=user_message, confidence=1.0,
                    source_run_id=run_id, source_turn_id=turn_id,
                    pref_key="response_format", pref_value=value, source="user_stated",
                ))

        # Facts: URLs.
        for m in _INFRA_URL_PATTERN.finditer(user_message):
            role = m.group("role").lower()
            # Avoid "URL URL is ..." when the captured role word is already "url".
            role_label = "Stripe webhook" if role in {"webhook", "url"} else role.capitalize()
            content = f"{role_label} URL is {m.group('value')}"
            out.append(MemoryCandidate(
                memory_type="fact", tenant_id=tenant_id, user_id=user_id,
                content=content, confidence=0.95,
                source_run_id=run_id, source_turn_id=turn_id,
                subject=f"customer:{user_id}", predicate="infrastructure",
            ))

        # Facts: deployment region.
        for m in _INFRA_REGION_PATTERN.finditer(user_message):
            region = m.group(1).lower()
            content = f"Runs in {region}"
            out.append(MemoryCandidate(
                memory_type="fact", tenant_id=tenant_id, user_id=user_id,
                content=content, confidence=0.85,
                source_run_id=run_id, source_turn_id=turn_id,
                subject=f"customer:{user_id}", predicate="deployment",
            ))

        return out


class LLMExtractor:
    """Send the turn to OpenAI with the assembled context, request structured
    candidates. Designed so the system message is identical to the main model
    call's system message — OpenAI's automatic prompt caching then reuses the
    warmed prefix and the extractor pays only for the appended brief and
    the latest dialogue."""

    def __init__(self, model: str = "gpt-4.1-mini"):
        from openai import AsyncOpenAI
        self.client = AsyncOpenAI()
        self.model = model

    async def extract(
        self,
        user_message: str,
        tenant_id: str,
        user_id: str,
        agent_id: str,
        run_id: str,
        turn_id: str | None = None,
        assembled_prompt: str | None = None,
        model_response: str | None = None,
    ) -> list[MemoryCandidate]:
        # The system message is the SAME string the main model call sent on
        # this turn. OpenAI's auto-caching keys on identical prefixes, so the
        # extractor's call benefits from the cache the main call just warmed.
        system_content = assembled_prompt or "<no assembled context>"

        # The user-side payload is the volatile, turn-specific tail:
        # extraction brief plus the latest user message ONLY. The agent's
        # reply is excluded by design — agent text is not a valid source
        # for new memory (see SOURCE OF TRUTH in the brief). model_response
        # is accepted on the signature for callers that pass it but is not
        # forwarded to the model.
        _ = model_response  # intentionally unused
        dialogue = f"=== Latest turn ===\nUser: {user_message}"
        user_content = f"{_EXTRACTION_BRIEF}\n\n{dialogue}\n\nReturn JSON now."

        resp = await self.client.chat.completions.create(
            model=self.model,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_content},
                {"role": "user", "content": user_content},
            ],
        )
        try:
            data = json.loads(resp.choices[0].message.content or "{}")
        except json.JSONDecodeError:
            data = {}
        return parse_candidates_dict(
            data,
            tenant_id=tenant_id, user_id=user_id, run_id=run_id,
            source_turn_id=turn_id, user_message=user_message,
        )


def parse_candidates_dict(
    data: dict,
    *,
    tenant_id: str,
    user_id: str,
    run_id: str,
    source_turn_id: str | None,
    user_message: str,
) -> list[MemoryCandidate]:
    """Convert structured-output JSON ({"facts": [...], "preferences": [...]})
    into MemoryCandidate objects, skipping malformed entries.

    Shared between LLMExtractor (two-call path) and OpenAIModel's combined
    call. Lives in extraction.py because the JSON shape is part of the
    extraction contract — model.py imports this helper rather than the
    other way around to keep the import direction one-way.
    """
    out: list[MemoryCandidate] = []
    for f in data.get("facts", []) or []:
        try:
            out.append(MemoryCandidate(
                memory_type="fact", tenant_id=tenant_id, user_id=user_id,
                content=f["content"], confidence=float(f["confidence"]),
                source_run_id=run_id, source_turn_id=source_turn_id,
                subject=f.get("subject", ""), predicate=f.get("predicate", ""),
            ))
        except (KeyError, TypeError, ValueError):
            continue
    for p in data.get("preferences", []) or []:
        try:
            out.append(MemoryCandidate(
                memory_type="preference", tenant_id=tenant_id, user_id=user_id,
                content=user_message, confidence=float(p.get("confidence", 1.0)),
                source_run_id=run_id, source_turn_id=source_turn_id,
                pref_key=p["pref_key"], pref_value=p["pref_value"],
                source="inferred",
            ))
        except (KeyError, TypeError, ValueError):
            continue
    return out


def extractor_from_env() -> RuleBasedExtractor | LLMExtractor:
    if os.getenv("FORCE_SIMULATED"):
        return RuleBasedExtractor()
    if os.getenv("OPENAI_API_KEY"):
        return LLMExtractor(model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"))
    return RuleBasedExtractor()
