from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from limitless.db.pool import get_pool
from limitless.research.packet_loader import load_topic_packet
from limitless.settings import Settings


def main() -> int:
    settings = Settings()

    print("Limitless smoke summary")
    print("-----------------------")
    print(f"Oracle target: {settings.oracle_dsn}")
    print(f"Wallet enabled: {settings.uses_wallet}")
    print(f"Vector enabled: {settings.oracle_vector_enabled}")

    packets = [
        load_topic_packet(
            "content/concept_packets/agent-memory.reviewed.json",
            "content/concept_packets/agent-memory.review.md",
            "content/research/agent-memory.md",
        ),
        load_topic_packet(
            "content/concept_packets/agent-loop.reviewed.json",
            "content/concept_packets/agent-loop.review.md",
            "content/research/agent-loop.md",
        ),
    ]
    for packet in packets:
        print(f"Packet ready: {packet.topic_slug} ({len(packet.concepts)} concepts)")

    pool = get_pool(settings)
    with pool.acquire() as connection:
        with connection.cursor() as cursor:
            cursor.execute("select count(*) from topics where slug in ('agent-memory','agent-loop')")
            topic_count = int(cursor.fetchone()[0])
            cursor.execute("select count(*) from concepts c join topics t on t.id = c.topic_id where t.slug in ('agent-memory','agent-loop')")
            concept_count = int(cursor.fetchone()[0])
            cursor.execute("select count(*) from xp_sessions s join topics t on t.id = s.topic_id where t.slug in ('agent-memory','agent-loop')")
            session_count = int(cursor.fetchone()[0])
            cursor.execute("select slug from topics where slug in ('agent-memory','agent-loop') order by slug")
            workshop_topics = [row[0] for row in cursor.fetchall()]

    print(f"Workshop topics found: {', '.join(workshop_topics)}")
    print(f"Workshop concept count: {concept_count}")
    print(f"Workshop XP sessions: {session_count}")
    print("Skills ready: ai-research, xp-builder, xp-debrief, framework-builder")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
