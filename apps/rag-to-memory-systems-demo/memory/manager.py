"""MemoryManager: orchestrator for the turn loop, context assembly,
supersession transactions, and cascade-erase."""
from __future__ import annotations
import asyncio
import inspect
import json
import re
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timezone
import oracledb
from memory.embeddings import vector_embedding_sql
from memory.extraction import RuleBasedExtractor, LLMExtractor
from memory.hashing import content_hash
from memory.agent_session import AgentSession
from memory.model import ModelResponse, SimulatedModel, OpenAIModel
from memory.promotion import PromotionGate
from memory.records import MemoryCandidate, PromotionResult
from memory.retrieval import RetrievalResult, RetrievedRow, assemble, relevance_tier
from memory.stores.fact import FactStore
from memory.stores.preference import PreferenceStore
from memory.stores.episodic import EpisodicStore
from memory.stores.policy import PolicyStore
from memory.stores.trace import TraceStore


_PROMPT_PREAMBLE = """\
You are an AI agent operating with structured memory. The <context> block
below is your current state, assembled fresh on every turn. Treat each
section according to these rules:

<policies>: Binding constraints set by the tenant. If the user requests
something that violates a policy, REFUSE and reference the specific policy
that prevents it. Do not work around it, offer a softer version, or
silently comply. Example:
  Policy: refund_threshold = {"max_auto_approve_usd": 500}
  User: "Please auto-approve a $1500 refund."
  Reply: "I can't auto-approve that — our refund_threshold policy caps
  automatic approvals at $500. I can escalate it for manual review if
  you'd like."

<preferences>: How the current user wants you to behave (format, style,
language). Honor them. Example: pref_value response_format=json means
your reply body should be valid JSON.

<facts>: Your authoritative record about the user and their environment.
Handle contradictions in TWO STAGES:

  Stage 1 — first time the user contradicts a fact, OR contradicts it
  with a HEDGED statement (uncertain recall): surface the discrepancy
  with this phrasing:
    "According to my records, [the existing fact]. If you know this to
    be incorrect, please let me know and I'll update it."
  Hedge markers that REQUIRE Stage 1 (do not jump to Stage 2):
    "I think X", "I thought X", "I believe X", "I recall X",
    "I remember X", "maybe X", "perhaps X", "I'm not sure but X",
    "I heard X", "it might be X", "could be X", "isn't it X?"
  A hedged contradiction is NOT a confirmation. The memory subsystem
  will NOT update on a hedge — so if you reply "Got it, I'll note X"
  to a hedged statement, you are lying to the user. Use Stage 1.

  Stage 2 — user confirms or re-asserts the new value: ACKNOWLEDGE THE
  UPDATE and STOP repeating the "According to my records" template.
  Confirmation includes any of:
    - "yes", "yep", "yeah", "correct", "right"
    - "that's right", "you're right"
    - "I just checked", "I just verified", "I confirmed"
    - "please update it", "please change it", "update your records"
    - The user restating the new value with certainty
      ("it definitely is X", "it was updated to X", "I'm sure it's X")
  Once any of those occurs, reply with an acknowledgement such as:
    "Got it — I'll note that the URL is now /v3/stripe."
  Do NOT recite "According to my records" again for the same fact in
  the same conversation. The memory subsystem updates the durable
  record automatically; you do not need to take separate action.

If the user's first message ALREADY contains both the correction AND a
confirmation signal ("I just checked, it's actually /v3"), treat it as
Stage 2 directly — don't ask them to confirm what they just confirmed.

Look at <recent> to determine which stage you're in. If your prior reply
already used the "According to my records" template for the SAME fact,
you are in Stage 2 now — acknowledge the update instead of repeating
Stage 1.

<episodes>: Summaries of past completed work. Use them to recognize when
"we've seen this before"; they describe what happened, not what is
currently true.

<recent>: The last few trace events. Use for conversational coherence
only. Your own prior replies may have been wrong; do not double down on
them if newer evidence contradicts them.

TOPIC SWITCHES: If the user's current message is on a different topic
than your most recent reply in <recent>, answer the current message
fresh. Do NOT reuse, paraphrase, or extend a prior reply that doesn't
directly address what was just asked. Treat <recent> as historical
context, not as a response template.

"""


