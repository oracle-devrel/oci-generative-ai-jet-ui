from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from limitless.db.pool import get_pool
from limitless.debrief.models import ConceptDebrief, DebriefResult
from limitless.debrief.scorer import apply_mastery_band, score_concept_update, trend_from_delta
from limitless.settings import Settings
from limitless.xp.models import SessionState, SessionTurn

CONFUSION_MARKERS = (
    "i don't know",
    "i dont know",
    "not sure",
    "unsure",
    "confused",
    "confuse",
    "don't remember",
    "do not remember",
)


def load_transcript(transcript_path: str | Path) -> SessionState:
    path = Path(transcript_path)
    return SessionState.model_validate_json(path.read_text(encoding="utf-8"))


def _has_learner_evidence(state: SessionState) -> bool:
    return any(turn.role == "user" for turn in state.turns)


def find_latest_transcript(
    topic_slug: str,
    transcripts_dir: str | Path = "content/transcripts",
    settings: Settings | None = None,
) -> Path:
    transcript_root = Path(transcripts_dir)
    resolved_settings = settings or Settings()

    try:
        pool = get_pool(resolved_settings)
        with pool.acquire() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    select s.session_key
                    from xp_sessions s
                    join topics t on t.id = s.topic_id
                    where t.slug = :slug
                    order by s.id desc
                    """,
                    slug=topic_slug,
                )
                for (session_key,) in cursor.fetchall():
                    candidate = transcript_root / f"{session_key}.json"
                    if not candidate.exists():
                        continue
                    try:
                        state = load_transcript(candidate)
                    except Exception:
                        continue
                    if state.topic_slug == topic_slug and _has_learner_evidence(state):
                        return candidate
    except Exception:
        pass

    candidates: list[tuple[float, Path]] = []
    for transcript_path in transcript_root.glob("*.json"):
        try:
            state = load_transcript(transcript_path)
        except Exception:
            continue
        if state.topic_slug == topic_slug and _has_learner_evidence(state):
            candidates.append((transcript_path.stat().st_mtime, transcript_path))

    if not candidates:
        raise FileNotFoundError(f"No transcript with learner evidence found for topic '{topic_slug}'")

    candidates.sort(key=lambda item: item[0], reverse=True)
    return candidates[0][1]


def summarize_concept_update(
    *,
    concept_label: str,
    score_before: float,
    score_after: float,
    band_after: str,
    evidence_snippet: str,
    next_step: str,
) -> str:
    return (
        f"{concept_label}: {score_before:.0f} -> {score_after:.0f} ({band_after})\n"
        f"Evidence: {evidence_snippet}\n"
        f"Next: {next_step}"
    )


def _is_confusion(text: str) -> bool:
    lowered = text.lower()
    return any(marker in lowered for marker in CONFUSION_MARKERS)


def _iter_user_turns_for_concept(turns: Iterable[SessionTurn], concept_slug: str) -> list[SessionTurn]:
    return [
        turn
        for turn in turns
        if turn.role == "user" and concept_slug in turn.target_concept_ids
    ]


def _iter_hint_turns_for_concept(turns: Iterable[SessionTurn], concept_slug: str) -> list[SessionTurn]:
    return [
        turn
        for turn in turns
        if turn.role == "assistant"
        and concept_slug in turn.target_concept_ids
        and turn.content.startswith("Hint:")
    ]


def _best_evidence_snippet(user_turns: list[SessionTurn]) -> str:
    if not user_turns:
        return "No direct learner evidence captured."
    best_turn = max(user_turns, key=lambda turn: len(turn.content.strip()))
    snippet = best_turn.content.strip().replace("\n", " ")
    return snippet[:220]


def _next_step(concept_label: str, hint_used: bool, confusion_note: str | None) -> str:
    if confusion_note:
        return f"Revisit {concept_label} and contrast it explicitly against the concept it was confused with."
    if hint_used:
        return f"Retry {concept_label} next session without hints and explain it in your own words."
    return f"Strengthen {concept_label} with one more retrieval pass and a concrete example."


def _lookup_concepts(state: SessionState, settings: Settings) -> dict[str, tuple[int, str]]:
    pool = get_pool(settings)
    with pool.acquire() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT c.ID, c.SLUG, c.LABEL
                FROM CONCEPTS c
                JOIN TOPICS t ON t.ID = c.TOPIC_ID
                WHERE t.SLUG = :topic_slug
                """,
                topic_slug=state.topic_slug,
            )
            return {row[1]: (int(row[0]), row[2]) for row in cursor.fetchall()}


