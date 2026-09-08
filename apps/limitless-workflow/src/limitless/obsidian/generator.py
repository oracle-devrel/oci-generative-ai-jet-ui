from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from limitless.db.pool import get_pool
from limitless.graph.models import TopicPacket
from limitless.obsidian.base import build_concept_tracker_base
from limitless.obsidian.canvas import build_canvas_edges, build_canvas_nodes, build_knowledge_map_canvas
from limitless.obsidian.theme import build_css_snippet
from limitless.research.packet_loader import load_topic_packet
from limitless.settings import Settings


@dataclass(slots=True)
class ConceptView:
    topic: str
    topic_title: str
    slug: str
    label: str
    summary: str
    primary_topic_slug: str
    related_topics: list[str]
    score: float = 0.0
    band: str | None = None
    delta: float = 0.0
    trend: str = "flat"
    last_reviewed: str | None = None
    next_step: str | None = None
    evidence_snippet: str | None = None
    confusion_note: str | None = None

    @property
    def display_band(self) -> str:
        return self.band or "Unassessed"


@dataclass(slots=True)
class TopicView:
    slug: str
    title: str
    score: float
    band: str
    weakest: ConceptView | None
    strongest: ConceptView | None
    concepts: list[ConceptView]


def _read_lob(value: Any) -> Any:
    if hasattr(value, "read"):
        return value.read()
    return value


def _parse_related_topics(raw: str | None) -> list[str]:
    raw = _read_lob(raw)
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return []
    return [str(value) for value in data]


