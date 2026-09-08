from __future__ import annotations

from typing import Iterable

from limitless.graph.models import TopicPacket
from limitless.research.chunker import ResearchChunk


def build_deterministic_concept_grounding(packet: TopicPacket | dict) -> dict[str, list[str]]:
    concepts: Iterable
    if isinstance(packet, TopicPacket):
        concepts = packet.concepts
        return {concept.id: list(concept.supporting_snippets) for concept in concepts}

    concepts = packet.get("concepts", [])
    return {
        concept["id"]: list(concept.get("supporting_snippets", []))
        for concept in concepts
    }


def match_concept_snippets_to_chunks(
    packet: TopicPacket,
    chunks: list[ResearchChunk],
) -> dict[str, list[tuple[str, int]]]:
    matches: dict[str, list[tuple[str, int]]] = {}

    for concept in packet.concepts:
        concept_matches: list[tuple[str, int]] = []
        for snippet in concept.supporting_snippets:
            normalized_snippet = snippet.lower()
            matched_index = 0
            for chunk in chunks:
                if normalized_snippet in chunk.content.lower():
                    matched_index = chunk.chunk_index
                    break
            concept_matches.append((snippet, matched_index))
        matches[concept.id] = concept_matches

    return matches
