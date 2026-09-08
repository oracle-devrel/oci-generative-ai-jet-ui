"""Record dataclasses for each memory type, plus the candidate type
that flows through the promotion gate."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal

MemoryType = Literal["policy", "preference", "fact", "episodic", "trace"]
Scope = Literal["global", "tenant", "user", "agent", "session"]


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


@dataclass
class FactRecord:
    fact_id: str
    tenant_id: str
    subject: str
    predicate: str
    content: str
    content_hash: str
    source_run_id: str
    confidence: float
    user_id: str | None = None
    agent_id: str | None = None
    source_turn_id: str | None = None
    metadata: dict[str, Any] | None = None
    status: str = "active"
    superseded_by: str | None = None
    expires_at: datetime | None = None
    created_at: datetime = field(default_factory=_now)


@dataclass
class EpisodeRecord:
    episode_id: str
    tenant_id: str
    task_type: str
    title: str
    summary: str
    outcome: str
    key_steps: list[str]
    source_run_id: str
    completed_at: datetime
    user_id: str | None = None
    artifacts: dict[str, Any] | None = None
    status: str = "active"


@dataclass
class MemoryCandidate:
    """Output of extraction; input to the promotion gate."""
    memory_type: MemoryType
    tenant_id: str
    content: str
    confidence: float
    source_run_id: str
    user_id: str | None = None
    agent_id: str | None = None
    source_turn_id: str | None = None

    # Fact-only fields
    subject: str | None = None
    predicate: str | None = None

    # Preference-only fields
    pref_key: str | None = None
    pref_value: Any | None = None
    source: str | None = None  # 'user_stated', 'inferred', 'admin_set'


@dataclass
class PromotionResult:
    """Gate verdict for one candidate."""
    # Gate action.
    outcome: Literal["written", "deduplicated", "rejected", "superseded"]
    record_id: str | None = None
    # Rejection reason, or 'superseded:<old_id>' on supersession.
    reason: str | None = None
    # Resulting record status. None for rejections and preferences
    # (PK-upserted, always active).
    status: str | None = None
    # Candidate's source confidence, echoed back for trace replay.
    confidence: float | None = None

    @classmethod
    def written(
        cls, record_id: str, status: str | None = None,
        confidence: float | None = None,
    ) -> "PromotionResult":
        return cls(
            outcome="written", record_id=record_id,
            status=status, confidence=confidence,
        )

    @classmethod
    def deduplicated(
        cls, existing_id: str, confidence: float | None = None,
    ) -> "PromotionResult":
        return cls(
            outcome="deduplicated", record_id=existing_id,
            confidence=confidence,
        )

    @classmethod
    def rejected(
        cls, reason: str, confidence: float | None = None,
    ) -> "PromotionResult":
        return cls(outcome="rejected", reason=reason, confidence=confidence)

    @classmethod
    def superseded(
        cls, new_id: str, old_id: str, confidence: float | None = None,
    ) -> "PromotionResult":
        return cls(
            outcome="superseded", record_id=new_id,
            reason=f"superseded:{old_id}", status="active",
            confidence=confidence,
        )
