#!/usr/bin/env python3
"""
Enhanced World Cup 2026 Feature Engineering
============================================
Builds on the existing Elo + form features with 5 new feature families
designed to break through the ~60% accuracy ceiling.

New feature families:
1. Goalscorer Intelligence (timing, depth, star dependency, penalties)
2. Psychological/Momentum (streaks, comebacks, clean sheets, draw tendency)
3. Poisson Expected Goals (over/underperformance vs statistical expectation)
4. Venue/Geography (altitude, confederation cross-match dynamics)
5. Tournament Stage Context (group vs knockout behavior)

Usage:
    python enhanced_features.py [--from-csv] [--from-oracle]
"""

import pandas as pd
import numpy as np
from collections import defaultdict, Counter
from scipy.stats import poisson
import warnings
import os
import sys

warnings.filterwarnings('ignore')

DATA_DIR = os.path.dirname(os.path.abspath(__file__))


# =============================================================================
# DATA LOADING
# =============================================================================

def load_from_csv():
    """Load match results and goalscorers from local CSVs."""
    df = pd.read_csv(os.path.join(DATA_DIR, "results.csv"))
    df['date'] = pd.to_datetime(df['date'])
    if df['neutral'].dtype == object:
        df['neutral'] = df['neutral'].map({'TRUE': True, 'FALSE': False, True: True, False: False})

    def get_result(row):
        if row['home_score'] > row['away_score']:
            return 'Win'
        if row['home_score'] < row['away_score']:
            return 'Loss'
        return 'Draw'

    df['result'] = df.apply(get_result, axis=1)
    df['year'] = df['date'].dt.year
    df = df.sort_values('date').reset_index(drop=True)

    gs = pd.read_csv(os.path.join(DATA_DIR, "goalscorers.csv"))
    gs['date'] = pd.to_datetime(gs['date'])

    print(f"Loaded {len(df):,} matches, {len(gs):,} goals from CSV")
    return df, gs


def load_from_oracle():
    """Load from Oracle ADB."""
    import oracledb
    connection = oracledb.connect(
        user="worldcup", password="YourPassword123#",
        dsn="myatp_low", config_dir="./wallet",
        wallet_location="./wallet", wallet_password="WorldCupDB1234"
    )
    df = pd.read_sql("""
        SELECT DATE_RW as "date", HOME_TEAM as home_team, AWAY_TEAM as away_team,
               HOME_SCORE as home_score, AWAY_SCORE as away_score,
               TOURNAMENT as tournament, CITY as city, COUNTRY as country, NEUTRAL as neutral
        FROM MATCH_RESULTS ORDER BY DATE_RW
    """, connection)
    gs = pd.read_sql("""
        SELECT DATE_RW as "date", HOME_TEAM as home_team, AWAY_TEAM as away_team,
               TEAM as team, SCORER as scorer, MINUTE as minute,
               OWN_GOAL as own_goal, PENALTY as penalty
        FROM GOALSCORERS ORDER BY DATE_RW
    """, connection)
    connection.close()

    df['date'] = pd.to_datetime(df['date'])
    if df['neutral'].dtype == object:
        df['neutral'] = df['neutral'].map({'TRUE': True, 'FALSE': False})

    def get_result(row):
        if row['home_score'] > row['away_score']:
            return 'Win'
        if row['home_score'] < row['away_score']:
            return 'Loss'
        return 'Draw'

    df['result'] = df.apply(get_result, axis=1)
    df['year'] = df['date'].dt.year
    df = df.sort_values('date').reset_index(drop=True)
    gs['date'] = pd.to_datetime(gs['date'])

    print(f"Loaded {len(df):,} matches, {len(gs):,} goals from Oracle")
    return df, gs


# =============================================================================
# EXISTING FEATURES (Elo, Form, Goals, H2H) - kept from original notebook
# =============================================================================

class FootballElo:
    INITIAL_RATING = 1500
    HOME_ADVANTAGE = 100
    K_FACTORS = {'world_cup': 60, 'continental': 50, 'qualifier': 40, 'friendly': 20}
    TOURNAMENT_CATEGORIES = {
        'FIFA World Cup': 'world_cup', 'Copa America': 'continental',
        'UEFA Euro': 'continental', 'African Cup of Nations': 'continental',
        'AFC Asian Cup': 'continental', 'CONCACAF Gold Cup': 'continental',
        'Oceania Nations Cup': 'continental', 'UEFA Nations League': 'qualifier',
        'Confederations Cup': 'continental',
    }

    def __init__(self):
        self.ratings = defaultdict(lambda: self.INITIAL_RATING)
        self.tournament_ratings = defaultdict(lambda: defaultdict(lambda: self.INITIAL_RATING))

    def classify_tournament(self, tournament):
        for key, cat in self.TOURNAMENT_CATEGORIES.items():
            if key.lower() in tournament.lower():
                return cat
        if 'qualification' in tournament.lower() or 'qualifier' in tournament.lower():
            return 'qualifier'
        if 'friendly' in tournament.lower():
            return 'friendly'
        return 'qualifier'

    def goal_diff_multiplier(self, gd):
        gd = abs(gd)
        if gd <= 1:
            return 1.0
        if gd == 2:
            return 1.5
        if gd == 3:
            return 1.75
        return 1.75 + (gd - 3) / 8

    def expected_score(self, ra, rb, ha=0):
        return 1.0 / (1.0 + 10.0 ** (-(ra - rb + ha) / 400.0))

    @classmethod
    def from_match_history(cls, df):
        """Replay a chronologically-sorted match DataFrame and return populated Elo.

        Same math as the notebook's chronological pass — used by the agent's
        FeatureRuntime to hydrate current Elo on demand from Oracle.
        """
        elo = cls()
        for row in df.itertuples(index=False):
            elo.update(row.home_team, row.away_team, row.home_score, row.away_score,
                       row.tournament, bool(row.neutral), row.date)
        return elo

    def update(self, ht, at, hs, as_, tournament, is_neutral, date):
        home_elo = self.ratings[ht]
        away_elo = self.ratings[at]
        cat = self.classify_tournament(tournament)
        k = self.K_FACTORS[cat]
        ha = 0 if is_neutral else self.HOME_ADVANTAGE
        home_exp = self.expected_score(home_elo, away_elo, ha)
        gd = hs - as_
        g = self.goal_diff_multiplier(gd)
        h_actual = 1.0 if gd > 0 else (0.5 if gd == 0 else 0.0)
        a_actual = 1.0 - h_actual

        self.ratings[ht] += k * g * (h_actual - home_exp)
        self.ratings[at] += k * g * (a_actual - (1 - home_exp))

        home_t_elo = self.tournament_ratings[cat][ht]
        away_t_elo = self.tournament_ratings[cat][at]
        home_t_exp = self.expected_score(home_t_elo, away_t_elo, ha)
        self.tournament_ratings[cat][ht] += k * g * (h_actual - home_t_exp)
        self.tournament_ratings[cat][at] += k * g * (a_actual - (1 - home_t_exp))

        return {
            'home_elo': home_elo, 'away_elo': away_elo,
            'elo_diff': home_elo - away_elo, 'elo_total': home_elo + away_elo,
            'home_expected': home_exp,
            'home_tournament_elo': home_t_elo, 'away_tournament_elo': away_t_elo,
            'tournament_elo_diff': home_t_elo - away_t_elo,
            'k_factor': k, 'tournament_category': cat,
        }


