from __future__ import annotations

import json
import uuid
from pathlib import Path

import oracledb

from limitless.db.pool import get_pool
from limitless.graph.models import ConceptPacket, TopicPacket
from limitless.research.packet_loader import load_topic_packet
from limitless.settings import Settings
from limitless.xp.models import DiagnosticPrompt, SessionState, SessionTurn


def slug_to_label(slug: str) -> str:
    return slug.replace("-", " ").title()


def load_reviewed_topic_packet(topic_slug: str) -> TopicPacket:
    packet_dir = Path("content/concept_packets")
    review_json = packet_dir / f"{topic_slug}.reviewed.json"
    review_md = packet_dir / f"{topic_slug}.review.md"
    research_md = Path("content/research") / f"{topic_slug}.md"
    return load_topic_packet(review_json, review_md, research_md)


def build_initial_diagnostic(concept_ids: list[str]) -> list[DiagnosticPrompt]:
    prompts: list[DiagnosticPrompt] = []
    for concept_id in concept_ids:
        label = slug_to_label(concept_id)
        prompts.append(
            DiagnosticPrompt(
                prompt_id=f"diagnostic-{concept_id}",
                target_concept_ids=[concept_id],
                text=f"Let’s focus on {label} for a second. What does it mean in this system, in your own words?",
            )
        )
    return prompts


def build_diagnostic_from_packet(packet: TopicPacket) -> list[DiagnosticPrompt]:
    prompts: list[DiagnosticPrompt] = []
    for concept in packet.concepts:
        text = concept.diagnostic_prompts[0] if concept.diagnostic_prompts else f"What is {concept.label} in your own words?"
        if not text.lower().startswith("let"):
            text = f"Let's focus on {concept.label} for a second. {text}"
        prompts.append(
            DiagnosticPrompt(
                prompt_id=f"diagnostic-{concept.id}",
                target_concept_ids=[concept.id],
                text=text,
            )
        )
    return prompts


def choose_teaching_order(packet: TopicPacket, weak_concept_id: str | None = None) -> list[str]:
    concept_ids = [concept.id for concept in packet.concepts]
    if weak_concept_id and weak_concept_id in concept_ids:
        return [weak_concept_id] + [concept_id for concept_id in concept_ids if concept_id != weak_concept_id]
    return concept_ids


def get_concept(packet: TopicPacket, concept_id: str) -> ConceptPacket:
    for concept in packet.concepts:
        if concept.id == concept_id:
            return concept
    raise KeyError(f"Unknown concept: {concept_id}")


def build_teaching_prompt(packet: TopicPacket, concept_id: str) -> str:
    concept = get_concept(packet, concept_id)
    secondary = concept.diagnostic_prompts[1] if len(concept.diagnostic_prompts) > 1 else f"How would you explain {concept.label} more precisely now?"
    return f"Let's focus on {concept.label} for a second. {secondary}"


def next_hint(packet: TopicPacket, concept_id: str, hint_index: int) -> str:
    concept = get_concept(packet, concept_id)
    ladder = concept.hint_reframe_ladder
    if not ladder:
        return f"Try again by contrasting {concept.label} with a related concept."
    if hint_index >= len(ladder):
        return ladder[-1]
    return ladder[hint_index]


def make_session_state(packet: TopicPacket) -> SessionState:
    return SessionState(
        session_key=uuid.uuid4().hex[:12],
        topic_slug=packet.topic_slug,
        topic_title=packet.title,
        grounding_label=packet.grounding_label,
    )


def add_turn(
    state: SessionState,
    *,
    role: str,
    content: str,
    phase: str,
    target_concept_ids: list[str] | None = None,
    hints_used: int = 0,
    grounding_reference: str | None = None,
) -> SessionTurn:
    turn = SessionTurn(
        turn_index=len(state.turns),
        role=role,  # type: ignore[arg-type]
        phase=phase,
        target_concept_ids=target_concept_ids or [],
        content=content,
        hints_used=hints_used,
        grounding_reference=grounding_reference,
    )
    state.turns.append(turn)
    return turn


def save_transcript_json(state: SessionState, output_dir: str | Path = "content/transcripts") -> Path:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    transcript_path = output_path / f"{state.session_key}.json"
    transcript_path.write_text(state.model_dump_json(indent=2), encoding="utf-8")
    return transcript_path


def create_db_session(state: SessionState, settings: Settings | None = None) -> int | None:
    resolved_settings = settings or Settings()
    pool = get_pool(resolved_settings)
    with pool.acquire() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT ID FROM TOPICS WHERE SLUG = :slug", slug=state.topic_slug)
            topic_row = cursor.fetchone()
            if topic_row is None:
                return None
            topic_id = int(topic_row[0])

            cursor.execute(
                "SELECT ID FROM RESEARCH_REPORTS WHERE TOPIC_ID = :topic_id ORDER BY VERSION_NUMBER DESC FETCH FIRST 1 ROWS ONLY",
                topic_id=topic_id,
            )
            report_row = cursor.fetchone()
            report_id = int(report_row[0]) if report_row else None

            session_id_var = cursor.var(oracledb.NUMBER)
            cursor.execute(
                """
                INSERT INTO XP_SESSIONS (
                    SESSION_KEY,
                    TOPIC_ID,
                    REPORT_ID,
                    STATUS,
                    GROUNDING_LABEL
                ) VALUES (
                    :session_key,
                    :topic_id,
                    :report_id,
                    :status,
                    :grounding_label
                ) RETURNING ID INTO :session_id
                """,
                session_key=state.session_key,
                topic_id=topic_id,
                report_id=report_id,
                status=state.status,
                grounding_label=state.grounding_label,
                session_id=session_id_var,
            )
        connection.commit()
        state.session_id = int(session_id_var.getvalue()[0])
        return state.session_id


def persist_turn(state: SessionState, turn: SessionTurn, settings: Settings | None = None) -> None:
    if state.session_id is None:
        return
    resolved_settings = settings or Settings()
    pool = get_pool(resolved_settings)
    with pool.acquire() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO XP_TURNS (
                    SESSION_ID,
                    TURN_INDEX,
                    ROLE,
                    PHASE,
                    TARGET_CONCEPT_SLUGS,
                    CONTENT,
                    HINTS_USED,
                    GROUNDING_REFERENCE
                ) VALUES (
                    :session_id,
                    :turn_index,
                    :role,
                    :phase,
                    :target_concept_slugs,
                    :content,
                    :hints_used,
                    :grounding_reference
                )
                """,
                session_id=state.session_id,
                turn_index=turn.turn_index,
                role=turn.role,
                phase=turn.phase,
                target_concept_slugs=json.dumps(turn.target_concept_ids),
                content=turn.content,
                hints_used=turn.hints_used,
                grounding_reference=turn.grounding_reference,
            )
        connection.commit()


def finalize_session(state: SessionState, status: str, settings: Settings | None = None) -> None:
    if state.session_id is None:
        return
    resolved_settings = settings or Settings()
    pool = get_pool(resolved_settings)
    with pool.acquire() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE XP_SESSIONS SET STATUS = :status, FINISHED_AT = CURRENT_TIMESTAMP WHERE ID = :session_id",
                status=status,
                session_id=state.session_id,
            )
        connection.commit()
    state.status = status
