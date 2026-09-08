import pytest
from data_migration_harness.environment import mongo_db
from data_migration_harness.tools.duality import (
    DEMO_AGGREGATION,
    create_relational_schema,
    populate_from_landing,
    run_sql_aggregation,
)
from data_migration_harness.tools.oracle_landing import create_landing_table, land_documents

pytestmark = pytest.mark.integration


def test_duality_unlock_returns_categories():
    create_landing_table()
    docs = list(mongo_db().products.find().limit(50))
    land_documents(docs)
    create_relational_schema()
    populate_from_landing()
    rows = run_sql_aggregation(DEMO_AGGREGATION, {"max_price": 50.0})
    assert isinstance(rows, list)
    if rows:
        assert "category" in rows[0]
        assert "avg_rating" in rows[0]
