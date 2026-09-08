from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class ConceptPacket(BaseModel):
    id: str
    label: str
    summary: str = ""
    primary_topic: str
    related_topics: list[str] = Field(default_factory=list)
    foundational: bool = False
    supporting_snippets: list[str] = Field(default_factory=list)
    diagnostic_prompts: list[str] = Field(default_factory=list)
    hint_reframe_ladder: list[str] = Field(default_factory=list)
    related_concepts: list[str] = Field(default_factory=list)


class ConceptEdge(BaseModel):
    source: str
    target: str
    kind: str


class TopicPacket(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    topic_slug: str = Field(alias="topic")
    title: str
    grounding_label: str | None = None
    source_report_path: str | None = None
    concepts: list[ConceptPacket] = Field(default_factory=list)
    edges: list[ConceptEdge] = Field(default_factory=list)
    review_markdown: str | None = None
    review_markdown_path: Path | None = None
    research_markdown: str | None = None
    research_markdown_path: Path | None = None