class TeamTracker:
    def __init__(self):
        self.match_history = []
        self.last_match_date = None

    def add_match(self, date, gf, ga):
        pts = 1.0 if gf > ga else (0.5 if gf == ga else 0.0)
        self.match_history.append((date, gf, ga, pts))
        self.last_match_date = date

    def form(self, n):
        recent = self.match_history[-n:]
        return np.mean([r[3] for r in recent]) if len(recent) >= 3 else 0.5

    def weighted_form(self, n, decay=0.9):
        recent = self.match_history[-n:]
        if len(recent) < 3:
            return 0.5
        weights = [decay ** i for i in range(len(recent) - 1, -1, -1)]
        return np.average([r[3] for r in recent], weights=weights)

    def avg_goals_scored(self, n):
        recent = self.match_history[-n:]
        return np.mean([r[1] for r in recent]) if len(recent) >= 3 else 1.5

    def avg_goals_conceded(self, n):
        recent = self.match_history[-n:]
        return np.mean([r[2] for r in recent]) if len(recent) >= 3 else 1.5

    def goal_diff_avg(self, n):
        recent = self.match_history[-n:]
        return np.mean([r[1] - r[2] for r in recent]) if len(recent) >= 3 else 0.0

    def days_since_last(self, current_date):
        if self.last_match_date is None:
            return 30
        return (current_date - self.last_match_date).days

    def total_matches(self):
        return len(self.match_history)


class H2HTracker:
    def __init__(self):
        self.records = defaultdict(lambda: defaultdict(int))

    def get_key(self, a, b):
        return (min(a, b), max(a, b))

    def add_match(self, ht, at, hs, as_):
        key = self.get_key(ht, at)
        self.records[key]['total'] += 1
        self.records[key][f'{ht}_goals'] += hs
        self.records[key][f'{at}_goals'] += as_
        if hs > as_:
            self.records[key][f'{ht}_wins'] += 1
        elif as_ > hs:
            self.records[key][f'{at}_wins'] += 1
        else:
            self.records[key]['draws'] += 1

    def get_features(self, a, b):
        key = self.get_key(a, b)
        rec = self.records[key]
        total = rec['total']
        if total == 0:
            return {'h2h_win_rate': 0.5, 'h2h_matches': 0, 'h2h_goal_diff': 0.0}
        return {
            'h2h_win_rate': rec.get(f'{a}_wins', 0) / total,
            'h2h_matches': total,
            'h2h_goal_diff': (rec.get(f'{a}_goals', 0) - rec.get(f'{b}_goals', 0)) / total,
        }


# =============================================================================
# NEW FEATURE FAMILY 1: GOALSCORER INTELLIGENCE
# =============================================================================

class GoalscorerTracker:
    """
    Tracks per-team goalscoring patterns from the goalscorers table.
    Features: timing, depth, star dependency, penalty reliance.
    """
    def __init__(self):
        # Per team: list of (minute, is_penalty, is_own_goal, scorer_name)
        self.team_goals = defaultdict(list)

    def parse_minute(self, minute_str):
        """Parse minute string like '45+2' or '90+3' into integer."""
        if pd.isna(minute_str) or minute_str == '':
            return None
        try:
            minute_str = str(minute_str).strip()
            if '+' in minute_str:
                parts = minute_str.split('+')
                return int(parts[0]) + int(parts[1])
            return int(float(minute_str))
        except (ValueError, IndexError):
            return None

    def add_goals(self, team, goals_list):
        """Add a list of (minute, is_penalty, is_own_goal, scorer) tuples."""
        self.team_goals[team].extend(goals_list)

    def get_features(self, team, n_recent_goals=50):
        """Extract goalscoring pattern features from last n goals."""
        goals = self.team_goals[team][-n_recent_goals:]
        if len(goals) < 5:
            return {
                'scoring_depth': 0.5,
                'star_dependency': 0.5,
                'penalty_ratio': 0.1,
                'late_goal_ratio': 0.2,
                'early_goal_ratio': 0.2,
                'first_half_ratio': 0.5,
            }

        minutes = [g[0] for g in goals if g[0] is not None]
        penalties = [g[1] for g in goals]
        scorers = [g[3] for g in goals if not g[2]]  # exclude own goals

        # Scoring depth: number of distinct scorers / total goals (higher = more distributed)
        if scorers:
            unique_scorers = len(set(scorers))
            scoring_depth = unique_scorers / len(scorers)
        else:
            scoring_depth = 0.5

        # Star dependency: top scorer's share of goals (higher = more dependent)
        if scorers:
            scorer_counts = Counter(scorers)
            top_scorer_goals = scorer_counts.most_common(1)[0][1]
            star_dependency = top_scorer_goals / len(scorers)
        else:
            star_dependency = 0.5

        # Penalty ratio
        penalty_ratio = sum(1 for p in penalties if p) / max(len(penalties), 1)

        # Goal timing features
        if minutes:
            late_goals = sum(1 for m in minutes if m >= 75) / len(minutes)
            early_goals = sum(1 for m in minutes if m <= 15) / len(minutes)
            first_half = sum(1 for m in minutes if m <= 45) / len(minutes)
        else:
            late_goals = 0.2
            early_goals = 0.2
            first_half = 0.5

        return {
            'scoring_depth': scoring_depth,
            'star_dependency': star_dependency,
            'penalty_ratio': penalty_ratio,
            'late_goal_ratio': late_goals,
            'early_goal_ratio': early_goals,
            'first_half_ratio': first_half,
        }


