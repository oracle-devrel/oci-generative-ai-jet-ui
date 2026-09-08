from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from limitless.graph.models import TopicPacket
from limitless.settings import Settings
from limitless.xp.hud import build_status_hud
from limitless.xp.session_service import (
    add_turn,
    build_diagnostic_from_packet,
    build_teaching_prompt,
    choose_teaching_order,
    create_db_session,
    finalize_session,
    get_concept,
    load_reviewed_topic_packet,
    make_session_state,
    next_hint,
    persist_turn,
    save_transcript_json,
)
from limitless.xp.models import SessionState, SessionTurn


SESSION_STATE_DIR = Path("content/session_state")
DIAGNOSIS_STATES = {"correct", "mostly-correct", "partial", "confused", "off-track"}
PEDAGOGICAL_ACTIONS = {
    "affirm-and-advance",
    "deepen-and-probe",
    "hint-and-retry",
    "reframe-and-retry",
    "contrast-and-clarify",
    "reset-and-reanchor",
}


def _state_path(session_key: str) -> Path:
    SESSION_STATE_DIR.mkdir(parents=True, exist_ok=True)
    return SESSION_STATE_DIR / f"{session_key}.json"


def save_session_state(state: SessionState) -> Path:
    path = _state_path(state.session_key)
    path.write_text(state.model_dump_json(indent=2), encoding="utf-8")
    return path


def load_session_state(session_key: str) -> SessionState:
    path = _state_path(session_key)
    return SessionState.model_validate_json(path.read_text(encoding="utf-8"))


def _recent_turns(turns: list[SessionTurn], limit: int = 4) -> list[dict[str, Any]]:
    trimmed = turns[-limit:]
    return [
        {
            "role": turn.role,
            "phase": turn.phase,
            "target_concept_ids": turn.target_concept_ids,
            "content": turn.content,
            "hints_used": turn.hints_used,
        }
        for turn in trimmed
    ]


def _hud(state: SessionState, packet: TopicPacket) -> str:
    target_label = None
    if state.current_target_concept:
        target_label = get_concept(packet, state.current_target_concept).label
    return build_status_hud(
        topic_title=state.topic_title,
        phase=state.phase,
        target_concept=target_label,
        hints_used=state.hints_used,
        concepts_covered=len(state.concepts_covered),
        grounding_label=state.grounding_label,
    )


def _record_assistant(state: SessionState, settings: Settings | None, content: str, target_concept_ids: list[str]) -> None:
    turn = add_turn(
        state,
        role="assistant",
        content=content,
        phase=state.phase,
        target_concept_ids=target_concept_ids,
        hints_used=state.hints_used,
        grounding_reference=state.grounding_label,
    )
    persist_turn(state, turn, settings)
    save_transcript_json(state)
    save_session_state(state)


def _record_user(state: SessionState, settings: Settings | None, content: str, target_concept_ids: list[str]) -> None:
    turn = add_turn(
        state,
        role="user",
        content=content,
        phase=state.phase,
        target_concept_ids=target_concept_ids,
    )
    persist_turn(state, turn, settings)
    save_transcript_json(state)
    save_session_state(state)


def _tokenize(text: str) -> list[str]:
    return [token for token in re.findall(r"[a-zA-Z][a-zA-Z\-]+", text.lower()) if len(token) >= 3]


def _concept_keywords(packet: TopicPacket, concept_id: str) -> set[str]:
    concept = get_concept(packet, concept_id)
    corpus = " ".join([concept.summary, *concept.supporting_snippets, *concept.diagnostic_prompts])
    return {token for token in _tokenize(corpus) if len(token) >= 5}


def _confusion_targets(packet: TopicPacket, concept_id: str, answer: str) -> list[str]:
    lower = answer.lower()
    concept = get_concept(packet, concept_id)
    confusions: list[str] = []
    for related_slug in concept.related_concepts:
        related_label = related_slug.replace("-", " ")
        if related_label in lower and related_slug != concept_id:
            confusions.append(related_slug)
    return confusions


