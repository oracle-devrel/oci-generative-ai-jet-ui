from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from limitless.db.pool import get_pool
from limitless.settings import Settings


def main(topic_slug: str = "agent-memory") -> int:
    settings = Settings()
    pool = get_pool(settings)
    with pool.acquire() as connection:
        with connection.cursor() as cursor:
            print(f"Learning state check for: {topic_slug}")
            print("--- latest sessions ---")
            cursor.execute(
                """
                select s.id, s.session_key, s.status, s.started_at, s.finished_at
                from xp_sessions s
                join topics t on t.id = s.topic_id
                where t.slug = :slug
                order by s.id desc
                fetch first 5 rows only
                """,
                slug=topic_slug,
            )
            for row in cursor.fetchall():
                print(row)

            print("--- latest assessments ---")
            cursor.execute(
                """
                select c.label, ca.score_before, ca.score_after, ca.band_after, ca.delta, ca.trend, ca.created_at
                from concept_assessments ca
                join concepts c on c.id = ca.concept_id
                join topics t on t.id = c.topic_id
                where t.slug = :slug
                order by ca.id desc
                fetch first 10 rows only
                """,
                slug=topic_slug,
            )
            for row in cursor.fetchall():
                print(row)

            print("--- latest evidence ---")
            cursor.execute(
                """
                select c.label, ce.hint_used, ce.confusion_note, ce.evidence_snippet, ce.created_at
                from concept_evidence ce
                join concepts c on c.id = ce.concept_id
                join topics t on t.id = c.topic_id
                where t.slug = :slug
                order by ce.id desc
                fetch first 10 rows only
                """,
                slug=topic_slug,
            )
            for row in cursor.fetchall():
                label, hint_used, confusion_note, snippet, created_at = row
                if hasattr(snippet, 'read'):
                    snippet = snippet.read()
                print((label, hint_used, confusion_note, (snippet or '')[:180], created_at))
    return 0


if __name__ == "__main__":
    topic = sys.argv[1] if len(sys.argv) > 1 else "agent-memory"
    raise SystemExit(main(topic))