# =============================================================================
# NEW FEATURE FAMILY 2: PSYCHOLOGICAL/MOMENTUM
# =============================================================================

class MomentumTracker:
    """
    Tracks psychological features: streaks, comebacks, clean sheets, draw tendency.
    """
    def __init__(self):
        # Per team: list of (result_pts, goals_for, goals_against, conceded_first)
        self.team_results = defaultdict(list)

    def add_match(self, team, gf, ga, conceded_first):
        pts = 1.0 if gf > ga else (0.5 if gf == ga else 0.0)
        self.team_results[team].append((pts, gf, ga, conceded_first))

    def get_features(self, team, n=15):
        results = self.team_results[team][-n:]
        if len(results) < 5:
            return {
                'current_streak': 0, 'unbeaten_streak': 0,
                'clean_sheet_pct': 0.3, 'comeback_rate': 0.2,
                'draw_tendency': 0.25, 'blowout_win_pct': 0.1,
                'blowout_loss_pct': 0.1, 'shutout_loss_pct': 0.1,
            }

        pts_list = [r[0] for r in results]

        # Current winning streak (consecutive wins from most recent)
        streak = 0
        for p in reversed(pts_list):
            if p == 1.0:
                streak += 1
            else:
                break

        # Unbeaten streak (consecutive non-losses from most recent)
        unbeaten = 0
        for p in reversed(pts_list):
            if p >= 0.5:
                unbeaten += 1
            else:
                break

        # Clean sheet percentage
        clean_sheets = sum(1 for r in results if r[2] == 0)
        clean_sheet_pct = clean_sheets / len(results)

        # Comeback rate: won after conceding first
        conceded_first_matches = [r for r in results if r[3]]
        if conceded_first_matches:
            comebacks = sum(1 for r in conceded_first_matches if r[0] == 1.0)
            comeback_rate = comebacks / len(conceded_first_matches)
        else:
            comeback_rate = 0.2

        # Draw tendency
        draws = sum(1 for r in results if r[0] == 0.5)
        draw_tendency = draws / len(results)

        # Blowout win % (won by 3+ goals)
        blowout_wins = sum(1 for r in results if r[1] - r[2] >= 3)
        blowout_win_pct = blowout_wins / len(results)

        # Blowout loss % (lost by 3+ goals)
        blowout_losses = sum(1 for r in results if r[2] - r[1] >= 3)
        blowout_loss_pct = blowout_losses / len(results)

        # Shutout loss % (lost without scoring)
        shutout_losses = sum(1 for r in results if r[1] == 0 and r[2] > 0)
        shutout_loss_pct = shutout_losses / len(results)

        return {
            'current_streak': streak,
            'unbeaten_streak': unbeaten,
            'clean_sheet_pct': clean_sheet_pct,
            'comeback_rate': comeback_rate,
            'draw_tendency': draw_tendency,
            'blowout_win_pct': blowout_win_pct,
            'blowout_loss_pct': blowout_loss_pct,
            'shutout_loss_pct': shutout_loss_pct,
        }


# =============================================================================
# NEW FEATURE FAMILY 3: POISSON EXPECTED GOALS
# =============================================================================

class PoissonTracker:
    """
    Models each team's scoring rate as a Poisson process.
    Computes expected goals and over/underperformance.
    """
    def __init__(self):
        self.team_scoring = defaultdict(list)  # goals scored per match
        self.team_conceding = defaultdict(list)  # goals conceded per match

    def add_match(self, team, gf, ga):
        self.team_scoring[team].append(gf)
        self.team_conceding[team].append(ga)

    # Pre-compute Poisson PMF grid for common lambda values (vectorized lookup)
    _GOALS_RANGE = np.arange(8)
    _LAMBDA_GRID = np.arange(0.3, 5.05, 0.1)  # 0.3 to 5.0 in 0.1 steps
    _PMF_CACHE = {}

    @classmethod
    def _get_pmfs(cls, lam):
        """Get cached Poisson PMFs for a lambda value (rounded to nearest 0.1)."""
        key = round(lam * 10)
        if key not in cls._PMF_CACHE:
            cls._PMF_CACHE[key] = poisson.pmf(cls._GOALS_RANGE, lam)
        return cls._PMF_CACHE[key]

    def get_features(self, home_team, away_team, n=20):
        h_scored = self.team_scoring[home_team][-n:]
        h_conceded = self.team_conceding[home_team][-n:]
        a_scored = self.team_scoring[away_team][-n:]
        a_conceded = self.team_conceding[away_team][-n:]

        if len(h_scored) < 5 or len(a_scored) < 5:
            return {
                'home_lambda': 1.5, 'away_lambda': 1.2,
                'home_poisson_win': 0.4, 'home_poisson_draw': 0.25,
                'home_scoring_variance': 1.0, 'away_scoring_variance': 1.0,
                'home_overperformance': 0.0, 'away_overperformance': 0.0,
            }

        # Expected goals: home team's attack vs away team's defense (and vice versa)
        h_scored_arr = np.array(h_scored, dtype=np.float64)
        h_conceded_arr = np.array(h_conceded, dtype=np.float64)
        a_scored_arr = np.array(a_scored, dtype=np.float64)
        a_conceded_arr = np.array(a_conceded, dtype=np.float64)

        home_lambda = np.clip((h_scored_arr.mean() + a_conceded_arr.mean()) / 2, 0.3, 5.0)
        away_lambda = np.clip((a_scored_arr.mean() + h_conceded_arr.mean()) / 2, 0.3, 5.0)

        # Vectorized Poisson outcome probabilities using cached PMFs
        h_pmf = self._get_pmfs(home_lambda)
        a_pmf = self._get_pmfs(away_lambda)
        prob_matrix = np.outer(h_pmf, a_pmf)
        home_win_prob = float(np.tril(prob_matrix, -1).sum())
        draw_prob = float(np.trace(prob_matrix))

        # Scoring variance
        home_var = float(h_scored_arr.var()) if len(h_scored) >= 3 else 1.0
        away_var = float(a_scored_arr.var()) if len(a_scored) >= 3 else 1.0

        # Over/underperformance: actual win rate vs Poisson-expected
        h_actual_wins = float((h_scored_arr > h_conceded_arr).mean())
        a_actual_wins = float((a_scored_arr > a_conceded_arr).mean())

        return {
            'home_lambda': float(home_lambda),
            'away_lambda': float(away_lambda),
            'home_poisson_win': home_win_prob,
            'home_poisson_draw': draw_prob,
            'home_scoring_variance': home_var,
            'away_scoring_variance': away_var,
            'home_overperformance': h_actual_wins - home_win_prob,
            'away_overperformance': a_actual_wins - (1 - home_win_prob - draw_prob),
        }


