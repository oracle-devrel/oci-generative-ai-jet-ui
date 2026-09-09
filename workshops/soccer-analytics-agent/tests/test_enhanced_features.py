from datetime import datetime, timedelta

import pytest

from enhanced_features import (
    FootballElo,
    H2HTracker,
    TeamTracker,
    determine_conceded_first,
)


def test_football_elo_goal_diff_multiplier():
    elo = FootballElo()

    assert elo.goal_diff_multiplier(0) == 1.0
    assert elo.goal_diff_multiplier(1) == 1.0
    assert elo.goal_diff_multiplier(2) == 1.5
    assert elo.goal_diff_multiplier(3) == 1.75
    assert elo.goal_diff_multiplier(5) == pytest.approx(2.0)


def test_team_tracker_defaults_and_days_since_last():
    tracker = TeamTracker()
    today = datetime(2026, 5, 23)

    assert tracker.weighted_form(10) == 0.5
    assert tracker.days_since_last(today) == 30

    tracker.add_match(today - timedelta(days=8), 2, 0)
    tracker.add_match(today - timedelta(days=4), 1, 1)
    tracker.add_match(today - timedelta(days=2), 0, 1)

    assert tracker.days_since_last(today) == 2
    assert tracker.form(10) == pytest.approx(0.5)


def test_h2h_tracker_records_matches_from_team_perspective():
    tracker = H2HTracker()
    tracker.add_match("Spain", "Brazil", 2, 1)
    tracker.add_match("Brazil", "Spain", 1, 1)

    spain = tracker.get_features("Spain", "Brazil")
    brazil = tracker.get_features("Brazil", "Spain")

    assert spain["h2h_matches"] == 2
    assert spain["h2h_win_rate"] == 0.5
    assert spain["h2h_goal_diff"] == pytest.approx(0.5)
    assert brazil["h2h_goal_diff"] == pytest.approx(-0.5)


def test_determine_conceded_first_accounts_for_own_goals():
    goals = [("Spain", "Own Goal", "12", True, False)]

    assert determine_conceded_first(goals, "Spain", gf=1, ga=2) is True
    assert determine_conceded_first(goals, "Brazil", gf=2, ga=1) is False


def test_determine_conceded_first_uses_scoreline_when_goal_times_missing():
    assert determine_conceded_first([], "Spain", gf=0, ga=0) is False
    assert determine_conceded_first([], "Spain", gf=0, ga=1) is True
