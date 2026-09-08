from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from limitless.db.pool import get_pool
from limitless.db.repositories import apply_schema, load_packet_into_oracle, prepare_connection_for_app_dml
from limitless.research.packet_loader import load_topic_packet
from limitless.settings import Settings


def iter_packet_paths() -> list[tuple[Path, Path]]:
    packets: list[tuple[Path, Path]] = []
    packet_dir = ROOT / "content" / "concept_packets"
    for review_json in sorted(packet_dir.glob("*.reviewed.json")):
        review_md = review_json.with_name(review_json.name.replace(".reviewed.json", ".review.md"))
        packets.append((review_json, review_md))
    return packets


def main() -> int:
    settings = Settings()
    pool = get_pool(settings)

    summaries: list[dict[str, object]] = []
    with pool.acquire() as connection:
        prepare_connection_for_app_dml(connection)
        apply_schema(connection)
        for review_json, review_md in iter_packet_paths():
            packet = load_topic_packet(review_json, review_md)
            research_path = ROOT / (packet.source_report_path or "")
            research_markdown = research_path.read_text(encoding="utf-8") if research_path.exists() else ""
            summary = load_packet_into_oracle(
                connection,
                packet=packet,
                research_markdown=research_markdown,
            )
            summaries.append({"topic": packet.topic_slug, **summary})
        connection.commit()

    print("Loaded reviewed packets into Oracle:")
    for summary in summaries:
        print(
            f"- {summary['topic']}: concepts={summary['concept_count']}, chunks={summary['chunk_count']}, report_id={summary['report_id']}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
