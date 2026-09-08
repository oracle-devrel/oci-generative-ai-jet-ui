import pytest
from data_migration_harness.app import app
from fastapi.testclient import TestClient

client = TestClient(app)


@pytest.mark.integration
def test_mongo_stats_returns_counts():
    r = client.get("/stats/mongo")
    assert r.status_code == 200
    data = r.json()
    assert data["products"] >= 0
    assert data["categories"] >= 0


@pytest.mark.integration
def test_oracle_stats_handles_missing_tables_gracefully():
    """Oracle stats endpoint must not 500 if tables do not exist."""
    r = client.get("/stats/oracle")
    assert r.status_code == 200
    data = r.json()
    assert "products" in data or data.get("migrated") is False


@pytest.mark.integration
def test_reset_returns_status():
    r = client.post("/reset")
    assert r.status_code == 200
    assert r.json() == {"status": "reset"}


@pytest.mark.integration
def test_oracle_stats_after_reset_is_unmigrated():
    client.post("/reset")
    r = client.get("/stats/oracle")
    assert r.status_code == 200
    assert r.json() == {"migrated": False}