@dataclass
class PromptContext:
    """Assembled context returned by assemble_context."""
    policies: list[dict] = field(default_factory=list)
    preferences: list[dict] = field(default_factory=list)
    facts: list[dict] = field(default_factory=list)
    episodes: list[dict] = field(default_factory=list)
    recent: list[dict] = field(default_factory=list)
    retrieval_mode: str = "hybrid"

    def to_prompt_text(self) -> str:
        # The preamble lives at the top of the prompt so it's part of the
        # cached prefix on the OpenAI side. The behavioral rules don't
        # change between turns; only <context> contents do.
        parts = [_PROMPT_PREAMBLE, "<context>"]
        if self.policies:
            parts.append("  <policies>")
            for p in self.policies:
                parts.append(f"    {p['policy_key']}={json.dumps(p['policy_value'])}")
            parts.append("  </policies>")
        if self.preferences:
            parts.append("  <preferences>")
            for p in self.preferences:
                parts.append(f"    {p['pref_key']}={json.dumps(p['pref_value'])}")
            parts.append("  </preferences>")
        if self.facts:
            parts.append("  <facts>")
            for f in self.facts:
                tier = f.get("relevance", "standard")
                # Subject is rendered so the LLM extractor can copy it
                # verbatim when proposing a contradicting (superseding)
                # candidate. Without it, the gate's contradiction check
                # (which keys on tenant + subject + predicate) misses,
                # producing duplicate active facts.
                subject = f.get("subject", "")
                parts.append(
                    f"    [{tier}] subject={subject} "
                    f"predicate={f['predicate']} :: {f['content']}"
                )
            parts.append("  </facts>")
        if self.episodes:
            parts.append("  <episodes>")
            for e in self.episodes:
                tier = e.get("relevance", "standard")
                parts.append(f"    [{tier}] [{e['task_type']}] {e['title']}: {e['summary']}")
            parts.append("  </episodes>")
        if self.recent:
            parts.append("  <recent>")
            for r in self.recent:
                parts.append(f"    turn {r['turn_index']} {r['event_type']}: {r['payload']}")
            parts.append("  </recent>")
        parts.append("</context>")
        return "\n".join(parts)

    def token_estimate(self) -> int:
        return len(self.to_prompt_text()) // 4


# Tier ordering: items at or above the configured floor are kept.
# "low" floor accepts everything; "high" floor accepts only [high].
_TIER_ORDER = {"low": 0, "standard": 1, "high": 2}


def _envelope_promotion(p: PromotionResult) -> dict:
    """Shape one PromotionResult into a six-field envelope entry."""
    is_fact = (
        p.outcome in ("written", "superseded")
        and (p.record_id or "").startswith("fact_")
    )
    is_pref = p.outcome == "written" and p.record_id and not is_fact
    if is_fact:
        ptype = "fact"
    elif is_pref:
        ptype = "preference"
    else:
        ptype = "other"
    return {
        "type": ptype,
        "fact_id": p.record_id if is_fact else None,
        "confidence": p.confidence,
        "status": p.status,
        "outcome": p.outcome,
        "reason": p.reason,
    }


# Single-word confirmations. Deterministic match: weaker models won't
# reliably reach into <recent> for "yep" / "correct".
_BARE_CONFIRM_RE = re.compile(
    r"^\s*(yes|yep|yeah|correct|right|that['’]?s\s+right|"
    r"ok|okay|sure|confirmed|please\s+update(\s+it)?)"
    r"[\s.!,]*$",
    re.IGNORECASE,
)

# Hedge phrases. Keep in sync with the preamble and with
# _EXTRACTION_BRIEF rule 2d (memory/extraction.py) — drift between
# the three lets the agent acknowledge an update the gate ignored.
_HEDGE_RE = re.compile(
    r"\b(i\s+think|i\s+thought|i\s+believe|i\s+recall|i\s+remember|"
    r"maybe|perhaps|i\s*['’]?m\s+not\s+sure|"
    r"i\s+heard|might\s+be|could\s+be)\b",
    re.IGNORECASE,
)