# =============================================================================
# NEW FEATURE FAMILY 4: VENUE/GEOGRAPHY
# =============================================================================

# Major city altitudes (meters) - affects stamina significantly
CITY_ALTITUDES = {
    'mexico city': 2240, 'bogota': 2640, 'quito': 2850, 'la paz': 3640,
    'johannesburg': 1753, 'addis ababa': 2355, 'nairobi': 1795, 'denver': 1609,
    'madrid': 667, 'sao paulo': 760, 'guadalajara': 1566, 'monterrey': 540,
    'atlanta': 320, 'dallas': 131, 'houston': 15, 'kansas city': 247,
    'los angeles': 30, 'miami': 2, 'new york': 3, 'philadelphia': 12,
    'san francisco': 16, 'seattle': 54, 'toronto': 76, 'vancouver': 0,
}

# Team confederation mapping
TEAM_CONFEDERATIONS = {
    # UEFA
    'Germany': 'UEFA', 'France': 'UEFA', 'Spain': 'UEFA', 'England': 'UEFA',
    'Italy': 'UEFA', 'Netherlands': 'UEFA', 'Portugal': 'UEFA', 'Belgium': 'UEFA',
    'Croatia': 'UEFA', 'Switzerland': 'UEFA', 'Denmark': 'UEFA', 'Austria': 'UEFA',
    'Poland': 'UEFA', 'Sweden': 'UEFA', 'Czech Republic': 'UEFA', 'Turkey': 'UEFA',
    'Scotland': 'UEFA', 'Wales': 'UEFA', 'Norway': 'UEFA', 'Ireland': 'UEFA',
    'Republic of Ireland': 'UEFA', 'Serbia': 'UEFA', 'Ukraine': 'UEFA',
    'Romania': 'UEFA', 'Hungary': 'UEFA', 'Greece': 'UEFA', 'Russia': 'UEFA',
    'Slovakia': 'UEFA', 'Slovenia': 'UEFA', 'Albania': 'UEFA', 'Finland': 'UEFA',
    'Iceland': 'UEFA', 'Bosnia and Herzegovina': 'UEFA', 'North Macedonia': 'UEFA',
    'Montenegro': 'UEFA', 'Georgia': 'UEFA', 'Bulgaria': 'UEFA',
    # CONMEBOL
    'Brazil': 'CONMEBOL', 'Argentina': 'CONMEBOL', 'Uruguay': 'CONMEBOL',
    'Colombia': 'CONMEBOL', 'Chile': 'CONMEBOL', 'Peru': 'CONMEBOL',
    'Ecuador': 'CONMEBOL', 'Paraguay': 'CONMEBOL', 'Venezuela': 'CONMEBOL',
    'Bolivia': 'CONMEBOL',
    # CONCACAF
    'Mexico': 'CONCACAF', 'USA': 'CONCACAF', 'United States': 'CONCACAF',
    'Costa Rica': 'CONCACAF', 'Jamaica': 'CONCACAF', 'Honduras': 'CONCACAF',
    'Panama': 'CONCACAF', 'Canada': 'CONCACAF', 'El Salvador': 'CONCACAF',
    'Trinidad and Tobago': 'CONCACAF', 'Guatemala': 'CONCACAF',
    # AFC
    'Japan': 'AFC', 'South Korea': 'AFC', 'Iran': 'AFC', 'Saudi Arabia': 'AFC',
    'Australia': 'AFC', 'Qatar': 'AFC', 'Iraq': 'AFC',
    'United Arab Emirates': 'AFC', 'Uzbekistan': 'AFC', 'China PR': 'AFC',
    # CAF
    'Morocco': 'CAF', 'Senegal': 'CAF', 'Nigeria': 'CAF', 'Cameroon': 'CAF',
    'Ghana': 'CAF', 'Algeria': 'CAF', 'Tunisia': 'CAF', 'Egypt': 'CAF',
    'Ivory Coast': 'CAF', 'South Africa': 'CAF', "Cote d'Ivoire": 'CAF',
    'Mali': 'CAF', 'DR Congo': 'CAF', 'Burkina Faso': 'CAF',
    # OFC
    'New Zealand': 'OFC',
}

# Confederation strength tiers (based on historical World Cup performance)
CONFED_STRENGTH = {'UEFA': 1.0, 'CONMEBOL': 0.95, 'CONCACAF': 0.6, 'AFC': 0.5, 'CAF': 0.5, 'OFC': 0.3}


