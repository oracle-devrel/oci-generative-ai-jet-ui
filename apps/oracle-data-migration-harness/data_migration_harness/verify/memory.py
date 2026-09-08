"""Layer 8: conversation memory migration checks."""

from data_migration_harness.memory import chat_history


def check() -> bool:
    """Verify that Mongo-side conversation memory was imported into Oracle."""
    mongo_count = chat_history.count_mongo_messages()
    oracle_count = chat_history.count_oracle_messages(source_side="mongo")
    return mongo_count == oracle_count
