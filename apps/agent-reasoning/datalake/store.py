"""
ReasoningStore: high-level interface for persisting and querying reasoning traces.

Provides CRUD operations over reasoning sessions, events, metrics, and
comparisons stored in Oracle 26ai Free via SQLAlchemy + python-oracledb.
"""

import json
import logging
import uuid
from dataclasses import asdict
from datetime import datetime
from typing import Any, Dict, Generator, List, Optional

from sqlalchemy import create_engine, func, or_
from sqlalchemy.orm import sessionmaker

from datalake.config import DatabaseConfig, get_db_config
from datalake.models import (
    Base,
    ReasoningComparison,
    ReasoningEvent,
    ReasoningMetric,
    ReasoningSession,
)

logger = logging.getLogger(__name__)


def _serialize_event_data(data: Any) -> str:
    """Serialize event data to JSON string.

    Handles dataclass instances, dicts, strings, and other primitives.
    """
    if data is None:
        return json.dumps(None)
    if isinstance(data, str):
        return json.dumps({"text": data})
    if hasattr(data, "__dataclass_fields__"):
        # Convert dataclass to dict, handling nested enums
        d = asdict(data)
        for k, v in d.items():
            if hasattr(v, "value"):
                d[k] = v.value
        return json.dumps(d)
    if isinstance(data, dict):
        return json.dumps(data)
    # Fallback: try JSON serialization
    try:
        return json.dumps(data, default=str)
    except (TypeError, ValueError):
        return json.dumps({"raw": str(data)})


