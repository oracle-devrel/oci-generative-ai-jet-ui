import pytest
from soccer_agent.agent.tools import TOOL_SCHEMAS, dispatch


def test_tool_schemas_shape():
    names = {t["name"] for t in TOOL_SCHEMAS}
    assert names == {
        "sql_query", "vector_search", "hybrid_retrieve", "predict_match",
        "build_match_briefing", "lookup_prediction", "remember", "recall",
        "get_elo", "get_team_form", "get_h2h", "get_momentum",
        "get_poisson_xg", "get_tournament_context",
    }


@pytest.mark.integration
def test_sql_query_select_ok(memory_schema_ready):
    r = dispatch("sql_query", {"sql": "SELECT 1 AS one FROM DUAL"}, session_id="t")
    assert r["rows"] == [{"ONE": 1}]


@pytest.mark.integration
def test_sql_query_rejects_delete(memory_schema_ready):
    r = dispatch("sql_query", {"sql": "DELETE FROM PREDICCIONES_FINAL"}, session_id="t")
    assert "error" in r and "SELECT" in r["error"]


@pytest.mark.integration
def test_lookup_prediction(predictions_loaded):
    r = dispatch("lookup_prediction",
                 {"home_team": "Spain", "away_team": "Brazil"}, session_id="t")
    assert r["prob_home_win"] == pytest.approx(0.45)