def _diagnose_answer(packet: TopicPacket, concept_id: str, answer: str, retry_count: int) -> dict[str, Any]:
    concept = get_concept(packet, concept_id)
    lower = answer.lower().strip()
    keywords = _concept_keywords(packet, concept_id)
    answer_tokens = _tokenize(answer)
    overlap = [token for token in answer_tokens if token in keywords]
    confusions = _confusion_targets(packet, concept_id, answer)

    what_is_correct: list[str] = []
    what_is_missing: list[str] = []

    if concept_id == "episodic-memory" and any(word in lower for word in ["past", "event", "previous", "history"]):
        what_is_correct.append("You tied episodic memory to prior events and outcomes.")
    if concept_id == "semantic-memory" and any(word in lower for word in ["fact", "knowledge", "rule", "preference"]):
        what_is_correct.append("You framed semantic memory as stable knowledge.")
    if concept_id == "procedural-memory" and any(word in lower for word in ["skill", "routine", "workflow", "tool", "method"]):
        what_is_correct.append("You connected procedural memory to repeatable methods or workflows.")

    if not what_is_correct:
        what_is_missing.append(f"You have not yet landed the core distinction for {concept.label}.")
    if len(answer_tokens) < 8:
        what_is_missing.append("The answer is too short to prove the distinction clearly.")
    if confusions:
        what_is_missing.append("A related concept appears to be bleeding into the explanation.")

    if not lower:
        state = "off-track"
        confidence = 0.1
    elif any(marker in lower for marker in ["don't know", "dont know", "not sure", "unsure"]):
        state = "confused"
        confidence = 0.25
    elif len(answer_tokens) < 5:
        state = "off-track"
        confidence = 0.2
    elif confusions and retry_count > 0:
        state = "confused"
        confidence = 0.4
    elif len(overlap) >= 4 and len(answer_tokens) >= 20 and not confusions:
        state = "correct"
        confidence = 0.9
    elif len(overlap) >= 2 and len(answer_tokens) >= 14 and not confusions:
        state = "mostly-correct"
        confidence = 0.75
    elif confusions:
        state = "confused"
        confidence = 0.45
    elif len(overlap) >= 1 or len(answer_tokens) >= 10:
        state = "partial"
        confidence = 0.58
    else:
        state = "off-track"
        confidence = 0.3

    return {
        "state": state,
        "confidence": round(confidence, 2),
        "what_is_correct": what_is_correct,
        "what_is_missing": what_is_missing,
        "confusions": confusions,
        "keyword_overlap": overlap,
    }


def _followup_prompt_for(concept_id: str, concept_label: str, contrast_with: str | None) -> str:
    if concept_id == "episodic-memory":
        return "Good. Now sharpen it: what makes episodic memory different from semantic memory if both can be useful later?"
    if concept_id == "semantic-memory":
        return "Good. Now sharpen it: what makes semantic memory stable knowledge rather than a remembered episode?"
    if concept_id == "procedural-memory":
        return "Good. Now sharpen it: how is procedural memory about methods and workflows, not just stored facts?"
    if concept_id == "goal":
        return "Good. Now sharpen it: what makes a goal specific enough to judge success later?"
    if concept_id == "context-retrieval":
        return "Good. Now sharpen it: how is context retrieval different from just throwing everything into the context window?"
    if concept_id == "tool-selection":
        return "Good. Now sharpen it: how is tool selection different from execution when both happen in the same loop?"
    if concept_id == "execution":
        return "Good. Now sharpen it: what counts as execution succeeding, even before evaluation checks whether it was useful?"
    if concept_id == "evaluation":
        return "Good. Now sharpen it: can execution succeed while evaluation still fails? Give a concrete case."
    if concept_id == "memory-update":
        return "Good. Now sharpen it: what deserves to persist after the loop, and what should be left behind?"
    return f"Good. Now sharpen it: what is the clearest distinction between {concept_label} and {contrast_with.replace('-', ' ') if contrast_with else 'the nearest related concept'}?"