class ReasoningStore:
    """
    High-level storage interface for reasoning session traces.

    Wraps SQLAlchemy sessions and provides domain-specific operations
    for creating, querying, replaying, and comparing reasoning runs.
    """

    def __init__(self, config: Optional[DatabaseConfig] = None):
        """
        Initialize the store with database configuration.

        Args:
            config: Oracle DB connection config. Uses env-var defaults if None.
        """
        if config is None:
            config = get_db_config()
        self.config = config

        self.engine = create_engine(
            config.connection_url,
            echo=config.echo,
            pool_size=config.pool_min,
            max_overflow=config.pool_max - config.pool_min,
            pool_pre_ping=True,
        )
        self.SessionFactory = sessionmaker(bind=self.engine)

    def init_db(self) -> None:
        """Create all tables if they do not exist."""
        Base.metadata.create_all(self.engine)
        logger.info("Database tables created/verified.")

    def drop_db(self) -> None:
        """Drop all tables. Use with caution."""
        Base.metadata.drop_all(self.engine)
        logger.warning("All database tables dropped.")

    # -------------------------------------------------------------------------
    # Session CRUD
    # -------------------------------------------------------------------------

    def create_session(
        self,
        query: str,
        strategy: str,
        model: str,
        metadata: Optional[Dict] = None,
    ) -> str:
        """
        Create a new reasoning session.

        Args:
            query: The input query/prompt.
            strategy: Reasoning strategy name (e.g. 'cot', 'tot', 'react').
            model: Model identifier (e.g. 'gemma3:latest').
            metadata: Optional dict of additional metadata.

        Returns:
            The UUID string of the created session.
        """
        session_id = str(uuid.uuid4())
        with self.SessionFactory() as db:
            session = ReasoningSession(
                id=session_id,
                query=query,
                strategy=strategy,
                model=model,
                status="running",
                session_metadata=json.dumps(metadata) if metadata else None,
            )
            db.add(session)
            db.commit()
            logger.info(
                "Created session %s (strategy=%s, model=%s)",
                session_id,
                strategy,
                model,
            )
        return session_id

    def add_event(
        self,
        session_id: str,
        event_type: str,
        data: Any,
        is_update: bool = False,
    ) -> str:
        """
        Add a reasoning event to a session.

        Automatically assigns the next sequence number within the session.

        Args:
            session_id: The parent session UUID.
            event_type: Event type string (node, task, sample, iteration, etc.).
            data: Event payload — a dataclass, dict, or string.
            is_update: Whether this event updates a previous one.

        Returns:
            The UUID string of the created event.
        """
        event_id = str(uuid.uuid4())
        serialized_data = _serialize_event_data(data)

        with self.SessionFactory() as db:
            # Get next sequence number for this session
            max_seq = (
                db.query(func.coalesce(func.max(ReasoningEvent.sequence_num), 0))
                .filter(ReasoningEvent.session_id == session_id)
                .scalar()
            )
            next_seq = max_seq + 1

            event = ReasoningEvent(
                id=event_id,
                session_id=session_id,
                event_type=event_type,
                sequence_num=next_seq,
                data=serialized_data,
                is_update=is_update,
            )
            db.add(event)
            db.commit()
        return event_id

    def add_events_batch(
        self,
        session_id: str,
        events: List[Dict[str, Any]],
    ) -> List[str]:
        """
        Add multiple events in a single transaction.

        Args:
            session_id: The parent session UUID.
            events: List of dicts with keys: event_type, data, is_update (optional).

        Returns:
            List of created event UUIDs.
        """
        event_ids = []
        with self.SessionFactory() as db:
            max_seq = (
                db.query(func.coalesce(func.max(ReasoningEvent.sequence_num), 0))
                .filter(ReasoningEvent.session_id == session_id)
                .scalar()
            )

            for i, evt in enumerate(events, start=1):
                event_id = str(uuid.uuid4())
                event = ReasoningEvent(
                    id=event_id,
                    session_id=session_id,
                    event_type=evt["event_type"],
                    sequence_num=max_seq + i,
                    data=_serialize_event_data(evt["data"]),
                    is_update=evt.get("is_update", False),
                )
                db.add(event)
                event_ids.append(event_id)

            db.commit()
        return event_ids

    def complete_session(
        self,
        session_id: str,
        final_answer: Optional[str] = None,
        metrics: Optional[Dict[str, Any]] = None,
        total_tokens: Optional[int] = None,
        status: str = "completed",
    ) -> None:
        """
        Finalize a reasoning session.

        Args:
            session_id: The session UUID.
            final_answer: The final generated answer.
            metrics: Dict with keys: ttft_ms, total_ms, tokens_per_sec, token_count, model.
            total_tokens: Total token count (alternative to metrics dict).
            status: Final status (completed, failed, cancelled).
        """
        with self.SessionFactory() as db:
            session = db.query(ReasoningSession).filter(ReasoningSession.id == session_id).first()
            if session is None:
                raise ValueError(f"Session {session_id} not found")

            session.status = status
            session.completed_at = datetime.utcnow()
            if final_answer is not None:
                session.final_answer = final_answer
            if total_tokens is not None:
                session.total_tokens = total_tokens

            # Add metrics if provided
            if metrics:
                metric = ReasoningMetric(
                    id=str(uuid.uuid4()),
                    session_id=session_id,
                    ttft_ms=metrics.get("ttft_ms"),
                    total_ms=metrics.get("total_ms"),
                    tokens_per_sec=metrics.get("tokens_per_sec"),
                    token_count=metrics.get("token_count"),
                    model=metrics.get("model", session.model),
                )
                db.add(metric)

                # Also set total_tokens from metrics if not already set
                if total_tokens is None and metrics.get("token_count"):
                    session.total_tokens = metrics["token_count"]

            db.commit()
            logger.info("Completed session %s (status=%s)", session_id, status)

    # -------------------------------------------------------------------------
    # Querying
    # -------------------------------------------------------------------------

    def get_session(self, session_id: str) -> Optional[Dict]:
        """
        Get a full session with all events and metrics.

        Args:
            session_id: The session UUID.

        Returns:
            Dict with session data, events list, and metrics, or None.
        """
        with self.SessionFactory() as db:
            session = db.query(ReasoningSession).filter(ReasoningSession.id == session_id).first()
            if session is None:
                return None

            result = session.to_dict()
            result["events"] = [e.to_dict() for e in session.events]
            result["metrics"] = session.metrics.to_dict() if session.metrics else None
            return result

    def list_sessions(
        self,
        strategy: Optional[str] = None,
        model: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """
        List sessions with optional filtering and pagination.

        Args:
            strategy: Filter by strategy name.
            model: Filter by model name.
            status: Filter by status.
            limit: Max results to return.
            offset: Number of results to skip.

        Returns:
            Dict with 'sessions' list, 'total' count, 'limit', 'offset'.
        """
        with self.SessionFactory() as db:
            query = db.query(ReasoningSession)

            if strategy:
                query = query.filter(ReasoningSession.strategy == strategy)
            if model:
                query = query.filter(ReasoningSession.model == model)
            if status:
                query = query.filter(ReasoningSession.status == status)

            total = query.count()

            sessions = (
                query.order_by(ReasoningSession.created_at.desc()).offset(offset).limit(limit).all()
            )

            return {
                "sessions": [s.to_dict() for s in sessions],
                "total": total,
                "limit": limit,
                "offset": offset,
            }

    def replay_session(self, session_id: str) -> Generator[Dict, None, None]:
        """
        Replay a session's events in order.

        Yields events one at a time in sequence_num order, suitable for
        step-by-step replay or streaming to a frontend.

        Args:
            session_id: The session UUID.

        Yields:
            Event dicts in chronological order.
        """
        with self.SessionFactory() as db:
            events = (
                db.query(ReasoningEvent)
                .filter(ReasoningEvent.session_id == session_id)
                .order_by(ReasoningEvent.sequence_num)
                .all()
            )
            for event in events:
                yield event.to_dict()

    def compare_sessions(self, session_ids: List[str]) -> Dict[str, Any]:
        """
        Compare multiple sessions side by side.

        Args:
            session_ids: List of session UUIDs to compare.

        Returns:
            Dict with comparison data including sessions, metrics, and event counts.
        """
        sessions = []
        for sid in session_ids:
            session_data = self.get_session(sid)
            if session_data:
                sessions.append(session_data)

        if not sessions:
            return {"sessions": [], "summary": {}}

        # Build comparison summary
        summary = {
            "strategies": list(set(s["strategy"] for s in sessions)),
            "models": list(set(s["model"] for s in sessions)),
            "query": sessions[0].get("query", ""),
            "metrics_comparison": [],
        }

        for s in sessions:
            metrics_entry = {
                "session_id": s["id"],
                "strategy": s["strategy"],
                "model": s["model"],
                "status": s["status"],
                "event_count": s.get("event_count", 0),
            }
            if s.get("metrics"):
                metrics_entry.update(
                    {
                        "ttft_ms": s["metrics"].get("ttft_ms"),
                        "total_ms": s["metrics"].get("total_ms"),
                        "tokens_per_sec": s["metrics"].get("tokens_per_sec"),
                        "token_count": s["metrics"].get("token_count"),
                    }
                )
            summary["metrics_comparison"].append(metrics_entry)

        return {"sessions": sessions, "summary": summary}

    def get_stats(self) -> Dict[str, Any]:
        """
        Get aggregate statistics across all sessions.

        Returns:
            Dict with total counts, strategy breakdowns, model breakdowns,
            and performance aggregates.
        """
        with self.SessionFactory() as db:
            total_sessions = db.query(func.count(ReasoningSession.id)).scalar() or 0
            total_events = db.query(func.count(ReasoningEvent.id)).scalar() or 0
            completed = (
                db.query(func.count(ReasoningSession.id))
                .filter(ReasoningSession.status == "completed")
                .scalar()
                or 0
            )
            failed = (
                db.query(func.count(ReasoningSession.id))
                .filter(ReasoningSession.status == "failed")
                .scalar()
                or 0
            )
            running = (
                db.query(func.count(ReasoningSession.id))
                .filter(ReasoningSession.status == "running")
                .scalar()
                or 0
            )

            # Strategy breakdown
            strategy_rows = (
                db.query(
                    ReasoningSession.strategy,
                    func.count(ReasoningSession.id),
                )
                .group_by(ReasoningSession.strategy)
                .all()
            )
            by_strategy = {row[0]: row[1] for row in strategy_rows}

            # Model breakdown
            model_rows = (
                db.query(
                    ReasoningSession.model,
                    func.count(ReasoningSession.id),
                )
                .group_by(ReasoningSession.model)
                .all()
            )
            by_model = {row[0]: row[1] for row in model_rows}

            # Performance averages (completed sessions with metrics)
            perf = (
                db.query(
                    func.avg(ReasoningMetric.ttft_ms),
                    func.avg(ReasoningMetric.total_ms),
                    func.avg(ReasoningMetric.tokens_per_sec),
                    func.avg(ReasoningMetric.token_count),
                )
                .join(
                    ReasoningSession,
                    ReasoningSession.id == ReasoningMetric.session_id,
                )
                .filter(ReasoningSession.status == "completed")
                .first()
            )

            # Per-strategy performance
            strategy_perf_rows = (
                db.query(
                    ReasoningSession.strategy,
                    func.avg(ReasoningMetric.total_ms),
                    func.avg(ReasoningMetric.tokens_per_sec),
                    func.count(ReasoningSession.id),
                )
                .join(
                    ReasoningMetric,
                    ReasoningMetric.session_id == ReasoningSession.id,
                )
                .filter(ReasoningSession.status == "completed")
                .group_by(ReasoningSession.strategy)
                .all()
            )
            strategy_performance = [
                {
                    "strategy": row[0],
                    "avg_duration_ms": round(row[1], 2) if row[1] else None,
                    "avg_tokens_per_sec": round(row[2], 2) if row[2] else None,
                    "session_count": row[3],
                }
                for row in strategy_perf_rows
            ]

            # Event type distribution
            event_type_rows = (
                db.query(
                    ReasoningEvent.event_type,
                    func.count(ReasoningEvent.id),
                )
                .group_by(ReasoningEvent.event_type)
                .all()
            )
            by_event_type = {row[0]: row[1] for row in event_type_rows}

            return {
                "total_sessions": total_sessions,
                "total_events": total_events,
                "status_counts": {
                    "completed": completed,
                    "failed": failed,
                    "running": running,
                },
                "by_strategy": by_strategy,
                "by_model": by_model,
                "by_event_type": by_event_type,
                "performance": {
                    "avg_ttft_ms": round(perf[0], 2) if perf and perf[0] else None,
                    "avg_total_ms": round(perf[1], 2) if perf and perf[1] else None,
                    "avg_tokens_per_sec": (round(perf[2], 2) if perf and perf[2] else None),
                    "avg_token_count": (round(perf[3], 2) if perf and perf[3] else None),
                },
                "strategy_performance": strategy_performance,
            }

    def search_sessions(
        self,
        query_text: str,
        limit: int = 20,
    ) -> List[Dict]:
        """
        Search sessions by query text (case-insensitive substring match).

        Also searches in strategy names and final answers.

        Args:
            query_text: Text to search for.
            limit: Max results.

        Returns:
            List of matching session dicts.
        """
        with self.SessionFactory() as db:
            pattern = f"%{query_text}%"
            sessions = (
                db.query(ReasoningSession)
                .filter(
                    or_(
                        ReasoningSession.query.ilike(pattern),
                        ReasoningSession.strategy.ilike(pattern),
                        ReasoningSession.final_answer.ilike(pattern),
                        ReasoningSession.model.ilike(pattern),
                    )
                )
                .order_by(ReasoningSession.created_at.desc())
                .limit(limit)
                .all()
            )
            return [s.to_dict() for s in sessions]

    # -------------------------------------------------------------------------
    # Comparison management
    # -------------------------------------------------------------------------

    def create_comparison(
        self,
        name: str,
        session_ids: List[str],
        query: Optional[str] = None,
    ) -> str:
        """
        Create a named comparison of multiple sessions.

        Args:
            name: Human-readable comparison name.
            session_ids: List of session UUIDs to include.
            query: Optional query text for context.

        Returns:
            The UUID of the created comparison.
        """
        comparison_id = str(uuid.uuid4())
        with self.SessionFactory() as db:
            comparison = ReasoningComparison(
                id=comparison_id,
                name=name,
                query=query,
                session_ids=json.dumps(session_ids),
            )
            db.add(comparison)
            db.commit()
        return comparison_id

    def get_comparison(self, comparison_id: str) -> Optional[Dict]:
        """Get a comparison with its sessions."""
        with self.SessionFactory() as db:
            comp = (
                db.query(ReasoningComparison)
                .filter(ReasoningComparison.id == comparison_id)
                .first()
            )
            if comp is None:
                return None

            result = comp.to_dict()
            result["sessions"] = []
            for sid in result["session_ids"]:
                session_data = self.get_session(sid)
                if session_data:
                    result["sessions"].append(session_data)
            return result

    def list_comparisons(self, limit: int = 20) -> List[Dict]:
        """List all comparisons."""
        with self.SessionFactory() as db:
            comps = (
                db.query(ReasoningComparison)
                .order_by(ReasoningComparison.created_at.desc())
                .limit(limit)
                .all()
            )
            return [c.to_dict() for c in comps]

    # -------------------------------------------------------------------------
    # Export
    # -------------------------------------------------------------------------

    def export_session_json(self, session_id: str) -> Optional[str]:
        """Export a full session as a JSON string."""
        session_data = self.get_session(session_id)
        if session_data is None:
            return None
        return json.dumps(session_data, indent=2, default=str)

    def export_session_markdown(self, session_id: str) -> Optional[str]:
        """
        Export a session as a Markdown document.

        Produces a human-readable report with session metadata, event timeline,
        and metrics.
        """
        session_data = self.get_session(session_id)
        if session_data is None:
            return None

        lines = [
            f"# Reasoning Session: {session_data['strategy'].upper()}",
            "",
            f"**Session ID:** `{session_data['id']}`  ",
            f"**Strategy:** {session_data['strategy']}  ",
            f"**Model:** {session_data['model']}  ",
            f"**Status:** {session_data['status']}  ",
            f"**Created:** {session_data['created_at']}  ",
            f"**Completed:** {session_data.get('completed_at', 'N/A')}  ",
            "",
            "## Query",
            "",
            f"> {session_data['query']}",
            "",
        ]

        # Final answer
        if session_data.get("final_answer"):
            lines.extend(
                [
                    "## Final Answer",
                    "",
                    session_data["final_answer"],
                    "",
                ]
            )

        # Metrics
        if session_data.get("metrics"):
            m = session_data["metrics"]
            lines.extend(
                [
                    "## Performance Metrics",
                    "",
                    "| Metric | Value |",
                    "|--------|-------|",
                    f"| TTFT | {m.get('ttft_ms', 'N/A')} ms |",
                    f"| Total Duration | {m.get('total_ms', 'N/A')} ms |",
                    f"| Tokens/sec | {m.get('tokens_per_sec', 'N/A')} |",
                    f"| Token Count | {m.get('token_count', 'N/A')} |",
                    "",
                ]
            )

        # Events
        events = session_data.get("events", [])
        if events:
            lines.extend(
                [
                    "## Event Timeline",
                    "",
                    f"Total events: {len(events)}",
                    "",
                ]
            )
            for evt in events:
                update_tag = " (update)" if evt.get("is_update") else ""
                lines.append(f"### Event #{evt['sequence_num']}: `{evt['event_type']}`{update_tag}")
                lines.append("")
                if evt.get("data"):
                    lines.append("```json")
                    lines.append(json.dumps(evt["data"], indent=2, default=str))
                    lines.append("```")
                    lines.append("")

        return "\n".join(lines)

    # -------------------------------------------------------------------------
    # Cleanup
    # -------------------------------------------------------------------------

    def delete_session(self, session_id: str) -> bool:
        """Delete a session and all its events/metrics (cascade)."""
        with self.SessionFactory() as db:
            session = db.query(ReasoningSession).filter(ReasoningSession.id == session_id).first()
            if session is None:
                return False
            db.delete(session)
            db.commit()
            logger.info("Deleted session %s", session_id)
            return True

    def close(self) -> None:
        """Dispose of the engine and connection pool."""
        self.engine.dispose()
        logger.info("Database connections closed.")