def get_venue_features(city, country, home_team, away_team):
    """Extract venue-related features."""
    city_lower = str(city).lower().strip() if pd.notna(city) else ''

    # Altitude
    altitude = CITY_ALTITUDES.get(city_lower, 100)  # default 100m
    is_high_altitude = int(altitude > 1500)

    # Confederation dynamics
    h_confed = TEAM_CONFEDERATIONS.get(home_team, 'OTHER')
    a_confed = TEAM_CONFEDERATIONS.get(away_team, 'OTHER')
    same_confederation = int(h_confed == a_confed)

    h_strength = CONFED_STRENGTH.get(h_confed, 0.4)
    a_strength = CONFED_STRENGTH.get(a_confed, 0.4)
    confed_strength_diff = h_strength - a_strength

    # Inter-continental flag (these tend to be more unpredictable)
    is_intercontinental = int(h_confed != a_confed)

    return {
        'altitude': altitude,
        'is_high_altitude': is_high_altitude,
        'same_confederation': same_confederation,
        'confed_strength_diff': confed_strength_diff,
        'is_intercontinental': is_intercontinental,
    }


# =============================================================================
# NEW FEATURE FAMILY 5: TOURNAMENT STAGE CONTEXT
# =============================================================================

class TournamentTracker:
    """
    Tracks team performance in different tournament contexts.
    World Cup group stage vs knockout, competitive vs friendly, etc.
    """
    def __init__(self):
        # Per team: {context: [result_pts]}
        self.context_results = defaultdict(lambda: defaultdict(list))

    def classify_stage(self, tournament, date):
        """Classify match as group/knockout/qualifying/friendly."""
        t = tournament.lower()
        if 'friendly' in t:
            return 'friendly'
        if 'qualification' in t or 'qualifier' in t:
            return 'qualifying'
        if 'fifa world cup' in t and 'qualification' not in t:
            return 'wc_finals'
        if any(x in t for x in ['euro', 'copa', 'asian cup', 'gold cup', 'african cup']):
            return 'continental_finals'
        return 'other_competitive'

    def add_match(self, team, tournament, date, gf, ga):
        stage = self.classify_stage(tournament, date)
        pts = 1.0 if gf > ga else (0.5 if gf == ga else 0.0)
        self.context_results[team][stage].append(pts)

    def get_features(self, team, n=20):
        contexts = self.context_results[team]

        def ctx_form(key, n=n):
            results = contexts.get(key, [])[-n:]
            return np.mean(results) if len(results) >= 3 else 0.5

        wc_form = ctx_form('wc_finals')
        competitive_form = ctx_form('wc_finals') * 0.4 + ctx_form('continental_finals') * 0.3 + ctx_form('qualifying') * 0.3
        friendly_form = ctx_form('friendly')

        # "Big game" factor: how much better/worse in competitive vs friendly
        big_game_factor = competitive_form - friendly_form

        # World Cup experience (total WC finals matches)
        wc_experience = len(contexts.get('wc_finals', []))

        return {
            'wc_form': wc_form,
            'competitive_form': competitive_form,
            'big_game_factor': big_game_factor,
            'wc_experience': wc_experience,
        }


# =============================================================================
# MAIN FEATURE PIPELINE
# =============================================================================

def build_goalscorer_index(gs_df):
    """
    Pre-process goalscorer data into a dict keyed by (date, home_team, away_team)
    for fast lookup during feature extraction. Uses itertuples for speed.
    """
    index = defaultdict(list)
    # Pre-process columns for speed
    gs = gs_df.copy()
    gs['scorer'] = gs['scorer'].fillna('Unknown')
    gs['own_goal'] = gs['own_goal'].astype(str).str.upper() == 'TRUE'
    gs['penalty'] = gs['penalty'].astype(str).str.upper() == 'TRUE'

    for row in gs.itertuples(index=False):
        key = (row.date, row.home_team, row.away_team)
        index[key].append((row.team, row.scorer, row.minute, row.own_goal, row.penalty))
    return index


def determine_conceded_first(match_goals, team, gf, ga):
    """
    Determine if a team conceded the first goal in a match.
    Uses goalscorer minute data when available.
    """
    if not match_goals or gf == 0:
        return ga > 0  # If they didn't score but conceded, they conceded first

    # Find the earliest goal
    earliest_minute = 999
    earliest_scored_for_team = None
    minute_parser = GoalscorerTracker()
    for g_team, _scorer, minute_str, own_goal, _penalty in match_goals:
        parsed = minute_parser.parse_minute(minute_str)
        if parsed is not None and parsed < earliest_minute:
            earliest_minute = parsed
            earliest_scored_for_team = (g_team == team) != bool(own_goal)

    if earliest_scored_for_team is None:
        return ga > 0

    return not earliest_scored_for_team


