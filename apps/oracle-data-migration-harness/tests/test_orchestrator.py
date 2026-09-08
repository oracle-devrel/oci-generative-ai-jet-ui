import pytest
from data_migration_harness.orchestrator import run_migration

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_seven_stages_emit_in_order():
    seen_stages_ordered = []
    async for event in run_migration():
        if not seen_stages_ordered or seen_stages_ordered[-1] != event["stage"]:
            seen_stages_ordered.append(event["stage"])
    assert seen_stages_ordered == [
        "plan",
        "sample",
        "translate_schema",
        "dry_run",
        "transfer",
        "verify",
        "reconcile",
        "unlocked",
    ]


@pytest.mark.asyncio
async def test_translate_schema_narration_mentions_duality():
    found = False
    async for event in run_migration():
        if event["stage"] == "translate_schema" and event["status"] == "completed":
            assert "Duality" in event["narration"]
            found = True
    assert found
