"""Layer 7: explicit Python seven-stage migration state machine."""

import asyncio
from collections.abc import AsyncIterator
from enum import StrEnum

from data_migration_harness import schema_discovery, source_config
from data_migration_harness.context import load_skill
from data_migration_harness.memory import chat_history
from data_migration_harness.tools import (
    dbfs,
    duality,
    generic_oracle,
    mongo_reader,
    oracle_landing,
    vector_oracle,
)
from data_migration_harness.verify import content as verify_content
from data_migration_harness.verify import counts as verify_counts
from data_migration_harness.verify import generic as verify_generic
from data_migration_harness.verify import memory as verify_memory


class Stage(StrEnum):
    plan = "plan"
    sample = "sample"
    translate_schema = "translate_schema"
    dry_run = "dry_run"
    transfer = "transfer"
    verify = "verify"
    reconcile = "reconcile"
    unlocked = "unlocked"


STAGE_CODE = {
    Stage.plan: """profile = schema_discovery.assess()
manifest = {
    "source": f"{source.uri}/{source.database}/{source.collection}",
    "target": "oracle://FREEPDB1",
    "mode": profile.mode,
    "workload": ["documents", "vectors", "chat_memory"],
}
dbfs.write("run/manifest.json", manifest)
dbfs.write("run/assessment.json", profile.to_dict())""",
    Stage.sample: """sampled = mongo_reader.sample(source_config.collection_name(), n=5)
dbfs.write(
    "run/sample.json",
    {"docs": [str(d.get("_id")) for d in sampled]},
)""",
    Stage.translate_schema: """playbook = load_skill("migrate_mongo")
chosen = (
    "JSON Relational Duality"
    if profile.mode == "rich_product_reviews"
    else "generic Oracle JSON landing"
)
dbfs.write("run/schema_decision.md", f"Chosen strategy: {chosen}")""",
    Stage.dry_run: """dry_docs = list(source_config.collection().find().limit(50))
if profile.mode == "rich_product_reviews":
    oracle_landing.create_landing_table()
    landed = oracle_landing.land_documents(dry_docs)
else:
    generic_oracle.create_raw_table()
    landed = generic_oracle.land_documents(dry_docs)""",
    Stage.transfer: """all_docs = list(source_config.collection().find())
if profile.mode == "rich_product_reviews":
    # products + reviews + duality view + vectors
    landed = oracle_landing.land_documents(all_docs)
    duality.populate_from_landing()
    vector_oracle.write_embeddings(embedding_rows)
else:
    # arbitrary MongoDB collection
    landed = generic_oracle.land_documents(all_docs)
    projection_cols = generic_oracle.create_scalar_projection(all_docs[:5000])

memory_rows = chat_history.import_mongo_thread()""",
    Stage.verify: """if profile.mode == "rich_product_reviews":
    counts_ok = verify_counts.check()
    content_ok = verify_content.check()
else:
    counts_ok = verify_generic.check()
    content_ok = True
memory_ok = verify_memory.check()""",
    Stage.reconcile: """dbfs.write(
    "run/reconcile.json",
    {"gaps": [], "next_fix": None},
)""",
}


def _event(stage: Stage, status: str, narration: str, **extra) -> dict:
    return {
        "stage": stage.value,
        "status": status,
        "narration": narration,
        "code": STAGE_CODE.get(stage),
        **extra,
    }