def build_features(df, gs_df, verbose=True):
    """
    Build the complete feature matrix with all 6 feature families.
    Returns a DataFrame ready for ML.
    """
    if verbose:
        print("Building goalscorer index...")
    gs_index = build_goalscorer_index(gs_df)

    # Initialize all trackers
    elo = FootballElo()
    team_trackers = defaultdict(TeamTracker)
    h2h = H2HTracker()
    gs_tracker = GoalscorerTracker()
    momentum = MomentumTracker()
    poisson_tracker = PoissonTracker()
    tournament_tracker = TournamentTracker()

    feature_rows = []

    if verbose:
        print("Processing matches chronologically...")
        total = len(df)

    for i, row in enumerate(df.itertuples(index=False)):
        ht, at = row.home_team, row.away_team
        hs, as_ = row.home_score, row.away_score
        is_neutral = row.neutral
        tournament = row.tournament
        date = row.date

        if verbose and i % 10000 == 0:
            print(f"  {i:,}/{total:,} ({i/total*100:.0f}%)")

        # ---- EXTRACT FEATURES (pre-match state) ----

        # Family 0: Elo
        elo_feats = elo.update(ht, at, hs, as_, tournament, is_neutral, date)

        # Family 0: Form
        ht_t = team_trackers[ht]
        at_t = team_trackers[at]
        form_feats = {
            'home_form_5': ht_t.form(5), 'home_form_10': ht_t.form(10),
            'home_form_20': ht_t.form(20),
            'away_form_5': at_t.form(5), 'away_form_10': at_t.form(10),
            'away_form_20': at_t.form(20),
            'home_weighted_form_10': ht_t.weighted_form(10),
            'away_weighted_form_10': at_t.weighted_form(10),
            'form_diff_5': ht_t.form(5) - at_t.form(5),
            'form_diff_10': ht_t.form(10) - at_t.form(10),
            'weighted_form_diff': ht_t.weighted_form(10) - at_t.weighted_form(10),
        }

        # Family 0: Goals
        goal_feats = {
            'home_goals_scored_avg_10': ht_t.avg_goals_scored(10),
            'home_goals_conceded_avg_10': ht_t.avg_goals_conceded(10),
            'away_goals_scored_avg_10': at_t.avg_goals_scored(10),
            'away_goals_conceded_avg_10': at_t.avg_goals_conceded(10),
            'home_goal_diff_avg_10': ht_t.goal_diff_avg(10),
            'away_goal_diff_avg_10': at_t.goal_diff_avg(10),
            'goal_diff_differential': ht_t.goal_diff_avg(10) - at_t.goal_diff_avg(10),
            'attack_vs_defense': ht_t.avg_goals_scored(10) - at_t.avg_goals_conceded(10),
        }

        # Family 0: H2H
        h2h_feats = h2h.get_features(ht, at)

        # Family 0: Context
        context_feats = {
            'is_neutral': int(is_neutral), 'is_home': int(not is_neutral),
            'is_world_cup': int('FIFA World Cup' in tournament and 'qualification' not in tournament.lower()),
            'is_continental': int(elo_feats['tournament_category'] == 'continental'),
            'is_friendly': int(elo_feats['tournament_category'] == 'friendly'),
            'home_days_rest': ht_t.days_since_last(date),
            'away_days_rest': at_t.days_since_last(date),
            'rest_diff': ht_t.days_since_last(date) - at_t.days_since_last(date),
            'home_experience': ht_t.total_matches(),
            'away_experience': at_t.total_matches(),
        }

        # ---- NEW FAMILY 1: Goalscorer Intelligence ----
        home_gs_feats = gs_tracker.get_features(ht)
        away_gs_feats = gs_tracker.get_features(at)
        goalscorer_feats = {
            'home_scoring_depth': home_gs_feats['scoring_depth'],
            'away_scoring_depth': away_gs_feats['scoring_depth'],
            'scoring_depth_diff': home_gs_feats['scoring_depth'] - away_gs_feats['scoring_depth'],
            'home_star_dependency': home_gs_feats['star_dependency'],
            'away_star_dependency': away_gs_feats['star_dependency'],
            'home_penalty_ratio': home_gs_feats['penalty_ratio'],
            'away_penalty_ratio': away_gs_feats['penalty_ratio'],
            'home_late_goal_ratio': home_gs_feats['late_goal_ratio'],
            'away_late_goal_ratio': away_gs_feats['late_goal_ratio'],
            'late_goal_diff': home_gs_feats['late_goal_ratio'] - away_gs_feats['late_goal_ratio'],
            'home_first_half_ratio': home_gs_feats['first_half_ratio'],
            'away_first_half_ratio': away_gs_feats['first_half_ratio'],
        }

        # ---- NEW FAMILY 2: Momentum ----
        home_mom = momentum.get_features(ht)
        away_mom = momentum.get_features(at)
        momentum_feats = {
            'home_streak': home_mom['current_streak'],
            'away_streak': away_mom['current_streak'],
            'streak_diff': home_mom['current_streak'] - away_mom['current_streak'],
            'home_unbeaten': home_mom['unbeaten_streak'],
            'away_unbeaten': away_mom['unbeaten_streak'],
            'home_clean_sheet_pct': home_mom['clean_sheet_pct'],
            'away_clean_sheet_pct': away_mom['clean_sheet_pct'],
            'home_comeback_rate': home_mom['comeback_rate'],
            'away_comeback_rate': away_mom['comeback_rate'],
            'home_draw_tendency': home_mom['draw_tendency'],
            'away_draw_tendency': away_mom['draw_tendency'],
            'draw_tendency_sum': home_mom['draw_tendency'] + away_mom['draw_tendency'],
            'home_blowout_win_pct': home_mom['blowout_win_pct'],
            'away_blowout_loss_pct': away_mom['blowout_loss_pct'],
            'home_shutout_loss_pct': home_mom['shutout_loss_pct'],
            'away_shutout_loss_pct': away_mom['shutout_loss_pct'],
        }

        # ---- NEW FAMILY 3: Poisson Expected Goals ----
        poisson_feats = poisson_tracker.get_features(ht, at)

        # ---- NEW FAMILY 4: Venue/Geography ----
        city = getattr(row, 'city', '')
        country = getattr(row, 'country', '')
        venue_feats = get_venue_features(city, country, ht, at)

        # ---- NEW FAMILY 5: Tournament Context ----
        home_tourn = tournament_tracker.get_features(ht)
        away_tourn = tournament_tracker.get_features(at)
        tournament_feats = {
            'home_wc_form': home_tourn['wc_form'],
            'away_wc_form': away_tourn['wc_form'],
            'wc_form_diff': home_tourn['wc_form'] - away_tourn['wc_form'],
            'home_competitive_form': home_tourn['competitive_form'],
            'away_competitive_form': away_tourn['competitive_form'],
            'home_big_game_factor': home_tourn['big_game_factor'],
            'away_big_game_factor': away_tourn['big_game_factor'],
            'big_game_diff': home_tourn['big_game_factor'] - away_tourn['big_game_factor'],
            'home_wc_experience': home_tourn['wc_experience'],
            'away_wc_experience': away_tourn['wc_experience'],
            'wc_experience_diff': home_tourn['wc_experience'] - away_tourn['wc_experience'],
        }

        # Combine everything
        features = {
            **elo_feats, **form_feats, **goal_feats, **h2h_feats, **context_feats,
            **goalscorer_feats, **momentum_feats, **poisson_feats,
            **venue_feats, **tournament_feats,
        }
        features['result'] = row.result
        features['date'] = date
        features['year'] = row.year
        features['home_team'] = ht
        features['away_team'] = at
        feature_rows.append(features)

        # ---- UPDATE STATE (post-match) ----
        ht_t.add_match(date, hs, as_)
        at_t.add_match(date, as_, hs)
        h2h.add_match(ht, at, hs, as_)
        poisson_tracker.add_match(ht, hs, as_)
        poisson_tracker.add_match(at, as_, hs)
        tournament_tracker.add_match(ht, tournament, date, hs, as_)
        tournament_tracker.add_match(at, tournament, date, as_, hs)

        # Update goalscorer tracker
        match_key = (date, ht, at)
        match_goals = gs_index.get(match_key, [])
        for g_team, scorer, minute_str, own_goal, penalty in match_goals:
            parsed_min = gs_tracker.parse_minute(minute_str)
            gs_tracker.add_goals(g_team, [(parsed_min, penalty, own_goal, scorer)])

        # Update momentum tracker
        ht_conceded_first = determine_conceded_first(match_goals, ht, hs, as_)
        at_conceded_first = determine_conceded_first(match_goals, at, as_, hs)
        momentum.add_match(ht, hs, as_, ht_conceded_first)
        momentum.add_match(at, as_, hs, at_conceded_first)

    df_features = pd.DataFrame(feature_rows)

    if verbose:
        non_meta = [c for c in df_features.columns
                    if c not in ['result', 'date', 'year', 'home_team', 'away_team', 'tournament_category']]
        print(f"\nFeature matrix: {df_features.shape[0]:,} rows x {len(non_meta)} features")

    return df_features, elo, team_trackers, h2h, gs_tracker, momentum, poisson_tracker, tournament_tracker


