"""Pluggable model layer.

Defaults to SimulatedModel; uses OpenAI when OPENAI_API_KEY is set.

OpenAIModel does a combined structured-output call that returns the
reply and extraction candidates in one API request. The manager reads
ModelResponse.candidates and skips its configured extractor when they
arrive inline. Two-call fallback runs for SimulatedModel and for the
bare-confirmation synthesizer (which rewrites the user_message after
the main call, so candidates must be re-extracted from the rewrite).
"""
from __future__ import annotations
import json
import os
from dataclasses import dataclass, field
from typing import Any

from memory.records import MemoryCandidate


@dataclass
class ModelResponse:
    text: str
    tool_calls: list[dict[str, Any]]
    input_tokens: int
    output_tokens: int
    # Parsed candidates from the combined call. None means "run the
    # configured extractor in a second pass."
    candidates: list[MemoryCandidate] | None = None


class SimulatedModel:
    """Deterministic templated response. References preferences/facts
    from the prompt context so the demo shows context taking effect.
    Accepts identity kwargs for OpenAIModel parity but ignores them;
    extraction always runs as a second pass."""

    async def complete(
        self,
        prompt_text: str,
        user_message: str,
        *,
        tenant_id: str | None = None,
        user_id: str | None = None,
        run_id: str | None = None,
        source_turn_id: str | None = None,
    ) -> ModelResponse:
        _ = (tenant_id, user_id, run_id, source_turn_id)  # interface parity
        terse = "terse" in prompt_text.lower()
        if terse:
            text = f"Acknowledged: {user_message[:60]}"
        else:
            text = (
                f"Got it. I see you said: {user_message!r}. "
                f"Drawing on what we already know, here's an acknowledgement."
            )
        return ModelResponse(
            text=text, tool_calls=[],
            input_tokens=len(prompt_text) // 4,
            output_tokens=len(text) // 4,
        )


# The extraction brief's normal "OUTPUT FORMAT" section expects a
# {facts, preferences} JSON object. In the combined call we override
# that with a wrapper that ALSO includes the reply text. This trailing
# block follows the brief in the system message so the model sees the
# extraction rules first and the combined schema last.
_COMBINED_OUTPUT_INSTRUCTION = """
== COMBINED OUTPUT FORMAT (OVERRIDES the OUTPUT FORMAT section above) ==

Return ONE JSON object containing BOTH your conversational reply AND
any memory extraction candidates from the user's latest message:

{
  "reply": "<your conversational reply to the user — plain text, follows the agent rules at the top of this system message>",
  "facts": [
    {"subject": "...", "predicate": "...", "content": "...", "confidence": 0.7-1.0}
  ],
  "preferences": [
    {"pref_key": "...", "pref_value": <any>, "confidence": 0.7-1.0}
  ]
}

The reply field is REQUIRED on every turn. If no extraction candidates
apply (most turns), set facts and preferences to empty arrays. Apply
all extraction rules from the brief above — hedge rejection, source-of-
truth, dedup against context, etc.
"""


class OpenAIModel:
    def __init__(self, model: str = "gpt-4.1-mini"):
        from openai import AsyncOpenAI
        self.client = AsyncOpenAI()
        self.model = model

    async def complete(
        self,
        prompt_text: str,
        user_message: str,
        *,
        tenant_id: str | None = None,
        user_id: str | None = None,
        run_id: str | None = None,
        source_turn_id: str | None = None,
    ) -> ModelResponse:
        """Combined reply+extraction when identity kwargs are present;
        reply-only otherwise."""
        combined = (
            tenant_id is not None and user_id is not None and run_id is not None
        )

        if combined:
            return await self._complete_combined(
                prompt_text, user_message,
                tenant_id=tenant_id, user_id=user_id,
                run_id=run_id, source_turn_id=source_turn_id,
            )
        return await self._complete_reply_only(prompt_text, user_message)

    async def _complete_combined(
        self,
        prompt_text: str,
        user_message: str,
        *,
        tenant_id: str,
        user_id: str,
        run_id: str,
        source_turn_id: str | None,
    ) -> ModelResponse:
        # Lazy import keeps the dependency arrow model -> extraction.
        from memory.extraction import _EXTRACTION_BRIEF, parse_candidates_dict

        system_content = (
            f"{prompt_text}\n\n"
            f"== MEMORY EXTRACTION (alongside your reply, same turn) ==\n\n"
            f"{_EXTRACTION_BRIEF}"
            f"{_COMBINED_OUTPUT_INSTRUCTION}"
        )
        user_content = f"Current user message:\n\n{user_message}"

        resp = await self.client.chat.completions.create(
            model=self.model,
            response_format={"type": "json_object"},
            temperature=0,
            messages=[
                {"role": "system", "content": system_content},
                {"role": "user", "content": user_content},
            ],
        )
        try:
            data = json.loads(resp.choices[0].message.content or "{}")
        except json.JSONDecodeError:
            data = {}

        candidates = parse_candidates_dict(
            data,
            tenant_id=tenant_id, user_id=user_id, run_id=run_id,
            source_turn_id=source_turn_id, user_message=user_message,
        )
        return ModelResponse(
            text=(data.get("reply") or ""),
            tool_calls=[],
            input_tokens=resp.usage.prompt_tokens if resp.usage else 0,
            output_tokens=resp.usage.completion_tokens if resp.usage else 0,
            candidates=candidates,
        )

    async def _complete_reply_only(
        self, prompt_text: str, user_message: str
    ) -> ModelResponse:
        # Marker distinguishes the live message from <recent> events.
        resp = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": prompt_text},
                {"role": "user", "content": f"Current user message:\n\n{user_message}"},
            ],
        )
        choice = resp.choices[0]
        return ModelResponse(
            text=choice.message.content or "",
            tool_calls=[],
            input_tokens=resp.usage.prompt_tokens if resp.usage else 0,
            output_tokens=resp.usage.completion_tokens if resp.usage else 0,
            candidates=None,
        )


def model_from_env() -> SimulatedModel | OpenAIModel:
    if os.getenv("FORCE_SIMULATED"):
        return SimulatedModel()
    if os.getenv("OPENAI_API_KEY"):
        return OpenAIModel(model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"))
    return SimulatedModel()
