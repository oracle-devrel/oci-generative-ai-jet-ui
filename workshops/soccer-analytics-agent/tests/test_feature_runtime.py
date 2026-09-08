"""Integration tests for FeatureRuntime against the real Oracle dataset.

The session-scoped `soccer_user_ready` fixture uses an isolated Oracle test
schema and drops/recreates that schema between test sessions. This module asks
`match_data_ready` to load the dataset into the test schema before any
FeatureRuntime call without touching the workshop/demo schema.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import oracledb
import pytest

from enhanced_features import ALL_FEATURES
from soccer_agent.agent.feature_runtime import FeatureRuntime, get_runtime
from soccer_agent.agent.tools import dispatch
from soccer_agent.db import get_connection

REPO = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def match_data_ready(soccer_user_ready) -> None:
    """Ensure MATCH_RESULTS has rows in the isolated test schema.

    The session-scoped soccer_user_ready fixture recreates the test schema, so
    this module-scoped fixture restores the dataset on entry.
    """
    needs_reload = False
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM MATCH_RESULTS")
            (count,) = cur.fetchone()
            if count == 0:
                needs_reload = True
    except oracledb.DatabaseError:
        needs_reload = True

    if needs_reload:
        subprocess.run(
            ["uv", "run", "python", str(REPO / "scripts" / "setup_db.py")],
            check=True, cwd=REPO,
        )


@pytest.fixture(scope="module")
def runtime(match_data_ready) -> FeatureRuntime:
    """Fresh FeatureRuntime with cleared caches."""
    get_runtime.cache_clear()
    return get_runtime()


@pytest.mark.integration
def test_get_elo_top_nations_above_average(runtime: FeatureRuntime):
    spain = runtime.get_elo("Spain")
    brazil = runtime.get_elo("Brazil")
    assert spain["elo"] > 1500
    assert brazil["elo"] > 1500


@pytest.mark.integration
def test_get_elo_weak_nation_below_average(runtime: FeatureRuntime):
    sm = runtime.get_elo("San Marino")
    assert sm["elo"] < 1500


@pytest.mark.integration
def test_get_team_form_returns_real_numbers(runtime: FeatureRuntime):
    f = runtime.get_team_form("Spain", n=10)
    assert 0.0 <= f["form"] <= 1.0
    assert f["total_matches"] > 0
    assert f["avg_goals_scored"] > 0


@pytest.mark.integration
def test_get_h2h_known_pair(runtime: FeatureRuntime):
    h = runtime.get_h2h("Spain", "Brazil")
    # Spain and Brazil have played each other many times across history.
    assert h["h2h_matches"] > 0
    assert 0.0 <= h["h2h_win_rate"] <= 1.0


@pytest.mark.integration
def test_get_momentum_shape(runtime: FeatureRuntime):
    m = runtime.get_momentum("Germany", n=15)
    assert "current_streak" in m
    assert "clean_sheet_pct" in m
    assert 0.0 <= m["clean_sheet_pct"] <= 1.0


@pytest.mark.integration
def test_get_poisson_xg_lambdas_in_range(runtime: FeatureRuntime):
    p = runtime.get_poisson_xg("Spain", "Brazil")
    assert 0.3 <= p["home_lambda"] <= 5.0
    assert 0.3 <= p["away_lambda"] <= 5.0


@pytest.mark.integration
def test_get_tournament_context_shape(runtime: FeatureRuntime):
    t = runtime.get_tournament_context("Spain")
    assert "wc_form" in t
    assert "big_game_factor" in t


@pytest.mark.integration
def test_build_feature_row_covers_all_92(runtime: FeatureRuntime):
    row = runtime.build_feature_row("Spain", "Brazil", neutral=True)
    assert set(row.keys()) >= set(ALL_FEATURES)
    # Elo features must reflect the actual rating, not zeros
    assert row["home_elo"] > 1000
    assert row["away_elo"] > 1000
    # H2H must reflect real matches
    assert row["h2h_matches"] > 0


@pytest.mark.integration
def test_runtime_elo_matches_notebook_elo(runtime: FeatureRuntime):
    """Drift guard: runtime Elo must equal a fresh notebook-style replay.

    The notebook's chronological pass and the runtime's _elo() must produce
    identical ratings for the same input data. If they ever diverge, this
    test catches it — without that guard, refactors to enhanced_features.py
    could silently break the agent's predictions.
    """
    from enhanced_features import FootballElo

    runtime_elo = runtime._elo()
    fresh_elo = FootballElo.from_match_history(runtime._all_matches())

    for team in ("Spain", "Brazil", "Iceland", "San Marino", "Argentina"):
        assert runtime_elo.ratings[team] == fresh_elo.ratings[team], (
            f"Elo drift for {team}: runtime={runtime_elo.ratings[team]} "
            f"fresh={fresh_elo.ratings[team]}"
        )


@pytest.mark.integration
def test_predict_match_uses_real_features(runtime: FeatureRuntime):
    # Strong-vs-strong should produce a more balanced distribution than
    # weak-vs-strong. Both should have features_used == 92.
    spain_brazil = dispatch("predict_match",
                            {"home_team": "Spain", "away_team": "Brazil",
                             "neutral": True}, session_id="t")
    iceland_brazil = dispatch("predict_match",
                              {"home_team": "Iceland", "away_team": "Brazil",
                               "neutral": True}, session_id="t")

    assert spain_brazil["features_used"] == 92
    assert iceland_brazil["features_used"] == 92

    # Probabilities sum to ~1
    s_total = (spain_brazil["prob_home_win"] + spain_brazil["prob_draw"]
               + spain_brazil["prob_away_win"])
    assert abs(s_total - 1.0) < 1e-5

    # Iceland's home-win probability vs Brazil should be lower than Spain's
    assert iceland_brazil["prob_home_win"] < spain_brazil["prob_home_win"]


@pytest.mark.integration
def test_build_match_briefing_use_case(runtime: FeatureRuntime):
    briefing = dispatch(
        "build_match_briefing",
        {"home_team": "Spain", "away_team": "Brazil", "neutral": True,
         "focus": "broadcast"},
        session_id="t",
    )

    assert briefing["use_case"] == "match_intelligence_briefing"
    assert briefing["live_prediction"]["features_used"] == 92
    assert briefing["team_snapshots"]["Spain"]["elo"]["elo"] > 1500
    assert briefing["matchup_context"]["h2h"]["h2h_matches"] > 0
    assert briefing["matchup_context"]["poisson_xg"]["home_lambda"] > 0
    assert briefing["narrative_bullets"]