def _retry_prompt_for(concept_id: str, concept_label: str) -> str:
    if concept_id == "episodic-memory":
        return "Try again in your own words: what makes episodic memory about a specific past run instead of stable knowledge?"
    if concept_id == "semantic-memory":
        return "Try again in your own words: what makes semantic memory stable knowledge instead of a remembered event?"
    if concept_id == "procedural-memory":
        return "Try again in your own words: what makes procedural memory about repeatable methods rather than facts?"
    if concept_id == "goal":
        return "Try again in your own words: what makes a goal specific enough that the agent could later judge success?"
    if concept_id == "context-retrieval":
        return "Try again in your own words: why is context retrieval more selective than just stuffing everything into the context window?"
    if concept_id == "tool-selection":
        return "Try again in your own words: how is choosing a tool different from actually running it?"
    if concept_id == "execution":
        return "Try again in your own words: what makes execution the action step rather than the judgment step?"
    if concept_id == "evaluation":
        return "Try again in your own words: how can evaluation fail even when execution technically succeeded?"
    if concept_id == "memory-update":
        return "Try again in your own words: what should persist after the loop, and what should not?"
    return f"Try again in your own words: what makes {concept_label} distinct here?"


def _concept_reframe_target(concept_id: str) -> str:
    if concept_id == "episodic-memory":
        return "what happened before in a specific run"
    if concept_id == "semantic-memory":
        return "what stays true across runs"
    if concept_id == "procedural-memory":
        return "how to do something repeatedly"
    if concept_id == "goal":
        return "what the agent is actually trying to accomplish"
    if concept_id == "context-retrieval":
        return "what information deserves to be pulled into the current turn"
    if concept_id == "tool-selection":
        return "which capability should be used before anything runs"
    if concept_id == "execution":
        return "the moment an action is actually taken in the environment"
    if concept_id == "evaluation":
        return "the check against the goal after the action happens"
    if concept_id == "memory-update":
        return "what should persist after the loop ends"
    return "the concept's core job in the system"


def _analysis_context(packet: TopicPacket, state: SessionState, concept_id: str, answer: str) -> dict[str, Any]:
    concept = get_concept(packet, concept_id)
    return {
        "latest_answer": answer,
        "active_concept": {
            "slug": concept.id,
            "label": concept.label,
            "summary": concept.summary,
            "supporting_snippets": concept.supporting_snippets,
            "related_concepts": concept.related_concepts,
            "diagnostic_prompts": concept.diagnostic_prompts,
            "hint_reframe_ladder": concept.hint_reframe_ladder,
        },
        "recent_turns": _recent_turns(state.turns, limit=4),
        "hint_state": {
            "hints_used_total": state.hints_used,
            "retry_count_for_current": state.retry_count_for_current,
        },
    }


def _pedagogical_action(packet: TopicPacket, state: SessionState, concept_id: str, diagnosis: dict[str, Any]) -> dict[str, Any]:
    concept = get_concept(packet, concept_id)
    state_name = diagnosis["state"]
    hint = next_hint(packet, concept_id, state.retry_count_for_current)
    contrast_with = diagnosis["confusions"][0] if diagnosis["confusions"] else (concept.related_concepts[0] if concept.related_concepts else None)

    if state_name == "correct":
        mode = "affirm-and-advance"
        pedagogical_intent = "Confirm the strong answer and move forward without slowing momentum."
        next_prompt = None
        reframe = None
    elif state_name == "mostly-correct":
        mode = "deepen-and-probe"
        pedagogical_intent = "Push for sharper distinctions or one more level of precision before moving on."
        next_prompt = _followup_prompt_for(concept_id, concept.label, contrast_with)
        reframe = None
    elif state_name == "partial":
        mode = "reframe-and-retry" if state.retry_count_for_current > 0 else "hint-and-retry"
        pedagogical_intent = "Keep the learner on the same concept and strengthen the explanation before advancing."
        next_prompt = _retry_prompt_for(concept_id, concept.label)
        reframe_target = _concept_reframe_target(concept_id)
        reframe = f"Think about {concept.label} as the part of the agent that answers: {reframe_target}."
    elif state_name == "confused":
        mode = "contrast-and-clarify"
        pedagogical_intent = "Force an explicit contrast so the learner stops blending related concepts together."
        next_prompt = f"Let's separate them clearly: how is {concept.label} different from {contrast_with.replace('-', ' ') if contrast_with else 'the concept you just blurred it with'}?"
        reframe = f"One way to think about it: {concept.label} is not just adjacent knowledge - it has its own job in the system."
    else:
        mode = "reset-and-reanchor"
        pedagogical_intent = "Reset the explanation and re-anchor the learner to the concept's core job."
        next_prompt = f"Let's reset. In one sentence: what is {concept.label} responsible for in this system?"
        anchor_target = _concept_reframe_target(concept_id)
        reframe = f"Anchor it to the simplest possible frame: {concept.label} is about {anchor_target}."

    if mode in {"hint-and-retry", "reframe-and-retry", "contrast-and-clarify", "reset-and-reanchor"}:
        hint_value = hint
    else:
        hint_value = None

    return {
        "mode": mode,
        "hint": hint_value,
        "reframe": reframe,
        "contrast_with": contrast_with,
        "next_prompt": next_prompt,
        "pedagogical_intent": pedagogical_intent,
    }


