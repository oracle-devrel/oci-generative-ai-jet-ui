"""Seed the demo tenant with policies, preferences, prior facts, and episodes.

Customer-support scenario: tenant acme-support, customer
jane_doe@example.com. Includes the Stripe webhook signature-mismatch
episode used by the multi-turn demo.
"""
from __future__ import annotations
import asyncio
import os
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

from memory.db import connect
from memory.hashing import content_hash
from memory.stores.policy import PolicyStore
from memory.stores.preference import PreferenceStore
from memory.stores.fact import FactStore
from memory.stores.episodic import EpisodicStore

TENANT = os.getenv("DEMO_TENANT_ID", "acme-support")
USER = os.getenv("DEMO_USER_ID", "jane_doe@example.com")
AGENT = os.getenv("DEMO_AGENT_ID", "agent:support_v1")


async def seed() -> None:
    conn = await connect()
    try:
        policies = PolicyStore(conn)
        preferences = PreferenceStore(conn)
        facts = FactStore(conn)
        episodes = EpisodicStore(conn)

        # ----- Policies: tenant-scoped, exact-match rules -----------------
        policy_rows = [
            ("refund_threshold", {"max_auto_approve_usd": 500}, "approval"),
            ("tone_guardrail", {"forbidden_phrases": ["unfortunately, our policy"]}, "guardrail"),
            ("data_residency", {"allowed_regions": ["us-east-1"]}, "compliance"),
            (
                "escalation_path",
                {"trigger": "negative_sentiment", "after_turns": 3, "queue": "tier2"},
                "operational",
            ),
            (
                "pii_redaction",
                {"fields": ["ssn", "card_number", "cvv"], "mode": "mask"},
                "compliance",
            ),
        ]
        for key, value, ptype in policy_rows:
            await policies.set_policy(TENANT, key, value, ptype)

        # ----- Preferences: per-user, upsert ------------------------------
        # 'verbosity' is intentionally NOT seeded — the multi-turn demo
        # extracts it from a user message, and pre-seeding would short-
        # circuit that extraction path.
        preference_rows = [
            ("notification_channel", {"channel": "email"}, "onboarding", 1.0),
            ("timezone", {"tz": "America/New_York"}, "onboarding", 1.0),
            ("language", {"locale": "en-US"}, "profile", 1.0),
        ]
        for key, value, source, confidence in preference_rows:
            await preferences.set(USER, TENANT, key, value, source, confidence)

        # ----- Facts about the customer: scoped to USER -------------------
        # The v1 webhook URL is the supersession target for the demo's
        # turn 3 (v1 → v2); leave it as-is.
        # `deployment` is intentionally NOT seeded — the demo's region
        # extraction ("our production runs in us-west-2") should land as
        # a fresh fact rather than superseding seed data. A second region
        # statement later supersedes the first, exercising the path.
        personal_facts = [
            ("infrastructure",
             "Stripe webhook URL is https://api.acme.com/v1/stripe"),
            ("account",
             "Account tier: Enterprise (signed 2024-Q3, renews 2026-Q3)"),
            ("integration",
             "Uses Stripe Connect with platform model; charges flow through their platform account"),
            ("stack",
             "Primary stack: Python 3.11 + FastAPI on Kubernetes (EKS)"),
        ]
        # Seed bypasses the promotion gate intentionally: this is admin-
        # authored initial state, so it lands as 'active' rather than the
        # 'provisional' status the gate would assign to fresh tenant-scoped
        # facts. _write_unchecked is the explicit name for that bypass.
        for predicate, content in personal_facts:
            await facts._write_unchecked(
                TENANT, f"customer:{USER}", predicate, content,
                content_hash(content), "run_seed", 0.95,
                status="active", user_id=USER,
            )

        # ----- Tenant-wide product knowledge: user_id IS NULL -------------
        # These rows return for any user in the tenant, exercising the
        # scope hierarchy in retrieval.
        product_facts = [
            ("product:stripe", "webhook_signing",
             "Stripe webhooks are signed with HMAC-SHA256 over the raw request body; the signature is sent in the Stripe-Signature header."),
            ("product:stripe", "webhook_retries",
             "Webhook retries follow exponential backoff: 1s, 4s, 16s, 64s, then daily for 3 days before the event is dropped."),
            ("product:stripe", "rate_limits",
             "API rate limits: 100 read requests per second and 25 write requests per second per account in live mode."),
        ]
        for subject, predicate, content in product_facts:
            await facts._write_unchecked(
                TENANT, subject, predicate, content,
                content_hash(content), "run_seed", 1.0, status="active",
            )

        # ----- Episodes: prior support cases ------------------------------
        episode_rows = [
            (
                "support_case",
                "Stripe webhook signature mismatch after secret rotation",
                "User rotated webhook secret in dashboard but kept old secret "
                "in env var. Resolved by updating env var and redeploying.",
                "resolved",
                [
                    "Confirmed signature verification was failing for all events",
                    "Compared dashboard secret to env var",
                    "Updated env var, redeployed, verified delivery",
                ],
                datetime(2026, 1, 15, tzinfo=timezone.utc),
            ),
            (
                "support_case",
                "Refund failed due to currency-locale mismatch",
                "Refund request sent a USD amount for an EUR charge. Resolved "
                "by reading the currency from the original charge object "
                "instead of the customer's locale setting.",
                "resolved",
                [
                    "Identified mismatched currency in failed refund response",
                    "Switched code to read currency from the charge, not the customer",
                    "Backfilled affected refunds via batch script",
                ],
                datetime(2026, 2, 8, tzinfo=timezone.utc),
            ),
            (
                "support_case",
                "Idempotency key collision during bulk data migration",
                "Bulk import reused idempotency keys across retries, causing "
                "later writes to silently return cached responses. Resolved "
                "by namespacing keys with the migration run_id.",
                "resolved",
                [
                    "Noticed duplicate-looking POSTs returning identical 200s",
                    "Traced to Stripe's idempotency cache",
                    "Re-ran migration with run-scoped idempotency keys",
                ],
                datetime(2026, 3, 22, tzinfo=timezone.utc),
            ),
        ]
        for task_type, title, summary, outcome, key_steps, completed_at in episode_rows:
            await episodes.write(
                TENANT, task_type,
                title=title, summary=summary, outcome=outcome,
                key_steps=key_steps, source_run_id="run_seed",
                user_id=USER, completed_at=completed_at,
            )

        fact_count = len(personal_facts) + len(product_facts)
        print(
            f"Seeded tenant {TENANT}: "
            f"{len(policy_rows)} policies, "
            f"{len(preference_rows)} preferences, "
            f"{fact_count} facts, "
            f"{len(episode_rows)} episodes."
        )
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(seed())