class MemoryManager:
    def __init__(
        self,
        conn: oracledb.AsyncConnection,
        model: SimulatedModel | OpenAIModel,
        extractor: RuleBasedExtractor | LLMExtractor,
        retrieval_mode: str = "hybrid",
        min_relevance_tier: str = "low",
    ):
        if min_relevance_tier not in _TIER_ORDER:
            raise ValueError(
                f"min_relevance_tier must be one of {list(_TIER_ORDER)}, "
                f"got {min_relevance_tier!r}"
            )
        self.conn = conn
        self.policy = PolicyStore(conn)
        self.preference = PreferenceStore(conn)
        self.fact = FactStore(conn)
        self.episodic = EpisodicStore(conn)
        self.trace = TraceStore(conn)
        self.model = model
        self.extractor = extractor
        self.retrieval_mode = retrieval_mode
        self.min_relevance_tier = min_relevance_tier
        self.gate = PromotionGate(
            self.fact, self.preference, self.episodic, manager=self,
        )
        # Last extractor output, before the gate adjudicated it.
        self.last_candidates: list = []
        # "combined" = inline from the structured-output call; "extractor" =
        # configured extractor ran separately. None until the first turn.
        self.last_candidates_source: str | None = None
        # Set when the bare-confirmation synthesizer rewrites the user
        # message; surfaced by the CLI's verbose mode.
        self.last_synthesized_message: str | None = None
        # Last assembled context; rendered by the CLI's /prompt command.
        self.last_context: PromptContext | None = None

    def _passes_tier(self, row: RetrievedRow) -> bool:
        """rank_score=None rows (policy/preference/trace) are tier 'standard'
        and pass any floor at or below 'standard'."""
        return _TIER_ORDER[row.relevance] >= _TIER_ORDER[self.min_relevance_tier]

    async def assemble_context(
        self, session: AgentSession, query_text: str
    ) -> PromptContext:
        result = await assemble(
            self.conn,
            tenant_id=session.tenant_id,
            user_id=session.user_id,
            run_id=session.run_id,
            query_text=query_text,
            mode=self.retrieval_mode,
        )
        ctx = PromptContext(retrieval_mode=result.mode)
        # Tier filter applies to facts and episodes only. Policies,
        # preferences, and recent trace are unfiltered.
        ctx.policies = [r.payload for r in result.by_kind("policy")]
        ctx.preferences = [r.payload for r in result.by_kind("preference")]
        ctx.facts = [
            {**r.payload, "relevance": r.relevance}
            for r in result.by_kind("fact")
            if self._passes_tier(r)
        ]
        ctx.episodes = [
            {**r.payload, "relevance": r.relevance}
            for r in result.by_kind("episodic")
            if self._passes_tier(r)
        ]
        ctx.recent = [r.payload for r in result.by_kind("trace")]
        self.last_context = ctx
        return ctx

    async def handle_turn(
        self, session: AgentSession, user_message: str
    ) -> tuple[ModelResponse, PromptContext, list[PromotionResult]]:
        """Five-step turn loop, executed synchronously so the CLI can show
        all results inline. Extraction runs after the model response is
        generated."""
        # 1. Trace user message.
        await self.trace.write(
            session.run_id, session.tenant_id, session.user_id,
            session.turn_index, "user_msg", {"text": user_message},
        )

        # 2. Assemble context.
        context = await self.assemble_context(session, user_message)
        prompt_text = context.to_prompt_text()

        # 3. Call model. OpenAIModel does combined reply + extraction in
        #    one structured-output call when identity kwargs are provided;
        #    SimulatedModel accepts the kwargs for parity but ignores them
        #    and leaves response.candidates = None so the extractor runs
        #    in a second step below.
        response = await self.model.complete(
            prompt_text, user_message,
            tenant_id=session.tenant_id,
            user_id=session.user_id,
            run_id=session.run_id,
            source_turn_id=str(session.turn_index),
        )

        # 4. Trace model message.
        await self.trace.write(
            session.run_id, session.tenant_id, session.user_id,
            session.turn_index, "model_msg",
            {"text": response.text, "input_tokens": response.input_tokens,
             "output_tokens": response.output_tokens},
            token_cost=response.input_tokens + response.output_tokens,
        )

        # 5. Extract and promote (synchronously here, so the CLI can show
        # results). If the model returned candidates inline (combined call),
        # the extractor is bypassed; otherwise extract_and_promote calls
        # the configured extractor against the user message.
        promotions = await self.extract_and_promote(
            session, user_message,
            assembled_prompt=prompt_text,
            model_response=response.text,
            pre_extracted_candidates=response.candidates,
        )

        # 6. Write the per-turn trace envelope.
        envelope = {
            "run_id": session.run_id,
            "turn_index": session.turn_index,
            "tenant_id": session.tenant_id,
            "user_id": session.user_id,
            "retrieval": {
                "facts_returned": [f.get("fact_id") for f in context.facts if f.get("fact_id")],
                "episodes_returned": [e.get("episode_id") for e in context.episodes if e.get("episode_id")],
                "preferences_applied": [p.get("pref_key") for p in context.preferences if p.get("pref_key")],
                "retrieval_mode": context.retrieval_mode,
            },
            "model_call": {
                "model": type(self.model).__name__,
                "input_tokens": response.input_tokens,
                "output_tokens": response.output_tokens,
            },
            "promotions": [
                _envelope_promotion(p)
                for p in promotions
            ],
        }
        await self.trace.write(
            session.run_id, session.tenant_id, session.user_id,
            session.turn_index, "turn_envelope", envelope,
            token_cost=response.input_tokens + response.output_tokens,
        )

        session.advance_turn()
        return response, context, promotions

    async def _synthesize_confirmed_message(
        self, session: AgentSession, user_message: str
    ) -> str | None:
        """If user_message is a bare confirmation and the prior user_msg
        was hedged, return the hedge-stripped prior text with a
        'Confirmed:' marker. Returns None when the pattern doesn't fire.

        Deterministic in code because weaker models won't reliably reach
        back into <recent> for a bare 'yep'."""
        if not _BARE_CONFIRM_RE.match(user_message.strip()):
            return None

        trace = await self.trace.get_run(session.run_id)
        # Most recent strictly-earlier user_msg in this run.
        prior_text = ""
        for event in reversed(trace):
            if (
                event["event_type"] == "user_msg"
                and event["turn_index"] < session.turn_index
            ):
                prior_text = (event.get("payload") or {}).get("text", "")
                break

        if not prior_text or not _HEDGE_RE.search(prior_text):
            return None

        # Strip hedges and collapse whitespace. Fall back to the prior
        # text if stripping leaves nothing.
        stripped = _HEDGE_RE.sub("", prior_text).strip()
        stripped = re.sub(r"\s+", " ", stripped)
        body = stripped or prior_text

        # "Confirmed:" marker — gpt-4.1-mini won't extract a supersession
        # from hedge-stripped text without it.
        return f"Confirmed: {body}"

    async def extract_and_promote(
        self,
        session: AgentSession,
        user_message: str,
        assembled_prompt: str | None = None,
        model_response: str | None = None,
        pre_extracted_candidates: list[MemoryCandidate] | None = None,
    ) -> list[PromotionResult]:
        self.last_candidates = []
        self.last_candidates_source = None
        self.last_synthesized_message = None

        # If the user just confirmed a prior hedged statement, rewrite their
        # bare 'yep' into the prior turn's text with the hedge stripped.
        # The extractor then proposes the supersession candidate from what
        # looks like an explicit fresh statement.
        effective_message = user_message
        synthesized = await self._synthesize_confirmed_message(session, user_message)
        if synthesized is not None:
            self.last_synthesized_message = synthesized
            effective_message = synthesized
            await self.trace.write(
                session.run_id, session.tenant_id, session.user_id,
                session.turn_index, "confirmation_synthesis",
                {"original": user_message, "synthesized": synthesized},
            )
            # Synthesizer fired — discard any candidates produced inline by
            # the combined model call. Those candidates were extracted
            # against the bare confirmation ("yes"), which carries no value
            # on its own. We need a fresh extraction against the
            # synthesized text via the configured extractor.
            pre_extracted_candidates = None

        if pre_extracted_candidates is not None:
            # Combined call already produced candidates; bypass the extractor.
            self.last_candidates_source = "combined"
            candidates = list(pre_extracted_candidates)
            self.last_candidates = candidates
        else:
            self.last_candidates_source = "extractor"
            try:
                extract_fn = self.extractor.extract
                extract_kwargs = dict(
                    user_message=effective_message,
                    tenant_id=session.tenant_id, user_id=session.user_id,
                    agent_id=session.agent_id, run_id=session.run_id,
                    assembled_prompt=assembled_prompt,
                    model_response=model_response,
                )
                if inspect.iscoroutinefunction(extract_fn):
                    candidates = await extract_fn(**extract_kwargs)
                else:
                    candidates = extract_fn(**extract_kwargs)
                self.last_candidates = list(candidates)
            except Exception as e:
                await self.trace.write(
                    session.run_id, session.tenant_id, session.user_id,
                    session.turn_index, "extraction_error", {"error": str(e)},
                )
                return []

        results: list[PromotionResult] = []
        for cand in candidates:
            try:
                results.append(await self.gate.promote(cand))
            except Exception as e:
                await self.trace.write(
                    session.run_id, session.tenant_id, session.user_id,
                    session.turn_index, "promotion_error",
                    {"error": str(e), "candidate_type": cand.memory_type},
                )
        return results

    async def supersede_fact(
        self, old_fact_id: str, new_candidate: MemoryCandidate
    ) -> PromotionResult:
        chash = content_hash(new_candidate.content)
        # The contradiction itself is the confirmation event, so the
        # superseding fact enters as 'active' rather than 'provisional'.
        new_status = "active"
        new_fact_id = f"fact_{secrets.token_hex(6)}"
        cur = self.conn.cursor()
        await cur.execute(
            f"""
            INSERT INTO fact_memory
              (fact_id, tenant_id, user_id, agent_id, subject, predicate,
               content, content_hash, embedding, status,
               source_run_id, source_turn_id, confidence, created_at)
            VALUES
              (:fact_id, :tid, :u_id, :a_id, :subj, :pred,
               :content, :chash, {vector_embedding_sql(':content')}, :status,
               :run_id, :turn_id, :conf, :now)
            """,
            fact_id=new_fact_id, tid=new_candidate.tenant_id,
            u_id=new_candidate.user_id, a_id=new_candidate.agent_id,
            subj=new_candidate.subject, pred=new_candidate.predicate,
            content=new_candidate.content, chash=chash, status=new_status,
            run_id=new_candidate.source_run_id, turn_id=new_candidate.source_turn_id,
            conf=new_candidate.confidence,
            now=datetime.now(tz=timezone.utc),
        )
        await cur.execute(
            "UPDATE fact_memory SET superseded_by = :new_id, status = 'revoked' "
            "WHERE fact_id = :old_id",
            new_id=new_fact_id, old_id=old_fact_id,
        )
        await self.conn.commit()
        return PromotionResult.superseded(
            new_fact_id, old_fact_id, confidence=new_candidate.confidence,
        )

    async def cascade_erase(
        self, user_id: str, tenant_id: str, reason: str = "gdpr_erasure"
    ) -> dict:
        """GDPR cascade: revoke fact/episodic, delete preference/trace,
        write audit row. All in one transaction, scoped to tenant_id."""
        cur = self.conn.cursor()
        await cur.execute(
            """
            UPDATE fact_memory SET content = '[erased]',
                                   content_hash = 'erased',
                                   embedding = NULL,
                                   status = 'revoked'
             WHERE user_id = :u_id
               AND tenant_id = :tid
            """,
            u_id=user_id, tid=tenant_id,
        )
        await cur.execute(
            """
            UPDATE episodic_memory SET summary = '[erased]',
                                       embedding = NULL,
                                       status = 'revoked'
             WHERE user_id = :u_id
               AND tenant_id = :tid
            """,
            u_id=user_id, tid=tenant_id,
        )
        await cur.execute(
            "DELETE FROM preference_memory WHERE user_id = :u_id AND tenant_id = :tid",
            u_id=user_id, tid=tenant_id,
        )
        await cur.execute(
            "DELETE FROM trace_memory WHERE user_id = :u_id AND tenant_id = :tid",
            u_id=user_id, tid=tenant_id,
        )
        await cur.execute(
            """
            INSERT INTO deletion_events (user_id, scope, deleted_at, reason)
            VALUES (:u_id, 'all', :now, :reason)
            """,
            u_id=user_id, now=datetime.now(tz=timezone.utc), reason=reason,
        )
        await self.conn.commit()
        return {"user_id": user_id, "tenant_id": tenant_id, "reason": reason}
