"""
SQLAlchemy ORM models for the reasoning datalake.

Uses the oracledb dialect with Oracle-native types:
  - VARCHAR2, CLOB, NUMBER, TIMESTAMP for standard columns
  - JSON column type for structured event data and metadata
  - UUIDs stored as VARCHAR2(36)

All tables live under the REASONING schema prefix by convention but
use the connected user's default schema.
"""

import uuid

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    """Declarative base for all datalake models."""

    pass


def generate_uuid() -> str:
    """Generate a new UUID string."""
    return str(uuid.uuid4())


class ReasoningSession(Base):
    """
    A single reasoning session — one query processed by one strategy.

    Captures the full lifecycle from creation through completion, including
    the final answer, timing, and arbitrary metadata.
    """

    __tablename__ = "reasoning_sessions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    query = Column(Text, nullable=False)
    strategy = Column(String(64), nullable=False, index=True)
    model = Column(String(128), nullable=False, index=True)
    created_at = Column(DateTime, default=func.now(), nullable=False, index=True)
    completed_at = Column(DateTime, nullable=True)
    final_answer = Column(Text, nullable=True)
    status = Column(
        String(20), nullable=False, default="running", index=True
    )  # running, completed, failed, cancelled
    total_tokens = Column(Integer, nullable=True)
    session_metadata = Column(Text, nullable=True)  # JSON stored as CLOB

    # Relationships
    events = relationship(
        "ReasoningEvent",
        back_populates="session",
        order_by="ReasoningEvent.sequence_num",
        cascade="all, delete-orphan",
    )
    metrics = relationship(
        "ReasoningMetric",
        back_populates="session",
        cascade="all, delete-orphan",
        uselist=False,
    )

    # Indexes
    __table_args__ = (
        Index("ix_sessions_strategy_model", "strategy", "model"),
        Index("ix_sessions_status_created", "status", "created_at"),
    )

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        import json

        return {
            "id": self.id,
            "query": self.query,
            "strategy": self.strategy,
            "model": self.model,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "completed_at": (self.completed_at.isoformat() if self.completed_at else None),
            "final_answer": self.final_answer,
            "status": self.status,
            "total_tokens": self.total_tokens,
            "metadata": (json.loads(self.session_metadata) if self.session_metadata else None),
            "event_count": len(self.events) if self.events else 0,
        }


class ReasoningEvent(Base):
    """
    A single event emitted during reasoning.

    Maps directly to the StreamEvent dataclass from the visualization layer.
    The data field stores the serialized event payload as JSON text, which
    can contain TreeNode, SubTask, VotingSample, ReflectionIteration,
    RefinementIteration, PipelineIteration, ReActStep, or ChainStep data.
    """

    __tablename__ = "reasoning_events"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    session_id = Column(
        String(36),
        ForeignKey("reasoning_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_type = Column(
        String(64), nullable=False, index=True
    )  # node, task, sample, iteration, refinement, pipeline, react_step, chain_step, text, final
    sequence_num = Column(Integer, nullable=False)
    data = Column(Text, nullable=False)  # JSON payload as CLOB
    created_at = Column(DateTime, default=func.now(), nullable=False)
    is_update = Column(Boolean, default=False, nullable=False)

    # Relationships
    session = relationship("ReasoningSession", back_populates="events")

    # Indexes
    __table_args__ = (
        Index("ix_events_session_seq", "session_id", "sequence_num"),
        Index("ix_events_type", "event_type"),
    )

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        import json

        return {
            "id": self.id,
            "session_id": self.session_id,
            "event_type": self.event_type,
            "sequence_num": self.sequence_num,
            "data": json.loads(self.data) if self.data else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "is_update": self.is_update,
        }


class ReasoningMetric(Base):
    """
    Performance metrics for a reasoning session.

    Captures timing (TTFT, total duration), throughput (tokens/sec),
    and token counts.
    """

    __tablename__ = "reasoning_metrics"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    session_id = Column(
        String(36),
        ForeignKey("reasoning_sessions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    ttft_ms = Column(Float, nullable=True)  # Time to first token (milliseconds)
    total_ms = Column(Float, nullable=True)  # Total duration (milliseconds)
    tokens_per_sec = Column(Float, nullable=True)  # Throughput
    token_count = Column(Integer, nullable=True)  # Total tokens generated
    model = Column(String(128), nullable=True)

    # Relationships
    session = relationship("ReasoningSession", back_populates="metrics")

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "session_id": self.session_id,
            "ttft_ms": self.ttft_ms,
            "total_ms": self.total_ms,
            "tokens_per_sec": self.tokens_per_sec,
            "token_count": self.token_count,
            "model": self.model,
        }


class ReasoningComparison(Base):
    """
    A named comparison grouping multiple reasoning sessions.

    Used to compare different strategies or models on the same query.
    The session_ids field stores a JSON array of session UUIDs.
    """

    __tablename__ = "reasoning_comparisons"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(256), nullable=False)
    query = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    session_ids = Column(Text, nullable=False)  # JSON array of UUIDs

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        import json

        return {
            "id": self.id,
            "name": self.name,
            "query": self.query,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "session_ids": (json.loads(self.session_ids) if self.session_ids else []),
        }
