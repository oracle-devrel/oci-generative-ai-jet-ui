from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from limitless.db.pool import get_pool
from limitless.settings import Settings


@dataclass(slots=True)
class FrameworkConcept:
    label: str
    band: str | None
    score: float
    evidence_snippet: str | None
    next_step: str | None


def build_framework_outline(
    *,
    topic_title: str,
    strong_concepts: list[str],
    weak_concepts: list[str],
) -> str:
    sections = "\n".join(f"## {concept}\n- Explain how {concept} supports the overall topic." for concept in strong_concepts)
    weak_lines = "\n".join(f"- {concept}" for concept in weak_concepts) or "- No major gaps identified yet."
    return f"# {topic_title} Framework\n\n## Thesis\nA first-pass framework grounded in demonstrated understanding rather than generic generation.\n\n{sections}\n\n## Open questions / gaps\n{weak_lines}\n"


def _fetch_topic_concepts(topic_slug: str, settings: Settings) -> tuple[str, list[FrameworkConcept]]:
    pool = get_pool(settings)
    with pool.acquire() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                WITH latest_assessment AS (
                    SELECT x.* FROM (
                        SELECT ca.*, ROW_NUMBER() OVER (PARTITION BY ca.CONCEPT_ID ORDER BY ca.ID DESC) rn
                        FROM CONCEPT_ASSESSMENTS ca
                    ) x WHERE x.rn = 1
                ), latest_evidence AS (
                    SELECT x.* FROM (
                        SELECT ce.*, ROW_NUMBER() OVER (PARTITION BY ce.CONCEPT_ID ORDER BY ce.ID DESC) rn
                        FROM CONCEPT_EVIDENCE ce
                    ) x WHERE x.rn = 1
                )
                SELECT t.TITLE, c.LABEL, la.BAND_AFTER, la.SCORE_AFTER, le.EVIDENCE_SNIPPET, la.NEXT_STEP
                FROM CONCEPTS c
                JOIN TOPICS t ON t.ID = c.TOPIC_ID
                LEFT JOIN latest_assessment la ON la.CONCEPT_ID = c.ID
                LEFT JOIN latest_evidence le ON le.CONCEPT_ID = c.ID
                WHERE t.SLUG = :topic_slug
                ORDER BY c.LABEL
                """,
                topic_slug=topic_slug,
            )
            rows = cursor.fetchall()

    if not rows:
        raise ValueError(f"No concepts found for topic '{topic_slug}'")

    topic_title = rows[0][0]
    concepts = [
        FrameworkConcept(
            label=row[1],
            band=row[2],
            score=float(row[3]) if row[3] is not None else 0.0,
            evidence_snippet=row[4].read() if hasattr(row[4], 'read') else row[4],
            next_step=row[5].read() if hasattr(row[5], 'read') else row[5],
        )
        for row in rows
    ]
    return topic_title, concepts


def select_framework_concepts(concepts: list[FrameworkConcept]) -> tuple[list[FrameworkConcept], list[FrameworkConcept]]:
    stronger = [concept for concept in concepts if concept.band in {"Developing", "Solid", "Strong"}]
    weaker = [concept for concept in concepts if concept.band in {None, "Fragile"}]
    return stronger, weaker


def render_framework_note(topic_title: str, stronger: list[FrameworkConcept], weaker: list[FrameworkConcept]) -> str:
    sections: list[str] = [
        "---",
        "cssclasses:",
        "  - cognitive-vault",
        "  - framework-note",
        "---",
        f"# {topic_title} Framework",
        "",
        "## Thesis",
        "A first-pass framework grounded in demonstrated understanding rather than generic generation.",
        "",
    ]

    if stronger:
        for concept in stronger:
            sections.extend(
                [
                    f"## {concept.label}",
                    f"- Current mastery: **{concept.band}** ({concept.score:.0f})",
                    f"- Evidence: {concept.evidence_snippet or 'No direct evidence yet.'}",
                    f"- Use in framework: explain how {concept.label} contributes to the wider topic.",
                    "",
                ]
            )
    else:
        sections.extend(
            [
                "## Framework sections",
                "- No strong enough concepts yet. Run more XP sessions before using this as a presentation-quality framework.",
                "",
            ]
        )

    sections.append("## Open questions / gaps")
    if weaker:
        sections.extend([f"- {concept.label}: {concept.next_step or 'Needs another retrieval pass.'}" for concept in weaker])
    else:
        sections.append("- No major gaps identified yet.")
    sections.append("")
    return "\n".join(sections)


def build_framework_note_for_topic(topic_slug: str, settings: Settings | None = None) -> tuple[str, str]:
    resolved_settings = settings or Settings()
    topic_title, concepts = _fetch_topic_concepts(topic_slug, resolved_settings)
    stronger, weaker = select_framework_concepts(concepts)
    return topic_title, render_framework_note(topic_title, stronger, weaker)


def write_framework_note(
    topic_slug: str,
    output_dir: str | Path = "Limitless/40 Frameworks",
    settings: Settings | None = None,
) -> Path:
    topic_title, note = build_framework_note_for_topic(topic_slug, settings)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    note_path = output_path / f"{topic_title} Framework.md"
    note_path.write_text(note, encoding="utf-8")
    return note_path