def _response_guidance(concept: TopicPacket | Any, diagnosis: dict[str, Any], action: dict[str, Any]) -> dict[str, Any]:
    state_name = diagnosis["state"]
    mode = action["mode"]
    must_acknowledge = diagnosis["what_is_correct"][:1]
    must_clarify = diagnosis["what_is_missing"][:1]
    stay_on_concept = mode in {
        "deepen-and-probe",
        "hint-and-retry",
        "reframe-and-retry",
        "contrast-and-clarify",
        "reset-and-reanchor",
    }

    acknowledgement_line = (
        must_acknowledge[0]
        if must_acknowledge
        else f"We are still working on {concept.label}."
    )
    teaching_move_line = action.get("reframe") or (action.get("hint") if action.get("hint") else action.get("pedagogical_intent"))
    prompt_handoff = "Ask the next prompt exactly once after the teaching move."

    return {
        "tone": "sharp, supportive, concise",
        "must_acknowledge": must_acknowledge,
        "must_clarify": must_clarify,
        "stay_on_concept": stay_on_concept,
        "advance_allowed": not stay_on_concept,
        "acknowledgement_line": acknowledgement_line,
        "teaching_move_line": teaching_move_line,
        "prompt_handoff": prompt_handoff,
        "avoid": [
            "Do not dump a full lecture.",
            "Do not pretend the learner is fully correct if they are not.",
            "Do not skip the contrast if the diagnosis says confused.",
            "Do not repeat the next prompt twice.",
        ],
        "rendering_hint": (
            "Use one short acknowledgement, then the teaching move, then the next prompt."
            if state_name in {"correct", "mostly-correct"}
            else "Use a brief correction, then the teaching move, then the retry prompt."
        ),
    }


def _build_tutor_message(packet: TopicPacket, concept_id: str, diagnosis: dict[str, Any], action: dict[str, Any]) -> str:
    concept = get_concept(packet, concept_id)
    state_name = diagnosis["state"]
    correct = diagnosis["what_is_correct"]
    missing = diagnosis["what_is_missing"]

    lines: list[str] = []
    if state_name == "correct":
        lines.append(correct[0] if correct else f"Good — that lands {concept.label} cleanly.")
    elif state_name == "mostly-correct":
        lines.append(correct[0] if correct else f"You're close on {concept.label}. I want one sharper distinction before we move on.")
    elif state_name == "partial":
        lines.append(f"You're part of the way there on {concept.label}, but I want one cleaner distinction before we move on.")
    elif state_name == "confused":
        lines.append(f"You're close, but you're blending {concept.label} with another nearby concept.")
    else:
        lines.append(f"Let's reset and anchor {concept.label} more clearly.")

    if action["hint"]:
        lines.append(f"Hint: {action['hint']}")
    if action["reframe"]:
        lines.append(f"Reframe: {action['reframe']}")
    if missing and state_name not in {"correct", "mostly-correct"}:
        lines.append(f"What is missing: {missing[0]}")
    return " ".join(lines)