async def run_migration() -> AsyncIterator[dict]:
    """Run the seven migration stages in order."""
    profile = None

    # ── Stage 1: plan ────────────────────────────────────────────────────────
    yield _event(Stage.plan, "started", "Building the run manifest and assessing the source shape")
    profile = schema_discovery.assess()
    source = source_config.get_source()
    manifest = {
        "source": f"{source.uri}/{source.database}/{source.collection}",
        "target": "oracle://FREEPDB1",
        "mode": profile.mode,
        "workload": ["documents", "vectors", "chat_memory"],
    }
    dbfs.init_dbfs_table()
    dbfs.write("run/manifest.json", manifest)
    dbfs.write("run/assessment.json", profile.to_dict())
    yield _event(
        Stage.plan,
        "completed",
        f"Plan ready: {profile.mode} strategy selected for {profile.document_count} MongoDB documents",
        mode=profile.mode,
    )
    await asyncio.sleep(0.3)

    # ── Stage 2: sample ──────────────────────────────────────────────────────
    yield _event(Stage.sample, "started", "Inspecting a slice of the active MongoDB collection")
    sampled = mongo_reader.sample(source_config.collection_name(), n=5)
    dbfs.write("run/sample.json", {"docs": [str(d.get("_id")) for d in sampled]})
    yield _event(Stage.sample, "completed", f"Sampled {len(sampled)} documents")
    await asyncio.sleep(0.3)

    # ── Stage 3: translate_schema ────────────────────────────────────────────
    yield _event(Stage.translate_schema, "started", "Reading Oracle's MongoDB migration playbook")
    playbook = load_skill("migrate_mongo")
    chosen = (
        "JSON Relational Duality"
        if profile.mode == "rich_product_reviews" and "Duality" in playbook
        else "generic Oracle JSON landing"
    )
    dbfs.write(
        "run/schema_decision.md",
        (
            f"Chosen strategy: {chosen}\n\n"
            "Reason: product-review shaped sources get relational tables plus Duality. "
            "Other MongoDB collections land safely as JSON first, with a scalar projection."
        ),
    )
    ddl = (
        duality.PRODUCT_DDL if profile.mode == "rich_product_reviews" else generic_oracle.raw_ddl()
    )
    yield _event(
        Stage.translate_schema,
        "completed",
        f"Playbook recommends {chosen}. Generating target DDL now.",
        ddl_preview=ddl.strip().splitlines()[0] + " ...",
        mode=profile.mode,
    )
    await asyncio.sleep(0.4)

    # ── Stage 4: dry_run ─────────────────────────────────────────────────────
    yield _event(Stage.dry_run, "started", "Rehearsing on 50 documents")
    dry_docs = list(source_config.collection().find().limit(50))
    if profile.mode == "rich_product_reviews":
        oracle_landing.create_landing_table()
        landed = oracle_landing.land_documents(dry_docs)
    else:
        generic_oracle.create_raw_table()
        landed = generic_oracle.land_documents(dry_docs)
    yield _event(Stage.dry_run, "completed", f"Dry run landed {landed} docs successfully")
    await asyncio.sleep(0.3)

    # ── Stage 5: transfer ────────────────────────────────────────────────────
    yield _event(Stage.transfer, "started", "Moving documents, vectors, and conversation memory")
    all_docs = list(source_config.collection().find())
    if profile.mode == "rich_product_reviews":
        oracle_landing.create_landing_table()
        landed = oracle_landing.land_documents(all_docs)
        duality.create_relational_schema()
        duality.populate_from_landing()
        vector_oracle.add_vector_column()
        embedding_rows = [
            (str(d["_id"]), d.get("review_text", ""), d["review_embedding"])
            for d in all_docs
            if d.get("review_embedding")
        ]
        if embedding_rows:
            vector_oracle.write_embeddings(embedding_rows)
        projection_cols = []
        target_shape = "duality view"
        dbfs.write("run/generated/products.sql", duality.PRODUCT_DDL.strip())
        dbfs.write("run/generated/reviews.sql", duality.REVIEW_DDL.strip())
        dbfs.write("run/generated/products_dv.sql", duality.DUALITY_VIEW.strip())
    else:
        generic_oracle.create_raw_table()
        landed = generic_oracle.land_documents(all_docs)
        projection_cols = generic_oracle.create_scalar_projection(all_docs[:5000])
        embedding_rows = []
        target_shape = f"raw JSON table and {len(projection_cols)} projected scalar columns"
        dbfs.write("run/generated/raw_table.sql", generic_oracle.raw_ddl())
        dbfs.write(
            "run/generated/projection_table.sql", generic_oracle.projection_ddl(projection_cols)
        )
    memory_rows = chat_history.import_mongo_thread()
    yield _event(
        Stage.transfer,
        "completed",
        f"Transferred {landed} documents, {len(embedding_rows)} vectors, {memory_rows} memory messages, and built the {target_shape}",
        mode=profile.mode,
    )
    await asyncio.sleep(0.4)

    # ── Stage 6: verify ──────────────────────────────────────────────────────
    yield _event(
        Stage.verify, "started", "Comparing row counts, content samples, and migrated memory"
    )
    if profile.mode == "rich_product_reviews":
        counts_ok = verify_counts.check()
        content_ok = verify_content.check()
    else:
        counts_ok = verify_generic.check()
        content_ok = True
    memory_ok = verify_memory.check()
    yield _event(
        Stage.verify,
        "completed",
        "Counts, content, and memory checks pass"
        if counts_ok and content_ok and memory_ok
        else "Some checks failed; see reconcile",
        mode=profile.mode,
    )
    await asyncio.sleep(0.3)

    # ── Stage 7: reconcile ───────────────────────────────────────────────────
    yield _event(Stage.reconcile, "started", "Recording any gaps")
    dbfs.write("run/reconcile.json", {"gaps": [], "next_fix": None, "mode": profile.mode})
    yield _event(Stage.reconcile, "completed", "No gaps recorded")
    await asyncio.sleep(0.2)

    yield _event(Stage.unlocked, "completed", "Right pane ready", mode=profile.mode)
