from __future__ import annotations

import json
from pathlib import Path

from limitless.graph.models import TopicPacket


def load_topic_packet(
    review_json_path: str | Path,
    review_markdown_path: str | Path | None = None,
    research_markdown_path: str | Path | None = None,
) -> TopicPacket:
    review_json = Path(review_json_path)
    data = json.loads(review_json.read_text(encoding="utf-8"))
    packet = TopicPacket.model_validate(data)

    if review_markdown_path is not None:
        review_md = Path(review_markdown_path)
        packet.review_markdown_path = review_md
        packet.review_markdown = review_md.read_text(encoding="utf-8")

    if research_markdown_path is not None:
        research_md = Path(research_markdown_path)
        packet.research_markdown_path = research_md
        packet.research_markdown = research_md.read_text(encoding="utf-8")

    return packet