# =============================================================================
# FEATURE COLUMNS
# =============================================================================

ORIGINAL_FEATURES = [
    'home_elo', 'away_elo', 'elo_diff', 'elo_total',
    'home_tournament_elo', 'away_tournament_elo', 'tournament_elo_diff',
    'home_expected',
    'home_form_5', 'home_form_10', 'home_form_20',
    'away_form_5', 'away_form_10', 'away_form_20',
    'home_weighted_form_10', 'away_weighted_form_10',
    'form_diff_5', 'form_diff_10', 'weighted_form_diff',
    'home_goals_scored_avg_10', 'home_goals_conceded_avg_10',
    'away_goals_scored_avg_10', 'away_goals_conceded_avg_10',
    'home_goal_diff_avg_10', 'away_goal_diff_avg_10',
    'goal_diff_differential', 'attack_vs_defense',
    'h2h_win_rate', 'h2h_matches', 'h2h_goal_diff',
    'is_neutral', 'is_home', 'is_world_cup', 'is_continental', 'is_friendly',
    'home_days_rest', 'away_days_rest', 'rest_diff',
    'home_experience', 'away_experience',
]

NEW_GOALSCORER_FEATURES = [
    'home_scoring_depth', 'away_scoring_depth', 'scoring_depth_diff',
    'home_star_dependency', 'away_star_dependency',
    'home_penalty_ratio', 'away_penalty_ratio',
    'home_late_goal_ratio', 'away_late_goal_ratio', 'late_goal_diff',
    'home_first_half_ratio', 'away_first_half_ratio',
]

NEW_MOMENTUM_FEATURES = [
    'home_streak', 'away_streak', 'streak_diff',
    'home_unbeaten', 'away_unbeaten',
    'home_clean_sheet_pct', 'away_clean_sheet_pct',
    'home_comeback_rate', 'away_comeback_rate',
    'home_draw_tendency', 'away_draw_tendency', 'draw_tendency_sum',
    'home_blowout_win_pct', 'away_blowout_loss_pct',
    'home_shutout_loss_pct', 'away_shutout_loss_pct',
]

NEW_POISSON_FEATURES = [
    'home_lambda', 'away_lambda',
    'home_poisson_win', 'home_poisson_draw',
    'home_scoring_variance', 'away_scoring_variance',
    'home_overperformance', 'away_overperformance',
]

NEW_VENUE_FEATURES = [
    'altitude', 'is_high_altitude',
    'same_confederation', 'confed_strength_diff', 'is_intercontinental',
]

NEW_TOURNAMENT_FEATURES = [
    'home_wc_form', 'away_wc_form', 'wc_form_diff',
    'home_competitive_form', 'away_competitive_form',
    'home_big_game_factor', 'away_big_game_factor', 'big_game_diff',
    'home_wc_experience', 'away_wc_experience', 'wc_experience_diff',
]

ALL_FEATURES = (ORIGINAL_FEATURES + NEW_GOALSCORER_FEATURES + NEW_MOMENTUM_FEATURES +
                NEW_POISSON_FEATURES + NEW_VENUE_FEATURES + NEW_TOURNAMENT_FEATURES)


# =============================================================================
# ML EXPERIMENTS
# =============================================================================

