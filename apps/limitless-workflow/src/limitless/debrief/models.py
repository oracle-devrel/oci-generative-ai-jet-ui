from __future__ import annotations

from pydantic import BaseModel, Field


class ConceptDebrief(BaseModel):
    concept_slug: str
    concept_label: str
    concept_id: int | None = None
    score_before: float = 0.0
    score_after: float = 0.0
    band_before: str | None = None
    band_after: str
    delta: float = 0.0
    trend: str
    evidence_snippet: str
    hint_used: bool = False
    hints_used_count: int = 0
    confusion_note: str | None = None
    next_step: str


class DebriefResult(BaseModel):
    topic_slug: str
    topic_title: str
    session_key: str
    session_id: int | None = None
    concept_updates: list[ConceptDebrief] = Field(default_factory=list)
