"""Promotion gate: classify → dedup → verify → compute_status → write.

Rules:
  1. Status is computed at write time, never user-supplied.
  2. Dedup keys on content_hash + scope tuple.
  3. Provisional records are not retrievable by default.

Contradiction-driven supersession lives in MemoryManager.
"""
from __future__ import annotations
from typing import Any
from memory.hashing import content_hash
from memory.records import MemoryCandidate, PromotionResult
from memory.stores.fact import FactStore
from memory.stores.preference import PreferenceStore
from memory.stores.episodic import EpisodicStore


def compute_status(scope: str, memory_type: str) -> str:
    """agent-scoped, preferences, and episodes → active. Otherwise provisional."""
    if scope == "agent":
        return "active"
    if memory_type in ("preference", "episodic"):
        return "active"
    return "provisional"


def resolve_scope(candidate: MemoryCandidate) -> str:
    """Most-specific scope wins: agent > user (preferences only) > tenant."""
    if candidate.agent_id:
        return "agent"
    if candidate.user_id and candidate.memory_type == "preference":
        return "user"
    return "tenant"


class PromotionGate:
    """Implements promote(candidate) -> PromotionResult contract."""

    def __init__(
        self,
        fact_store: FactStore,
        preference_store: PreferenceStore,
        episodic_store: EpisodicStore,
        manager: Any | None = None,  # MemoryManager — set after construction
    ):
        self.fact = fact_store
        self.pref = preference_store
        self.episodic = episodic_store
        self.manager = manager

    async def promote(self, candidate: MemoryCandidate) -> PromotionResult:
        """Run the full gate in one transaction. Rolls back on any exit
        path; commits only after a successful write."""
        scope = resolve_scope(candidate)
        memory_type = candidate.memory_type
        chash = content_hash(candidate.content)
        conn = self.fact.conn  # stores share one AsyncConnection

        try:
            # 1. Dedup. Facts use content_hash; preferences are PK-upserted.
            if memory_type == "fact":
                existing = await self.fact.find_dedup(
                    content_hash=chash,
                    tenant_id=candidate.tenant_id,
                    user_id=candidate.user_id,
                    agent_id=candidate.agent_id,
                )
                if existing:
                    await conn.rollback()
                    return PromotionResult.deduplicated(
                        existing, confidence=candidate.confidence,
                    )

            # 2. Type-specific verification
            if memory_type == "fact":
                if candidate.confidence < 0.7:
                    await conn.rollback()
                    return PromotionResult.rejected(
                        "low_confidence", confidence=candidate.confidence,
                    )
                if not candidate.source_run_id:
                    await conn.rollback()
                    return PromotionResult.rejected(
                        "no_provenance", confidence=candidate.confidence,
                    )
                # Contradiction → supersession. Rollback first so the
                # manager's supersede_fact transaction runs clean.
                if candidate.subject and candidate.predicate:
                    contradiction = await self.fact.find_contradiction(
                        tenant_id=candidate.tenant_id,
                        subject=candidate.subject,
                        predicate=candidate.predicate,
                        content_hash=chash,
                        user_id=candidate.user_id,
                    )
                    if contradiction:
                        if self.manager is None:
                            await conn.rollback()
                            return PromotionResult.rejected(
                                "needs_manager_for_supersede",
                                confidence=candidate.confidence,
                            )
                        await conn.rollback()
                        return await self.manager.supersede_fact(contradiction, candidate)

            if memory_type == "preference":
                if candidate.confidence is not None and candidate.confidence < 0.5:
                    await conn.rollback()
                    return PromotionResult.rejected(
                        "low_confidence", confidence=candidate.confidence,
                    )
                if not candidate.pref_key:
                    await conn.rollback()
                    return PromotionResult.rejected(
                        "no_pref_key", confidence=candidate.confidence,
                    )

            # 3. Compute status from scope+type.
            status = compute_status(scope, memory_type)

            # 4. Dispatch the write. commit=False keeps the dedup
            # SELECTs and the write in one transaction.
            if memory_type == "fact":
                fid = await self.fact._write_unchecked(
                    tenant_id=candidate.tenant_id,
                    subject=candidate.subject,
                    predicate=candidate.predicate,
                    content=candidate.content,
                    content_hash=chash,
                    source_run_id=candidate.source_run_id,
                    source_turn_id=candidate.source_turn_id,
                    confidence=candidate.confidence,
                    status=status,
                    user_id=candidate.user_id,
                    agent_id=candidate.agent_id,
                    commit=False,
                )
                await conn.commit()
                return PromotionResult.written(
                    fid, status=status, confidence=candidate.confidence,
                )

            if memory_type == "preference":
                await self.pref.set(
                    user_id=candidate.user_id,
                    tenant_id=candidate.tenant_id,
                    pref_key=candidate.pref_key,
                    pref_value=candidate.pref_value,
                    source=candidate.source or "inferred",
                    confidence=candidate.confidence,
                    commit=False,
                )
                await conn.commit()
                # Preferences are PK-upserted; status=None on the result.
                return PromotionResult.written(
                    candidate.pref_key, confidence=candidate.confidence,
                )

            await conn.rollback()
            return PromotionResult.rejected(
                f"no_handler_for_type:{memory_type}",
                confidence=candidate.confidence,
            )
        except Exception:
            # Any mid-flight failure rolls back; exception still propagates.
            await conn.rollback()
            raise
