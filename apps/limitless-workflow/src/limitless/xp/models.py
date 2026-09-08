from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


Phase = Literal["diagnostic", "teaching", "wrapup"]
Role = Literal["system", "assistant", "user"]


class DiagnosticPrompt(BaseModel):
    prompt_id: str
    target_concept_ids: list[str] = Field(default_factory=list)
    text: str


class SessionTurn(BaseModel):
    turn_index: int
    role: Role
    phase: str
    target_concept_ids: list[str] = Field(default_factory=list)
    content: str
    hints_used: int = 0
    grounding_reference: str | None = None


class SessionState(BaseModel):
    session_key: str
    topic_slug: str
    topic_title: str
    grounding_label: str | None = None
    session_id: int | None = None
    phase: str = "diagnostic"
    current_target_concept: str | None = None
    current_prompt_text: str | None = None
    hints_used: int = 0
    retry_count_for_current: int = 0
    current_index: int = 0
    diagnostic_concepts: list[str] = Field(default_factory=list)
    teaching_order: list[str] = Field(default_factory=list)
    concepts_covered: list[str] = Field(default_factory=list)
    turns: list[SessionTurn] = Field(default_factory=list)
    status: str = "created"