def _lookup_previous_assessment(concept_id: int, settings: Settings) -> tuple[float, str | None]:
    pool = get_pool(settings)
    with pool.acquire() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT SCORE_AFTER, BAND_AFTER
                FROM CONCEPT_ASSESSMENTS
                WHERE CONCEPT_ID = :concept_id
                ORDER BY ID DESC
                FETCH FIRST 1 ROWS ONLY
                """,
                concept_id=concept_id,
            )
            row = cursor.fetchone()
            if row is None:
                return 0.0, None
            return float(row[0]), row[1]


def analyze_transcript(state: SessionState, settings: Settings | None = None) -> DebriefResult:
    resolved_settings = settings or Settings()
    concept_lookup = _lookup_concepts(state, resolved_settings)

    target_concepts = []
    seen: set[str] = set()
    for turn in state.turns:
        if turn.role != "user":
            continue
        for concept_slug in turn.target_concept_ids:
            if concept_slug in concept_lookup and concept_slug not in seen:
                seen.add(concept_slug)
                target_concepts.append(concept_slug)

    updates: list[ConceptDebrief] = []
    for concept_slug in target_concepts:
        concept_id, concept_label = concept_lookup[concept_slug]
        user_turns = _iter_user_turns_for_concept(state.turns, concept_slug)
        hint_turns = _iter_hint_turns_for_concept(state.turns, concept_slug)
        evidence_snippet = _best_evidence_snippet(user_turns)
        confusion_note = evidence_snippet if _is_confusion(evidence_snippet) else None
        explanation_length = max((len(turn.content.strip()) for turn in user_turns), default=0)
        score_before, band_before = _lookup_previous_assessment(concept_id, resolved_settings)
        delta, score_after = score_concept_update(
            score_before=score_before,
            explanation_length=explanation_length,
            user_turn_count=len(user_turns),
            hints_used_count=len(hint_turns),
            confusion_detected=confusion_note is not None,
        )
        band_after = apply_mastery_band(score_after)
        updates.append(
            ConceptDebrief(
                concept_slug=concept_slug,
                concept_label=concept_label,
                concept_id=concept_id,
                score_before=score_before,
                score_after=score_after,
                band_before=band_before,
                band_after=band_after,
                delta=delta,
                trend=trend_from_delta(delta),
                evidence_snippet=evidence_snippet,
                hint_used=bool(hint_turns),
                hints_used_count=len(hint_turns),
                confusion_note=confusion_note,
                next_step=_next_step(concept_label, bool(hint_turns), confusion_note),
            )
        )

    return DebriefResult(
        topic_slug=state.topic_slug,
        topic_title=state.topic_title,
        session_key=state.session_key,
        session_id=state.session_id,
        concept_updates=updates,
    )


def persist_debrief_result(result: DebriefResult, settings: Settings | None = None) -> None:
    if result.session_id is None:
        return

    resolved_settings = settings or Settings()
    pool = get_pool(resolved_settings)
    with pool.acquire() as connection:
        with connection.cursor() as cursor:
            for update in result.concept_updates:
                assessment_id_var = cursor.var(int)
                cursor.execute(
                    """
                    INSERT INTO CONCEPT_ASSESSMENTS (
                        SESSION_ID,
                        CONCEPT_ID,
                        SCORE_BEFORE,
                        SCORE_AFTER,
                        BAND_BEFORE,
                        BAND_AFTER,
                        DELTA,
                        TREND,
                        NEXT_STEP
                    ) VALUES (
                        :session_id,
                        :concept_id,
                        :score_before,
                        :score_after,
                        :band_before,
                        :band_after,
                        :delta,
                        :trend,
                        :next_step
                    ) RETURNING ID INTO :assessment_id
                    """,
                    session_id=result.session_id,
                    concept_id=update.concept_id,
                    score_before=update.score_before,
                    score_after=update.score_after,
                    band_before=update.band_before,
                    band_after=update.band_after,
                    delta=update.delta,
                    trend=update.trend,
                    next_step=update.next_step,
                    assessment_id=assessment_id_var,
                )
                assessment_id = int(assessment_id_var.getvalue()[0])
                cursor.execute(
                    """
                    INSERT INTO CONCEPT_EVIDENCE (
                        ASSESSMENT_ID,
                        CONCEPT_ID,
                        EVIDENCE_KIND,
                        EVIDENCE_SNIPPET,
                        HINT_USED,
                        CONFUSION_NOTE
                    ) VALUES (
                        :assessment_id,
                        :concept_id,
                        :evidence_kind,
                        :evidence_snippet,
                        :hint_used,
                        :confusion_note
                    )
                    """,
                    assessment_id=assessment_id,
                    concept_id=update.concept_id,
                    evidence_kind="transcript-summary",
                    evidence_snippet=update.evidence_snippet,
                    hint_used=1 if update.hint_used else 0,
                    confusion_note=update.confusion_note,
                )
            cursor.execute(
                "UPDATE XP_SESSIONS SET STATUS = :status WHERE ID = :session_id",
                status="debriefed",
                session_id=result.session_id,
            )
        connection.commit()


def build_cli_summary(result: DebriefResult) -> str:
    lines = [f"XP Debrief Summary - {result.topic_title}"]
    for update in result.concept_updates:
        lines.append(
            summarize_concept_update(
                concept_label=update.concept_label,
                score_before=update.score_before,
                score_after=update.score_after,
                band_after=update.band_after,
                evidence_snippet=update.evidence_snippet,
                next_step=update.next_step,
            )
        )
    return "\n\n".join(lines)


def run_debrief(
    *,
    topic_slug: str,
    transcript_path: str | Path | None = None,
    latest: bool = False,
    settings: Settings | None = None,
) -> DebriefResult:
    resolved_settings = settings or Settings()

    if transcript_path is None:
        if not latest:
            raise ValueError("Provide transcript_path or set latest=True")
        transcript_path = find_latest_transcript(topic_slug, settings=resolved_settings)

    state = load_transcript(transcript_path)
    result = analyze_transcript(state, resolved_settings)
    if not result.concept_updates:
        raise ValueError(
            f"Transcript '{transcript_path}' contains no learner evidence for debrief. "
            "Run a real XP session with user answers before debriefing."
        )
    persist_debrief_result(result, resolved_settings)
    return result