def _next_prompt(state: SessionState, packet: TopicPacket) -> str | None:
    if state.phase == "diagnostic":
        prompts = build_diagnostic_from_packet(packet)
        if state.current_index < len(prompts):
            prompt = prompts[state.current_index]
            state.current_target_concept = prompt.target_concept_ids[0]
            state.current_prompt_text = prompt.text
            return prompt.text
        state.phase = "teaching"
        state.current_index = 0
        state.retry_count_for_current = 0

    if state.phase == "teaching":
        if state.current_index < len(state.teaching_order):
            concept_id = state.teaching_order[state.current_index]
            state.current_target_concept = concept_id
            prompt = build_teaching_prompt(packet, concept_id)
            state.current_prompt_text = prompt
            return prompt
        state.phase = "wrapup"
        state.current_target_concept = None
        state.current_prompt_text = None
        return None

    return None


def start_session(topic_slug: str, focus_concept_id: str | None = None, settings: Settings | None = None) -> dict[str, Any]:
    packet = load_reviewed_topic_packet(topic_slug)
    state = make_session_state(packet)
    state.diagnostic_concepts = [concept.id for concept in packet.concepts]
    state.teaching_order = choose_teaching_order(packet, focus_concept_id)
    create_db_session(state, settings)
    save_transcript_json(state)
    save_session_state(state)
    prompt = _next_prompt(state, packet)
    if prompt:
        _record_assistant(state, settings, prompt, [state.current_target_concept] if state.current_target_concept else [])

    transcript_path = save_transcript_json(state)
    state_path = save_session_state(state)
    return {
        "session_key": state.session_key,
        "state_path": str(state_path),
        "transcript_path": str(transcript_path),
        "phase": state.phase,
        "status": state.status,
        "hud": _hud(state, packet),
        "prompt": state.current_prompt_text,
    }


def answer_session(session_key: str, answer: str, settings: Settings | None = None) -> dict[str, Any]:
    packet = load_reviewed_topic_packet(load_session_state(session_key).topic_slug)
    state = load_session_state(session_key)
    concept_id = state.current_target_concept
    if concept_id is None:
        raise ValueError("No active concept in session. Use finish or start a new session.")

    _record_user(state, settings, answer, [concept_id])
    if concept_id not in state.concepts_covered:
        state.concepts_covered.append(concept_id)

    diagnosis = _diagnose_answer(packet, concept_id, answer, state.retry_count_for_current)
    action = _pedagogical_action(packet, state, concept_id, diagnosis)
    analysis_context = _analysis_context(packet, state, concept_id, answer)
    response_guidance = _response_guidance(get_concept(packet, concept_id), diagnosis, action)

    requires_followup = action["mode"] in {
        "deepen-and-probe",
        "hint-and-retry",
        "reframe-and-retry",
        "contrast-and-clarify",
        "reset-and-reanchor",
    }

    tutor_message = _build_tutor_message(packet, concept_id, diagnosis, action)

    if requires_followup:
        if action["mode"] in {"hint-and-retry", "reframe-and-retry", "contrast-and-clarify", "reset-and-reanchor"}:
            state.retry_count_for_current += 1
        if action["hint"]:
            state.hints_used += 1
        state.current_prompt_text = action["next_prompt"] or state.current_prompt_text
        _record_assistant(state, settings, tutor_message, [concept_id])
        return {
            "session_key": state.session_key,
            "phase": state.phase,
            "status": state.status,
            "hud": _hud(state, packet),
            "analysis_context": analysis_context,
            "tutoring_contract": {
                "diagnosis": diagnosis,
                "pedagogical_action": action,
                "response_guidance": response_guidance,
            },
            "tutor_message": tutor_message,
            "prompt": state.current_prompt_text,
            "awaiting_retry": action["mode"] != "deepen-and-probe",
            "finished": False,
        }

    state.current_index += 1
    state.retry_count_for_current = 0
    next_prompt = _next_prompt(state, packet)

    if next_prompt is None:
        state.status = "finished"
        finalize_session(state, state.status, settings)
        closing = "Good stopping point. Run XP Debrief next to assess what changed."
        full_message = f"{tutor_message} {closing}"
        _record_assistant(state, settings, full_message, [concept_id])
        transcript_path = save_transcript_json(state)
        save_session_state(state)
        return {
            "session_key": state.session_key,
            "phase": state.phase,
            "status": state.status,
            "hud": _hud(state, packet),
            "analysis_context": analysis_context,
            "tutoring_contract": {
                "diagnosis": diagnosis,
                "pedagogical_action": {
                    **action,
                    "mode": "affirm-and-advance",
                    "next_prompt": None,
                    "pedagogical_intent": "Close the session after a sufficient answer and hand off to XP Debrief.",
                },
                "response_guidance": response_guidance,
            },
            "tutor_message": full_message,
            "prompt": None,
            "transcript_path": str(transcript_path),
            "finished": True,
        }

    _record_assistant(state, settings, f"{tutor_message}\n\n{next_prompt}", [state.current_target_concept] if state.current_target_concept else [concept_id])
    save_session_state(state)
    transcript_path = save_transcript_json(state)
    return {
        "session_key": state.session_key,
        "phase": state.phase,
        "status": state.status,
        "hud": _hud(state, packet),
        "analysis_context": analysis_context,
        "tutoring_contract": {
            "diagnosis": diagnosis,
            "pedagogical_action": {**action, "next_prompt": next_prompt},
            "response_guidance": response_guidance,
        },
        "tutor_message": tutor_message,
        "prompt": next_prompt,
        "awaiting_retry": False,
        "transcript_path": str(transcript_path),
        "finished": False,
    }