def run_experiments(df_features):
    """Run ablation study: original features vs each new family vs all combined."""
    from sklearn.metrics import accuracy_score, classification_report
    from xgboost import XGBClassifier
    from lightgbm import LGBMClassifier
    from sklearn.preprocessing import LabelEncoder

    df_ml = df_features[df_features['year'] >= 1990].copy()

    # Time-based split
    train_mask = df_ml['year'] < 2020
    test_mask = df_ml['year'] >= 2020
    y_train = df_ml.loc[train_mask, 'result']
    y_test = df_ml.loc[test_mask, 'result']

    le = LabelEncoder()
    y_train_enc = le.fit_transform(y_train)
    y_test_enc = le.transform(y_test)

    print(f"\nTrain: {sum(train_mask):,}  Test: {sum(test_mask):,}")
    print("=" * 80)

    feature_sets = {
        'Original (37 features)': ORIGINAL_FEATURES,
        '+ Goalscorer Intelligence': ORIGINAL_FEATURES + NEW_GOALSCORER_FEATURES,
        '+ Momentum/Psychology': ORIGINAL_FEATURES + NEW_MOMENTUM_FEATURES,
        '+ Poisson Expected Goals': ORIGINAL_FEATURES + NEW_POISSON_FEATURES,
        '+ Venue/Geography': ORIGINAL_FEATURES + NEW_VENUE_FEATURES,
        '+ Tournament Context': ORIGINAL_FEATURES + NEW_TOURNAMENT_FEATURES,
        'ALL COMBINED': ALL_FEATURES,
    }

    results = {}

    for name, features in feature_sets.items():
        # Filter to features that exist in the dataframe
        available = [f for f in features if f in df_ml.columns]
        X_train = df_ml.loc[train_mask, available].fillna(0)
        X_test = df_ml.loc[test_mask, available].fillna(0)

        # XGBoost (our best performer)
        xgb = XGBClassifier(
            n_estimators=500, max_depth=6, learning_rate=0.05,
            subsample=0.8, colsample_bytree=0.8, min_child_weight=5,
            reg_alpha=0.1, reg_lambda=1.0, random_state=42,
            n_jobs=4, eval_metric='mlogloss',
        )
        xgb.fit(X_train, y_train_enc, eval_set=[(X_test, y_test_enc)], verbose=False)
        xgb_pred = le.inverse_transform(xgb.predict(X_test))
        xgb_acc = accuracy_score(y_test, xgb_pred)

        # LightGBM
        lgb = LGBMClassifier(
            n_estimators=500, max_depth=6, learning_rate=0.05,
            subsample=0.8, colsample_bytree=0.8, min_child_samples=20,
            reg_alpha=0.1, reg_lambda=1.0, random_state=42,
            n_jobs=4, verbose=-1,
        )
        lgb.fit(X_train, y_train)
        lgb_acc = accuracy_score(y_test, lgb.predict(X_test))

        results[name] = {'xgb': xgb_acc, 'lgb': lgb_acc, 'n_features': len(available)}

        print(f"\n{name} ({len(available)} features)")
        print(f"  XGBoost:  {xgb_acc:.2%}")
        print(f"  LightGBM: {lgb_acc:.2%}")

    # Final detailed report for best configuration
    print("\n" + "=" * 80)
    print("DETAILED RESULTS: ALL COMBINED")
    print("=" * 80)

    available = [f for f in ALL_FEATURES if f in df_ml.columns]
    X_train = df_ml.loc[train_mask, available].fillna(0)
    X_test = df_ml.loc[test_mask, available].fillna(0)

    xgb_final = XGBClassifier(
        n_estimators=800, max_depth=7, learning_rate=0.03,
        subsample=0.85, colsample_bytree=0.75, min_child_weight=5,
        reg_alpha=0.15, reg_lambda=1.5, random_state=42,
        n_jobs=4, eval_metric='mlogloss',
    )
    xgb_final.fit(X_train, y_train_enc, eval_set=[(X_test, y_test_enc)], verbose=False)
    final_pred = le.inverse_transform(xgb_final.predict(X_test))
    final_acc = accuracy_score(y_test, final_pred)

    print(f"\nFinal XGBoost (tuned): {final_acc:.2%}")
    print(classification_report(y_test, final_pred))

    # Feature importance for final model
    importance = pd.DataFrame({
        'feature': available,
        'importance': xgb_final.feature_importances_
    }).sort_values('importance', ascending=False)

    print("\nTop 20 Most Important Features:")
    print("-" * 50)
    for _, row in importance.head(20).iterrows():
        family = "NEW" if row['feature'] not in ORIGINAL_FEATURES else "orig"
        print(f"  [{family}] {row['feature']:<35} {row['importance']:.4f}")

    # Count new features in top 20
    new_in_top20 = sum(1 for _, r in importance.head(20).iterrows()
                       if r['feature'] not in ORIGINAL_FEATURES)
    print(f"\nNew features in top 20: {new_in_top20}/20")

    return results, xgb_final, le, importance


def run_random_split_experiment(df_features):
    """
    Also test with random split (apples-to-apples with baseline notebook).
    The baseline used random split, so we need this comparison too.
    """
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import accuracy_score
    from xgboost import XGBClassifier
    from sklearn.preprocessing import LabelEncoder

    df_ml = df_features[df_features['year'] >= 1990].copy()
    available = [f for f in ALL_FEATURES if f in df_ml.columns]

    X = df_ml[available].fillna(0)
    y = df_ml['result']

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    le = LabelEncoder()
    y_train_enc = le.fit_transform(y_train)
    y_test_enc = le.transform(y_test)

    xgb = XGBClassifier(
        n_estimators=800, max_depth=7, learning_rate=0.03,
        subsample=0.85, colsample_bytree=0.75, min_child_weight=5,
        reg_alpha=0.15, reg_lambda=1.5, random_state=42,
        n_jobs=4, eval_metric='mlogloss',
    )
    xgb.fit(X_train, y_train_enc, eval_set=[(X_test, y_test_enc)], verbose=False)
    pred = le.inverse_transform(xgb.predict(X_test))
    acc = accuracy_score(y_test, pred)

    print(f"\n{'='*80}")
    print("RANDOM SPLIT COMPARISON (apples-to-apples with baseline)")
    print(f"{'='*80}")
    print("  Baseline (old notebook):      59.0%")
    print(f"  Enhanced XGBoost (all feats):  {acc:.1%}")
    print(f"  Improvement:                  +{acc*100 - 59:.1f} pp")


# =============================================================================
# MAIN
# =============================================================================

if __name__ == '__main__':
    use_oracle = '--from-oracle' in sys.argv

    if use_oracle:
        df, gs = load_from_oracle()
    else:
        df, gs = load_from_csv()

    df_features, elo, team_trackers, h2h, gs_tracker, momentum, poisson_tracker, tourn_tracker = \
        build_features(df, gs)

    results, model, le, importance = run_experiments(df_features)
    run_random_split_experiment(df_features)

    # Save enhanced feature matrix for notebook use
    output_path = os.path.join(DATA_DIR, 'enhanced_features.parquet')
    df_features.to_parquet(output_path, index=False)
    print(f"\nSaved feature matrix to {output_path}")
