"""Per-team feature runtime backed by Oracle.

Surfaces the notebook's enhanced-features trackers as on-demand methods.
Oracle is the source of truth; per-team windows are queried fresh each
cold call and cached in-process via lru_cache. Full-history Elo replays
once per process.
"""

from __future__ import annotations

import functools
from typing import Any

import numpy as np
import pandas as pd

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from enhanced_features import (  # noqa: E402
    ALL_FEATURES,
    FootballElo,
    GoalscorerTracker,
    H2HTracker,
    MomentumTracker,
    PoissonTracker,
    TeamTracker,
    TournamentTracker,
    get_venue_features,
)
from soccer_agent.db import get_connection  # noqa: E402


_STATEMENT_TIMEOUT_MS = 8000  # cap any single SELECT at 8s


def _coerce_neutral(series: pd.Series) -> pd.Series:
    """Normalize the NEUTRAL column to bool, treating NULLs as False."""
    if series.dtype == bool:
        return series
    return (series.astype(str).str.upper() == "TRUE").fillna(False)


class FeatureRuntime:
    """Hydrates enhanced-features trackers from Oracle on demand.

    All caches live for the process lifetime. The first call to anything
    that needs full-history Elo pays ~5-10s; everything else is <100ms.

    Singleton coupling note: the @lru_cache decorators on the instance
    methods below key on `self`. This is safe only because `get_runtime()`
    enforces a process-wide singleton — every call returns the same
    FeatureRuntime, so there is exactly one `self` for the lru_cache to
    hold. Do NOT construct FeatureRuntime() directly outside of tests;
    use `get_runtime()`.
    """

    # ---------- low-level Oracle access ----------

    @functools.lru_cache(maxsize=1)
    def _all_matches(self) -> pd.DataFrame:
        """Full chronological match history. Used for Elo replay."""
        with get_connection() as conn:
            conn.call_timeout = _STATEMENT_TIMEOUT_MS * 4  # full table read
            df = pd.read_sql(
                "SELECT DATE_RW, HOME_TEAM, AWAY_TEAM, HOME_SCORE, AWAY_SCORE, "
                "TOURNAMENT, CITY, COUNTRY, NEUTRAL FROM MATCH_RESULTS "
                "WHERE HOME_SCORE IS NOT NULL AND AWAY_SCORE IS NOT NULL "
                "ORDER BY DATE_RW",
                conn,
            )
        df.columns = [c.lower() for c in df.columns]
        df = df.rename(columns={"date_rw": "date"})
        df["date"] = pd.to_datetime(df["date"])
        df["neutral"] = _coerce_neutral(df["neutral"])
        return df

    @functools.lru_cache(maxsize=256)
    def _team_window(self, team: str, n: int) -> pd.DataFrame:
        """Last N matches involving team, oldest-first."""
        with get_connection() as conn:
            conn.call_timeout = _STATEMENT_TIMEOUT_MS
            df = pd.read_sql(
                "SELECT * FROM ("
                "  SELECT DATE_RW, HOME_TEAM, AWAY_TEAM, HOME_SCORE, AWAY_SCORE, "
                "         TOURNAMENT, CITY, COUNTRY, NEUTRAL "
                "    FROM MATCH_RESULTS "
                "   WHERE (HOME_TEAM = :t OR AWAY_TEAM = :t) "
                "     AND HOME_SCORE IS NOT NULL AND AWAY_SCORE IS NOT NULL "
                "   ORDER BY DATE_RW DESC FETCH FIRST :n ROWS ONLY"
                ") ORDER BY DATE_RW",
                conn,
                params={"t": team, "n": int(n)},
            )
        df.columns = [c.lower() for c in df.columns]
        df = df.rename(columns={"date_rw": "date"})
        if len(df):
            df["date"] = pd.to_datetime(df["date"])
            df["neutral"] = _coerce_neutral(df["neutral"])
        return df

    @functools.lru_cache(maxsize=128)
    def _h2h_window(self, a: str, b: str, n: int = 50) -> pd.DataFrame:
        """Last N matches between two teams (either ordering)."""
        with get_connection() as conn:
            conn.call_timeout = _STATEMENT_TIMEOUT_MS
            df = pd.read_sql(
                "SELECT * FROM ("
                "  SELECT DATE_RW, HOME_TEAM, AWAY_TEAM, HOME_SCORE, AWAY_SCORE, "
                "         TOURNAMENT, NEUTRAL "
                "    FROM MATCH_RESULTS "
                "   WHERE ((HOME_TEAM = :a AND AWAY_TEAM = :b) "
                "       OR (HOME_TEAM = :b AND AWAY_TEAM = :a)) "
                "     AND HOME_SCORE IS NOT NULL AND AWAY_SCORE IS NOT NULL "
                "   ORDER BY DATE_RW DESC FETCH FIRST :n ROWS ONLY"
                ") ORDER BY DATE_RW",
                conn,
                params={"a": a, "b": b, "n": int(n)},
            )
        df.columns = [c.lower() for c in df.columns]
        df = df.rename(columns={"date_rw": "date"})
        if len(df):
            df["date"] = pd.to_datetime(df["date"])
        return df

    @functools.lru_cache(maxsize=256)
    def _team_goals(self, team: str, n_goals: int = 50) -> pd.DataFrame:
        """Last N goals scored by team (from GOALSCORERS)."""
        with get_connection() as conn:
            conn.call_timeout = _STATEMENT_TIMEOUT_MS
            df = pd.read_sql(
                "SELECT * FROM ("
                "  SELECT DATE_RW, TEAM, SCORER, MINUTE, OWN_GOAL, PENALTY "
                "    FROM GOALSCORERS "
                "   WHERE TEAM = :t "
                "   ORDER BY DATE_RW DESC FETCH FIRST :n ROWS ONLY"
                ") ORDER BY DATE_RW",
                conn,
                params={"t": team, "n": int(n_goals)},
            )
        df.columns = [c.lower() for c in df.columns]
        df = df.rename(columns={"date_rw": "date"})
        if len(df):
            df["date"] = pd.to_datetime(df["date"])
        return df

    # ---------- hydrated trackers ----------

    @functools.lru_cache(maxsize=1)
    def _elo(self) -> FootballElo:
        """Replay full history; cold ~5-10s, warm 0ms."""
        return FootballElo.from_match_history(self._all_matches())

    def _team_tracker(self, team: str, n: int = 20) -> TeamTracker:
        """Build a TeamTracker from the last N matches involving `team`."""
        tt = TeamTracker()
        window = self._team_window(team, n)
        for row in window.itertuples(index=False):
            if row.home_team == team:
                gf, ga = row.home_score, row.away_score
            else:
                gf, ga = row.away_score, row.home_score
            tt.add_match(row.date, gf, ga)
        return tt

    def _momentum_tracker(self, team: str, n: int = 30) -> MomentumTracker:
        """Build a MomentumTracker from the last N matches involving `team`."""
        mt = MomentumTracker()
        window = self._team_window(team, n)
        for row in window.itertuples(index=False):
            if row.home_team == team:
                gf, ga = row.home_score, row.away_score
            else:
                gf, ga = row.away_score, row.home_score
            # We don't have minute data here; approximate conceded_first as "they
            # conceded and didn't score" — matches enhanced_features fallback.
            conceded_first = (ga > 0 and gf == 0) or (ga > gf)
            mt.add_match(team, gf, ga, conceded_first)
        return mt

    def _poisson_tracker(self, team: str, n: int = 30) -> PoissonTracker:
        pt = PoissonTracker()
        window = self._team_window(team, n)
        for row in window.itertuples(index=False):
            if row.home_team == team:
                gf, ga = row.home_score, row.away_score
            else:
                gf, ga = row.away_score, row.home_score
            pt.add_match(team, gf, ga)
        return pt

    def _tournament_tracker(self, team: str, n: int = 50) -> TournamentTracker:
        tt = TournamentTracker()
        window = self._team_window(team, n)
        for row in window.itertuples(index=False):
            if row.home_team == team:
                gf, ga = row.home_score, row.away_score
            else:
                gf, ga = row.away_score, row.home_score
            tt.add_match(team, row.tournament, row.date, gf, ga)
        return tt

    def _goalscorer_tracker(self, team: str, n_goals: int = 50) -> GoalscorerTracker:
        gst = GoalscorerTracker()
        goals = self._team_goals(team, n_goals)
        if not len(goals):
            return gst
        records = []
        for row in goals.itertuples(index=False):
            parsed = gst.parse_minute(row.minute)
            own_goal = str(row.own_goal).upper() == "TRUE"
            penalty = str(row.penalty).upper() == "TRUE"
            scorer = row.scorer if pd.notna(row.scorer) else "Unknown"
            records.append((parsed, penalty, own_goal, scorer))
        gst.add_goals(team, records)
        return gst

    def _h2h(self, a: str, b: str) -> H2HTracker:
        h = H2HTracker()
        window = self._h2h_window(a, b)
        for row in window.itertuples(index=False):
            h.add_match(row.home_team, row.away_team, row.home_score, row.away_score)
        return h

    # ---------- public tool entrypoints ----------

    def get_elo(self, team: str) -> dict[str, Any]:
        """Current Elo rating per tournament tier (notebook family 0).

        Mirrors FootballElo from enhanced_features.py — same K-factors,
        same goal-diff multiplier, same home advantage.
        """
        elo = self._elo()
        return {
            "team": team,
            "elo": float(elo.ratings[team]),
            "world_cup_elo": float(elo.tournament_ratings["world_cup"][team]),
            "continental_elo": float(elo.tournament_ratings["continental"][team]),
            "qualifier_elo": float(elo.tournament_ratings["qualifier"][team]),
            "friendly_elo": float(elo.tournament_ratings["friendly"][team]),
            "vs_average": float(elo.ratings[team] - 1500.0),
        }

    def get_team_form(self, team: str, n: int = 10) -> dict[str, Any]:
        """Recent form, weighted form, and goal averages (notebook family 0).

        Same TeamTracker math as the notebook — pts (W=1, D=0.5, L=0),
        exponential decay weighting, rolling goal averages over last N matches.
        """
        tt = self._team_tracker(team, max(n, 20))
        return {
            "team": team,
            "n": int(n),
            "form": float(tt.form(n)),
            "weighted_form": float(tt.weighted_form(n)),
            "avg_goals_scored": float(tt.avg_goals_scored(n)),
            "avg_goals_conceded": float(tt.avg_goals_conceded(n)),
            "goal_diff_avg": float(tt.goal_diff_avg(n)),
            "total_matches": int(tt.total_matches()),
        }

    def get_h2h(self, team_a: str, team_b: str) -> dict[str, Any]:
        """Head-to-head record (notebook family 0).

        Same H2HTracker as enhanced_features.py — win rate from team_a's
        perspective + goal diff per match + total matches played.
        """
        h = self._h2h(team_a, team_b)
        feats = h.get_features(team_a, team_b)
        return {
            "team_a": team_a,
            "team_b": team_b,
            **{k: (float(v) if isinstance(v, (int, float, np.floating)) else v)
               for k, v in feats.items()},
        }

    def get_momentum(self, team: str, n: int = 15) -> dict[str, Any]:
        """Psychological/momentum features (notebook family 2).

        MomentumTracker: streaks, clean sheets, comebacks, draw tendency,
        blowout patterns. Conceded-first is approximated from final score
        when minute-level data is absent.
        """
        mt = self._momentum_tracker(team, max(n, 30))
        feats = mt.get_features(team, n)
        return {"team": team, "n": int(n),
                **{k: float(v) for k, v in feats.items()}}

    def get_poisson_xg(self, home_team: str, away_team: str,
                       n: int = 20) -> dict[str, Any]:
        """Poisson expected-goals model (notebook family 3).

        PoissonTracker: lambdas from attack-vs-defense rolling means,
        Poisson outcome probabilities via cached PMFs, overperformance
        vs actual win rate.
        """
        h_pt = self._poisson_tracker(home_team, max(n, 20))
        a_pt = self._poisson_tracker(away_team, max(n, 20))
        # Merge into a single tracker so we can call get_features(h, a)
        combined = PoissonTracker()
        combined.team_scoring[home_team] = h_pt.team_scoring[home_team]
        combined.team_conceding[home_team] = h_pt.team_conceding[home_team]
        combined.team_scoring[away_team] = a_pt.team_scoring[away_team]
        combined.team_conceding[away_team] = a_pt.team_conceding[away_team]
        feats = combined.get_features(home_team, away_team, n)
        return {"home_team": home_team, "away_team": away_team,
                **{k: float(v) for k, v in feats.items()}}

    def get_tournament_context(self, team: str) -> dict[str, Any]:
        """Tournament-stage context features (notebook family 5).

        TournamentTracker: WC-finals form vs continental vs qualifying vs
        friendly, plus the "big game factor" (competitive minus friendly).
        """
        tt = self._tournament_tracker(team)
        feats = tt.get_features(team)
        return {"team": team, **{k: float(v) for k, v in feats.items()}}

    # ---------- predict_match orchestrator ----------

    def build_feature_row(self, home_team: str, away_team: str,
                          neutral: bool = True,
                          city: str = "",
                          country: str = "",
                          tournament: str = "FIFA World Cup",
                          ) -> dict[str, float]:
        """Assemble the full 92-feature row predict_match needs.

        Uses the exact tracker classes and feature names from
        enhanced_features.py so the agent and the trained model speak
        the same language.
        """
        elo = self._elo()
        h_elo = float(elo.ratings[home_team])
        a_elo = float(elo.ratings[away_team])
        ha = 0 if neutral else elo.HOME_ADVANTAGE
        cat = elo.classify_tournament(tournament)
        h_t_elo = float(elo.tournament_ratings[cat][home_team])
        a_t_elo = float(elo.tournament_ratings[cat][away_team])

        elo_feats = {
            "home_elo": h_elo, "away_elo": a_elo,
            "elo_diff": h_elo - a_elo, "elo_total": h_elo + a_elo,
            "home_tournament_elo": h_t_elo, "away_tournament_elo": a_t_elo,
            "tournament_elo_diff": h_t_elo - a_t_elo,
            "home_expected": elo.expected_score(h_elo, a_elo, ha),
        }

        ht_t = self._team_tracker(home_team, 25)
        at_t = self._team_tracker(away_team, 25)
        form_feats = {
            "home_form_5": ht_t.form(5), "home_form_10": ht_t.form(10),
            "home_form_20": ht_t.form(20),
            "away_form_5": at_t.form(5), "away_form_10": at_t.form(10),
            "away_form_20": at_t.form(20),
            "home_weighted_form_10": ht_t.weighted_form(10),
            "away_weighted_form_10": at_t.weighted_form(10),
            "form_diff_5": ht_t.form(5) - at_t.form(5),
            "form_diff_10": ht_t.form(10) - at_t.form(10),
            "weighted_form_diff": ht_t.weighted_form(10) - at_t.weighted_form(10),
        }
        goal_feats = {
            "home_goals_scored_avg_10": ht_t.avg_goals_scored(10),
            "home_goals_conceded_avg_10": ht_t.avg_goals_conceded(10),
            "away_goals_scored_avg_10": at_t.avg_goals_scored(10),
            "away_goals_conceded_avg_10": at_t.avg_goals_conceded(10),
            "home_goal_diff_avg_10": ht_t.goal_diff_avg(10),
            "away_goal_diff_avg_10": at_t.goal_diff_avg(10),
            "goal_diff_differential": ht_t.goal_diff_avg(10) - at_t.goal_diff_avg(10),
            "attack_vs_defense": ht_t.avg_goals_scored(10) - at_t.avg_goals_conceded(10),
        }

        h2h_feats = self._h2h(home_team, away_team).get_features(home_team, away_team)

        context_feats = {
            "is_neutral": int(neutral), "is_home": int(not neutral),
            # Match enhanced_features.py:760 exactly — case-sensitive on
            # 'FIFA World Cup', 'qualification' substring on lowercase.
            "is_world_cup": int("FIFA World Cup" in tournament
                                and "qualification" not in tournament.lower()),
            "is_continental": int(cat == "continental"),
            "is_friendly": int(cat == "friendly"),
            # Hardcoded to the training-data median so live predictions stay
            # deterministic and reproducible (the workshop promises exact
            # numbers). Do NOT derive these from datetime.now(): the dataset's
            # latest match is forward-dated, so a wall-clock days_rest grows
            # every day and drifts predict_match off the documented values.
            "home_days_rest": 30,
            "away_days_rest": 30,
            "rest_diff": 0,
            "home_experience": ht_t.total_matches(),
            "away_experience": at_t.total_matches(),
        }

        gs_h = self._goalscorer_tracker(home_team).get_features(home_team)
        gs_a = self._goalscorer_tracker(away_team).get_features(away_team)
        gs_feats = {
            "home_scoring_depth": gs_h["scoring_depth"],
            "away_scoring_depth": gs_a["scoring_depth"],
            "scoring_depth_diff": gs_h["scoring_depth"] - gs_a["scoring_depth"],
            "home_star_dependency": gs_h["star_dependency"],
            "away_star_dependency": gs_a["star_dependency"],
            "home_penalty_ratio": gs_h["penalty_ratio"],
            "away_penalty_ratio": gs_a["penalty_ratio"],
            "home_late_goal_ratio": gs_h["late_goal_ratio"],
            "away_late_goal_ratio": gs_a["late_goal_ratio"],
            "late_goal_diff": gs_h["late_goal_ratio"] - gs_a["late_goal_ratio"],
            "home_first_half_ratio": gs_h["first_half_ratio"],
            "away_first_half_ratio": gs_a["first_half_ratio"],
        }

        mom_h = self._momentum_tracker(home_team).get_features(home_team)
        mom_a = self._momentum_tracker(away_team).get_features(away_team)
        mom_feats = {
            "home_streak": mom_h["current_streak"],
            "away_streak": mom_a["current_streak"],
            "streak_diff": mom_h["current_streak"] - mom_a["current_streak"],
            "home_unbeaten": mom_h["unbeaten_streak"],
            "away_unbeaten": mom_a["unbeaten_streak"],
            "home_clean_sheet_pct": mom_h["clean_sheet_pct"],
            "away_clean_sheet_pct": mom_a["clean_sheet_pct"],
            "home_comeback_rate": mom_h["comeback_rate"],
            "away_comeback_rate": mom_a["comeback_rate"],
            "home_draw_tendency": mom_h["draw_tendency"],
            "away_draw_tendency": mom_a["draw_tendency"],
            "draw_tendency_sum": mom_h["draw_tendency"] + mom_a["draw_tendency"],
            "home_blowout_win_pct": mom_h["blowout_win_pct"],
            "away_blowout_loss_pct": mom_a["blowout_loss_pct"],
            "home_shutout_loss_pct": mom_h["shutout_loss_pct"],
            "away_shutout_loss_pct": mom_a["shutout_loss_pct"],
        }

        # Poisson uses both teams' windows
        combined = PoissonTracker()
        h_pt = self._poisson_tracker(home_team)
        a_pt = self._poisson_tracker(away_team)
        combined.team_scoring[home_team] = h_pt.team_scoring[home_team]
        combined.team_conceding[home_team] = h_pt.team_conceding[home_team]
        combined.team_scoring[away_team] = a_pt.team_scoring[away_team]
        combined.team_conceding[away_team] = a_pt.team_conceding[away_team]
        poisson_feats = combined.get_features(home_team, away_team)

        venue_feats = get_venue_features(city, country, home_team, away_team)

        ttrk_h = self._tournament_tracker(home_team).get_features(home_team)
        ttrk_a = self._tournament_tracker(away_team).get_features(away_team)
        tournament_feats = {
            "home_wc_form": ttrk_h["wc_form"],
            "away_wc_form": ttrk_a["wc_form"],
            "wc_form_diff": ttrk_h["wc_form"] - ttrk_a["wc_form"],
            "home_competitive_form": ttrk_h["competitive_form"],
            "away_competitive_form": ttrk_a["competitive_form"],
            "home_big_game_factor": ttrk_h["big_game_factor"],
            "away_big_game_factor": ttrk_a["big_game_factor"],
            "big_game_diff": ttrk_h["big_game_factor"] - ttrk_a["big_game_factor"],
            "home_wc_experience": ttrk_h["wc_experience"],
            "away_wc_experience": ttrk_a["wc_experience"],
            "wc_experience_diff": ttrk_h["wc_experience"] - ttrk_a["wc_experience"],
        }

        full = {
            **elo_feats, **form_feats, **goal_feats, **h2h_feats, **context_feats,
            **gs_feats, **mom_feats, **poisson_feats,
            **venue_feats, **tournament_feats,
        }
        return {name: float(full.get(name, 0.0)) for name in ALL_FEATURES}


@functools.lru_cache(maxsize=1)
def get_runtime() -> FeatureRuntime:
    """Process-lifetime singleton."""
    return FeatureRuntime()