def hint_session(session_key: str, settings: Settings | None = None) -> dict[str, Any]:
    state = load_session_state(session_key)
    packet = load_reviewed_topic_packet(state.topic_slug)
    if state.current_target_concept is None:
        raise ValueError("No active concept in session.")
    hint = next_hint(packet, state.current_target_concept, state.retry_count_for_current)
    state.hints_used += 1
    state.retry_count_for_current += 1
    _record_assistant(state, settings, f"Hint: {hint}", [state.current_target_concept])
    return {
        "session_key": state.session_key,
        "phase": state.phase,
        "status": state.status,
        "hud": _hud(state, packet),
        "analysis_context": _analysis_context(packet, state, state.current_target_concept, ""),
        "tutoring_contract": {
            "diagnosis": {
                "state": "partial",
                "confidence": 0.4,
                "what_is_correct": [],
                "what_is_missing": ["The learner explicitly requested help."],
                "confusions": [],
                "keyword_overlap": [],
            },
            "pedagogical_action": {
                "mode": "hint-and-retry",
                "hint": hint,
                "reframe": None,
                "contrast_with": None,
                "next_prompt": state.current_prompt_text,
                "pedagogical_intent": "Provide a small nudge and keep the learner on the same concept.",
            },
            "response_guidance": {
                "tone": "sharp, supportive, concise",
                "must_acknowledge": [],
                "must_clarify": ["The learner explicitly requested help."],
                "stay_on_concept": True,
                "advance_allowed": False,
                "avoid": [
                    "Do not dump a full lecture.",
                    "Do not move on before the learner retries.",
                ],
                "rendering_hint": "Use one short hint and ask for a retry."
            },
        },
        "tutor_message": f"Hint: {hint}",
        "prompt": state.current_prompt_text,
    }


def status_session(session_key: str) -> dict[str, Any]:
    state = load_session_state(session_key)
    packet = load_reviewed_topic_packet(state.topic_slug)
    return {
        "session_key": state.session_key,
        "phase": state.phase,
        "status": state.status,
        "hud": _hud(state, packet),
        "prompt": state.current_prompt_text,
        "analysis_context": _analysis_context(packet, state, state.current_target_concept, "") if state.current_target_concept else None,
    }


def finish_session(session_key: str, settings: Settings | None = None) -> dict[str, Any]:
    state = load_session_state(session_key)
    packet = load_reviewed_topic_packet(state.topic_slug)
    state.status = "finished"
    finalize_session(state, state.status, settings)
    transcript_path = save_transcript_json(state)
    save_session_state(state)
    return {
        "session_key": state.session_key,
        "phase": state.phase,
        "status": state.status,
        "hud": _hud(state, packet),
        "prompt": None,
        "transcript_path": str(transcript_path),
        "finished": True,
    }