def _format_date(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    return str(value)


def _fetch_concepts(settings: Settings) -> list[ConceptView]:
    pool = get_pool(settings)
    with pool.acquire() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                WITH latest_assessments AS (
                    SELECT x.*
                    FROM (
                        SELECT ca.*, ROW_NUMBER() OVER (PARTITION BY ca.CONCEPT_ID ORDER BY ca.ID DESC) rn
                        FROM CONCEPT_ASSESSMENTS ca
                    ) x
                    WHERE x.rn = 1
                ), latest_evidence AS (
                    SELECT x.*
                    FROM (
                        SELECT ce.*, ROW_NUMBER() OVER (PARTITION BY ce.CONCEPT_ID ORDER BY ce.ID DESC) rn
                        FROM CONCEPT_EVIDENCE ce
                    ) x
                    WHERE x.rn = 1
                )
                SELECT
                    t.SLUG AS TOPIC_SLUG,
                    t.TITLE AS TOPIC_TITLE,
                    c.SLUG AS CONCEPT_SLUG,
                    c.LABEL,
                    c.SUMMARY,
                    c.PRIMARY_TOPIC_SLUG,
                    c.RELATED_TOPICS_JSON,
                    la.SCORE_AFTER,
                    la.BAND_AFTER,
                    la.DELTA,
                    la.TREND,
                    la.CREATED_AT,
                    la.NEXT_STEP,
                    le.EVIDENCE_SNIPPET,
                    le.CONFUSION_NOTE
                FROM CONCEPTS c
                JOIN TOPICS t ON t.ID = c.TOPIC_ID
                LEFT JOIN latest_assessments la ON la.CONCEPT_ID = c.ID
                LEFT JOIN latest_evidence le ON le.CONCEPT_ID = c.ID
                ORDER BY t.SLUG, c.LABEL
                """
            )
            concepts: list[ConceptView] = []
            for row in cursor.fetchall():
                concepts.append(
                    ConceptView(
                        topic=row[0],
                        topic_title=row[1],
                        slug=row[2],
                        label=row[3],
                        summary=_read_lob(row[4]) or "",
                        primary_topic_slug=row[5],
                        related_topics=_parse_related_topics(row[6]),
                        score=float(row[7]) if row[7] is not None else 0.0,
                        band=row[8],
                        delta=float(row[9]) if row[9] is not None else 0.0,
                        trend=row[10] or "flat",
                        last_reviewed=_format_date(row[11]),
                        next_step=_read_lob(row[12]),
                        evidence_snippet=_read_lob(row[13]),
                        confusion_note=_read_lob(row[14]),
                    )
                )
            return concepts


def _topic_band(score: float, concepts: list[ConceptView]) -> str:
    if not any(concept.band for concept in concepts):
        return "Unassessed"
    if score < 25:
        return "Fragile"
    if score < 70:
        return "Developing"
    if score < 85:
        return "Solid"
    return "Strong"


def _build_topic_views(concepts: list[ConceptView]) -> list[TopicView]:
    grouped: dict[str, list[ConceptView]] = {}
    titles: dict[str, str] = {}
    for concept in concepts:
        grouped.setdefault(concept.topic, []).append(concept)
        titles[concept.topic] = concept.topic_title

    topic_views: list[TopicView] = []
    for slug, topic_concepts in grouped.items():
        score = round(sum(concept.score for concept in topic_concepts) / max(1, len(topic_concepts)), 2)
        weakest = min(topic_concepts, key=lambda concept: concept.score, default=None)
        strongest = max(topic_concepts, key=lambda concept: concept.score, default=None)
        topic_views.append(
            TopicView(
                slug=slug,
                title=titles[slug],
                score=score,
                band=_topic_band(score, topic_concepts),
                weakest=weakest,
                strongest=strongest,
                concepts=topic_concepts,
            )
        )
    topic_views.sort(key=lambda topic: (0 if topic.slug == "agent-memory" else 1, topic.slug))
    return topic_views


def _trend_class(trend: str) -> str:
    return {
        "up": "trend-up",
        "down": "trend-down",
    }.get(trend, "trend-flat")


def build_dashboard(
    *,
    topic_views: list[TopicView],
    strongest: list[ConceptView],
    weakest: list[ConceptView],
    recent_session_summary: str,
    next_review_targets: list[ConceptView],
) -> str:
    hero = next(topic for topic in topic_views if topic.slug == "agent-memory")
    secondary = next((topic for topic in topic_views if topic.slug == "agent-loop"), None)

    def render_concept_list(items: list[ConceptView]) -> str:
        if not items:
            return "<p class='muted'>No assessed concepts yet.</p>"
        rows = []
        for item in items:
            rows.append(
                f"<li><strong>[[{item.label}]]</strong> <span class='band band-{item.display_band}'>{item.display_band}</span> "
                f"<span class='{_trend_class(item.trend)}'>{'▲' if item.trend == 'up' else '▼' if item.trend == 'down' else '→'} {item.delta:+.0f}</span></li>"
            )
        return "<ul class='link-list'>" + "".join(rows) + "</ul>"

    secondary_html = ""
    if secondary is not None:
        secondary_html = f"""
<div class="vault-panel">
  <div class="eyebrow">Secondary topic</div>
  <div class="metric">[[Agent Loop]]</div>
  <p><span class="band band-{secondary.band}">{secondary.band}</span> score {secondary.score:.0f}</p>
  <p class="muted">Weakest: [[{secondary.weakest.label}]]</p>
</div>
"""

    return f"""---
cssclasses:
  - cognitive-vault
  - dashboard
---
# Limitless Command Center

<div class="vault-strip">
  <div class="eyebrow">Active topic</div>
  <div class="metric">{hero.title}</div>
  <p><span class="band band-{hero.band}">{hero.band}</span> score {hero.score:.0f}</p>
  <p>Weakest concept: [[{hero.weakest.label if hero.weakest else 'Unassessed'}]]</p>
  <p>Next review: {hero.weakest.next_step if hero.weakest and hero.weakest.next_step else 'Run XP Builder again on the weakest concept.'}</p>
</div>

<div class="vault-grid two">
  <div class="vault-panel hero">
    <div class="eyebrow">Hero topic</div>
    <div class="metric">[[Agent Memory]]</div>
    <p><span class="band band-{hero.band}">{hero.band}</span> score {hero.score:.0f}</p>
    <p class="muted">Strongest: [[{hero.strongest.label if hero.strongest else 'Unassessed'}]]</p>
  </div>
  {secondary_html}
</div>

<div class="vault-grid three">
  <div class="vault-panel">
    <div class="eyebrow">Weakest concepts</div>
    {render_concept_list(weakest)}
  </div>
  <div class="vault-panel">
    <div class="eyebrow">Strongest concepts</div>
    {render_concept_list(strongest)}
  </div>
  <div class="vault-panel">
    <div class="eyebrow">Next review targets</div>
    {render_concept_list(next_review_targets)}
  </div>
</div>

<div class="vault-panel">
  <div class="eyebrow">Recent session</div>
  <p class="session-snippet">{recent_session_summary}</p>
</div>

## Concepts Base

![[Atlas/Concept Tracker.base#Agent Memory]]

## Systemwide Weak Points

![[Atlas/Concept Tracker.base#Weakest Systemwide]]
"""


def build_topic_note(
    *,
    title: str,
    score: float,
    weakest: str,
    next_review: str,
    bridges: list[str],
    triad: list[ConceptView] | None = None,
    recent_updates: list[ConceptView] | None = None,
    grounding_label: str | None = None,
    source_report_path: str | None = None,
) -> str:
    triad = triad or []
    recent_updates = recent_updates or []

    triad_cards = []
    for concept in triad:
        triad_cards.append(
            f"<div class='concept-card'><div class='eyebrow'>{concept.label}</div>"
            f"<p><span class='band band-{concept.display_band}'>{concept.display_band}</span> score {concept.score:.0f}</p>"
            f"<p class='{_trend_class(concept.trend)}'>{'▲' if concept.trend == 'up' else '▼' if concept.trend == 'down' else '→'} {concept.delta:+.0f}</p>"
            f"<p class='muted'>Last reviewed: {concept.last_reviewed or 'Not yet assessed'}</p></div>"
        )
    updates_html = "".join(
        f"<li><strong>[[{concept.label}]]</strong> — {concept.evidence_snippet or 'No evidence yet.'}</li>"
        for concept in recent_updates
    ) or "<p class='muted'>No recent debrief updates yet.</p>"
    bridge_html = "".join(f"<li>{bridge}</li>" for bridge in bridges)
    return f"""---
cssclasses:
  - cognitive-vault
  - topic-note
---
# {title}

<div class="vault-panel">
  <div class="eyebrow">Weak point / next review</div>
  <p><span class="band">Current score</span> {score:.0f}</p>
  <p><strong>Weak point:</strong> [[{weakest}]]</p>
  <p><strong>Next review:</strong> {next_review}</p>
</div>

<div class="vault-grid three">
  {''.join(triad_cards)}
</div>

<div class="vault-panel">
  <div class="eyebrow">Recent session evidence summary</div>
  <ul class="link-list">{updates_html}</ul>
</div>

<div class="vault-panel">
  <div class="eyebrow">Cross-topic bridges</div>
  <ul class="link-list">{bridge_html}</ul>
</div>

<div class="vault-panel">
  <div class="eyebrow">Research grounding</div>
  <p><strong>Grounding label:</strong> {grounding_label or 'Reviewed concept packet'}</p>
  <p><strong>Source report:</strong> `{source_report_path or 'unknown'}`</p>
</div>

## Views

![[Atlas/Concept Tracker.base#Agent Memory]]
"""


def _frontmatter_lines(data: dict[str, Any]) -> list[str]:
    lines = ["---"]
    for key, value in data.items():
        if isinstance(value, list):
            lines.append(f"{key}:")
            for item in value:
                lines.append(f"  - {item}")
        else:
            lines.append(f"{key}: {value}")
    lines.append("---")
    return lines


def build_concept_note(concept: ConceptView, related_links: list[str]) -> str:
    frontmatter = _frontmatter_lines(
        {
            "topic": concept.topic,
            "score": int(round(concept.score)),
            "band": concept.display_band,
            "delta": int(round(concept.delta)),
            "trend": concept.trend,
            "last_reviewed": concept.last_reviewed or "",
            "related_topics": concept.related_topics,
            "tags": [f"topic/{concept.topic}", "type/concept"],
            "cssclasses": ["cognitive-vault", "concept-note"],
        }
    )
    related_body = "\n".join(f"- {link}" for link in related_links) if related_links else "- None yet"
    return "\n".join(
        frontmatter
        + [
            f"# {concept.label}",
            "",
            "## Status",
            f"- Band: **{concept.display_band}**",
            f"- Score: **{concept.score:.0f}**",
            f"- Delta: **{concept.delta:+.0f}**",
            f"- Trend: **{concept.trend}**",
            f"- Last reviewed: **{concept.last_reviewed or 'Not yet assessed'}**",
            "",
            "## Summary",
            concept.summary or "No summary yet.",
            "",
            "## Recent evidence",
            concept.evidence_snippet or "No direct learner evidence captured yet.",
            "",
            "## Related concepts",
            related_body,
            "",
            "## Next retrieval prompt",
            concept.next_step or f"Explain {concept.label} again in your own words.",
        ]
    )


def build_session_note(topic_title: str, session_key: str, updates: list[ConceptView]) -> str:
    rows = "\n".join(
        f"- **[[{concept.label}]]** — {concept.evidence_snippet or 'No evidence.'}" for concept in updates
    ) or "- No assessed concepts recorded."
    return f"""---
cssclasses:
  - cognitive-vault
  - session-note
---
# Session {session_key}

## Topic
- [[{topic_title}]]

## Evidence
{rows}
"""


def _load_packets() -> dict[str, TopicPacket]:
    packet_dir = Path("content/concept_packets")
    packets: dict[str, TopicPacket] = {}
    for review_json in packet_dir.glob("*.reviewed.json"):
        review_md = review_json.with_name(review_json.name.replace(".reviewed.json", ".review.md"))
        packet = load_topic_packet(review_json, review_md)
        packets[packet.topic_slug] = packet
    return packets


def refresh_obsidian_projection(settings: Settings | None = None) -> list[Path]:
    resolved_settings = settings or Settings()
    vault = resolved_settings.obsidian_vault_path
    packets = _load_packets()
    concepts = [concept for concept in _fetch_concepts(resolved_settings) if concept.topic in packets]
    topic_views = _build_topic_views(concepts)
    topic_lookup = {topic.slug: topic for topic in topic_views}
    concept_lookup = {concept.slug: concept for concept in concepts}

    assessed_concepts = [concept for concept in concepts if concept.band is not None]
    active_topic_concepts = [concept for concept in concepts if concept.topic == 'agent-memory']
    strongest_pool = assessed_concepts or active_topic_concepts or concepts
    weakest_pool = assessed_concepts or active_topic_concepts or concepts
    strongest = sorted(strongest_pool, key=lambda concept: concept.score, reverse=True)[:3]
    weakest = sorted(weakest_pool, key=lambda concept: concept.score)[:3]
    next_review_targets = [concept for concept in weakest if concept.next_step][:3] or weakest[:3]

    recent_session_summary = "Run XP Debrief to generate the first visible memory update."
    session_updates: dict[str, list[ConceptView]] = {topic.slug: [] for topic in topic_views}

    pool = get_pool(resolved_settings)
    with pool.acquire() as connection:
        with connection.cursor() as cursor:
            allowed_topics_sql = ", ".join(f"'{topic_slug}'" for topic_slug in sorted(packets))
            cursor.execute(
                f"""
                SELECT SESSION_KEY, TITLE, SLUG
                FROM (
                    SELECT x.SESSION_KEY, t.TITLE, t.SLUG, x.ID
                    FROM (
                        SELECT s.*, ROW_NUMBER() OVER (PARTITION BY s.TOPIC_ID ORDER BY s.ID DESC) rn
                        FROM XP_SESSIONS s
                    ) x
                    JOIN TOPICS t ON t.ID = x.TOPIC_ID
                    WHERE x.rn = 1 AND t.SLUG IN ({allowed_topics_sql})
                    ORDER BY x.ID DESC
                )
                FETCH FIRST 1 ROWS ONLY
                """
            )
            row = cursor.fetchone()
            if row:
                recent_session_summary = f"Latest session: {row[0]} for {row[1]}."

            cursor.execute(
                """
                WITH latest_assessment AS (
                    SELECT x.* FROM (
                        SELECT ca.*, ROW_NUMBER() OVER (PARTITION BY ca.CONCEPT_ID ORDER BY ca.ID DESC) rn
                        FROM CONCEPT_ASSESSMENTS ca
                    ) x WHERE x.rn = 1
                )
                SELECT t.SLUG, c.SLUG
                FROM latest_assessment la
                JOIN CONCEPTS c ON c.ID = la.CONCEPT_ID
                JOIN TOPICS t ON t.ID = c.TOPIC_ID
                ORDER BY la.ID DESC
                """
            )
            for topic_slug, concept_slug in cursor.fetchall():
                if topic_slug not in topic_lookup:
                    continue
                if concept_slug in concept_lookup:
                    session_updates.setdefault(topic_slug, [])
                    if concept_lookup[concept_slug] not in session_updates[topic_slug]:
                        session_updates[topic_slug].append(concept_lookup[concept_slug])

    paths_to_write = [
        vault / "10 Topics",
        vault / "20 Concepts",
        vault / "30 Sessions",
        vault / "40 Frameworks",
        vault / "Atlas",
        vault / ".obsidian" / "snippets",
    ]
    for path in paths_to_write:
        path.mkdir(parents=True, exist_ok=True)

    for generated_dir in [vault / '10 Topics', vault / '20 Concepts', vault / '30 Sessions']:
        for existing in generated_dir.glob('*.md'):
            if existing.name != '.gitkeep':
                existing.unlink(missing_ok=True)

    written: list[Path] = []

    dashboard_path = vault / "00 Dashboard.md"
    dashboard_path.write_text(
        build_dashboard(
            topic_views=topic_views,
            strongest=strongest,
            weakest=weakest,
            recent_session_summary=recent_session_summary,
            next_review_targets=next_review_targets,
        ),
        encoding="utf-8",
    )
    written.append(dashboard_path)

    for topic_slug, topic in topic_lookup.items():
        packet = packets.get(topic_slug)
        packet_bridges = []
        if packet:
            for edge in packet.edges:
                if edge.kind == "bridge":
                    source = concept_lookup.get(edge.source)
                    target = concept_lookup.get(edge.target)
                    if source and target:
                        packet_bridges.append(f"[[{source.label}]] ↔ [[{target.label}]]")
                    else:
                        packet_bridges.append(f"{edge.source} ↔ {edge.target}")
        topic_path = vault / "10 Topics" / f"{topic.title}.md"
        topic_path.write_text(
            build_topic_note(
                title=topic.title,
                score=topic.score,
                weakest=topic.weakest.label if topic.weakest else "Unassessed",
                next_review=topic.weakest.next_step if topic.weakest and topic.weakest.next_step else "Run XP Builder on the weakest concept.",
                bridges=packet_bridges,
                triad=topic.concepts,
                recent_updates=session_updates.get(topic_slug, [])[:3],
                grounding_label=packet.grounding_label if packet else None,
                source_report_path=packet.source_report_path if packet else None,
            ),
            encoding="utf-8",
        )
        written.append(topic_path)

    for concept in concepts:
        packet = packets.get(concept.topic)
        related_links = []
        if packet:
            packet_concept = next((item for item in packet.concepts if item.id == concept.slug), None)
            if packet_concept:
                for related_slug in packet_concept.related_concepts:
                    related = concept_lookup.get(related_slug)
                    related_links.append(f"[[{related.label}]]" if related else related_slug)
        concept_path = vault / "20 Concepts" / f"{concept.label}.md"
        concept_path.write_text(build_concept_note(concept, related_links), encoding="utf-8")
        written.append(concept_path)

    for topic_slug, updates in session_updates.items():
        if not updates:
            continue
        topic_title = topic_lookup[topic_slug].title
        session_path = vault / "30 Sessions" / f"Latest {topic_title} Session.md"
        session_path.write_text(build_session_note(topic_title, topic_slug, updates[:5]), encoding="utf-8")
        written.append(session_path)

    base_path = vault / "Atlas" / "Concept Tracker.base"
    base_path.write_text(build_concept_tracker_base(), encoding="utf-8")
    written.append(base_path)

    main_concepts = [concept.label for concept in topic_lookup.get("agent-memory", TopicView("", "", 0, "Unassessed", None, None, [])).concepts]
    secondary_concepts = [concept.label for concept in topic_lookup.get("agent-loop", TopicView("", "", 0, "Unassessed", None, None, [])).concepts]
    nodes = build_canvas_nodes("Agent Memory", main_concepts, secondary_topic="Agent Loop", secondary_concepts=secondary_concepts)
    edges = build_canvas_edges(nodes)
    canvas_path = vault / "Atlas" / "Knowledge Map.canvas"
    canvas_path.write_text(build_knowledge_map_canvas(nodes, edges), encoding="utf-8")
    written.append(canvas_path)

    css_path = vault / ".obsidian" / "snippets" / "limitless-cognitive-vault.css"
    css_path.write_text(build_css_snippet(), encoding="utf-8")
    written.append(css_path)

    return written
