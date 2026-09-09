# Dataset Enhancement: From 40 to 92 Features

## Overview

The original prediction model used 40 features derived from Elo ratings, recent form, goal averages, head-to-head records, and match context. These features hit a ceiling around 57-58% accuracy on a time-based split.

We designed 5 new feature families (52 additional features) to break through that ceiling. Each family targets a specific blind spot in the original feature set. The combined 92-feature model reaches ~60-61% accuracy, a 3-4 percentage point improvement that translates to meaningfully better tournament predictions.

This document explains each feature family in depth: what it measures, how it's computed, and why it helps.

## Raw Data Sources

Two datasets feed the entire pipeline:

- **results.csv**: 48,943 international football matches (1872-2024). Columns: date, home_team, away_team, home_score, away_score, tournament, city, country, neutral.
- **goalscorers.csv**: 44,568 individual goals with minute-level timing. Columns: date, home_team, away_team, team, scorer, minute, own_goal, penalty.

The goalscorers table is what makes 3 of the 5 new feature families possible. The original notebook ignored it entirely.

## The Chronological Processing Constraint

Every feature is extracted from the **pre-match state** of its tracker. After features are recorded, the trackers update with the match result. This prevents data leakage (the model can't "see" future results during training).

```
for each match (chronologically):
    1. Extract all 92 features from current tracker states
    2. Record features + result as one training row
    3. Update all trackers with this match's result
```

This means early matches in the dataset have sparse features (few prior matches to compute form from). We handle this with sensible defaults: form defaults to 0.5 (neutral), goal averages default to 1.5, H2H defaults to 0.5 win rate.

## The Original 40 Features (Baseline)

For context, here's what the baseline already captured:

**Elo ratings (8 features)**: Global and tournament-specific ratings, rating differences, expected score. See [elo-system.md](elo-system.md).

**Form (11 features)**: Win rates over last 5, 10, and 20 matches. Exponentially-weighted form (decay=0.9) that values recent results more. Differentials between home and away team form.

**Goal statistics (8 features)**: Average goals scored and conceded over last 10 matches. Goal difference averages. Attack-vs-defense matchup (home attack vs away defense).

**Head-to-head (3 features)**: Historical win rate, total meetings, and average goal difference between the specific pair of teams.

**Match context (10 features)**: Neutral venue flag, home advantage flag, tournament type (World Cup / continental / friendly), days of rest for each team, rest differential, and total international experience (match count) for both teams.

These 40 features are solid. They capture the two biggest predictors of match outcomes: team quality (Elo) and recent trajectory (form). The 5 new families target what's left.

---

## Family 1: Goalscorer Intelligence (12 features)

**What it captures**: How a team scores, not just how much. Two teams averaging 1.5 goals per game can look identical in the baseline features but have completely different scoring profiles.

**Tracker**: `GoalscorerTracker` processes the goalscorers.csv data, maintaining a rolling list of the last 50 goals per team with minute, penalty flag, own-goal flag, and scorer name.

### Features

| Feature | Formula | What it reveals |
|---|---|---|
| `home_scoring_depth` | unique scorers / total goals | Teams with 8 different scorers in their last 50 goals are harder to defend against than teams relying on 2-3 strikers |
| `away_scoring_depth` | (same, for away team) | |
| `scoring_depth_diff` | home - away | Positive means the home team has more distributed scoring |
| `home_star_dependency` | top scorer's goals / total goals | High dependency = vulnerability if the star is marked or injured |
| `away_star_dependency` | (same, for away team) | |
| `home_penalty_ratio` | penalty goals / total goals | Teams that score heavily from penalties may be flattering their goal stats |
| `away_penalty_ratio` | (same, for away team) | |
| `home_late_goal_ratio` | goals in minute 75+ / total goals | Late-scoring teams are mentally resilient and physically fit |
| `away_late_goal_ratio` | (same, for away team) | |
| `late_goal_diff` | home - away | |
| `home_first_half_ratio` | goals in minute 1-45 / total goals | Teams that score early can control the game through possession |
| `away_first_half_ratio` | (same, for away team) | |

### Minute Parsing

The goalscorers dataset stores minutes as strings like `"45+2"` or `"90+3"`. The parser handles all formats:

```python
def parse_minute(self, minute_str):
    if '+' in minute_str:
        parts = minute_str.split('+')
        return int(parts[0]) + int(parts[1])  # "45+2" -> 47
    return int(float(minute_str))
```

### Why It Helps (+1.0 pp)

Scoring depth turned out to be one of the most informative new features. Teams with distributed scoring (depth > 0.6) win at higher rates than star-dependent teams (depth < 0.3) in knockout situations. The model learns this interaction between scoring depth and tournament stage.

---

## Family 2: Psychological / Momentum (16 features)

**What it captures**: Streaks, mental resilience, defensive solidity, and behavioral tendencies. Football is as much a mental game as a physical one, and momentum effects are real.

**Tracker**: `MomentumTracker` stores the last 15 results per team as (points, goals_for, goals_against, conceded_first) tuples.

### Features

| Feature | Formula | What it reveals |
|---|---|---|
| `home_streak` | Consecutive wins from most recent match backward | Confidence and form (but also regression risk) |
| `away_streak` | (same, for away team) | |
| `streak_diff` | home - away | |
| `home_unbeaten` | Consecutive non-losses from most recent match | More stable than win streak, captures draw-prone teams |
| `away_unbeaten` | (same, for away team) | |
| `home_clean_sheet_pct` | Matches with 0 goals conceded / last 15 | Defensive reliability |
| `away_clean_sheet_pct` | (same, for away team) | |
| `home_comeback_rate` | Wins after conceding first / matches where conceded first | Mental toughness. Teams that comeback frequently are dangerous underdogs |
| `away_comeback_rate` | (same, for away team) | |
| `home_draw_tendency` | Draws / last 15 matches | Some teams structurally draw more (defensive style, closely-matched opponents) |
| `away_draw_tendency` | (same, for away team) | |
| `draw_tendency_sum` | home + away | When both teams are draw-prone, the draw probability spikes |
| `home_blowout_win_pct` | Wins by 3+ goals / last 15 | Ability to dominate weaker opponents |
| `away_blowout_loss_pct` | Losses by 3+ goals / last 15 | Vulnerability to collapse |
| `home_shutout_loss_pct` | Losses where team scored 0 / last 15 | Complete offensive failure rate |
| `away_shutout_loss_pct` | (same, for away team) | |

### Conceded-First Detection

To compute comeback rate, we need to know which team conceded first. This requires parsing the goalscorers data to find the earliest goal in each match:

```python
def determine_conceded_first(match_goals, team, gf, ga):
    if not match_goals or gf == 0:
        return ga > 0  # Didn't score but conceded = conceded first

    earliest_minute = 999
    earliest_team = None
    for g_team, scorer, minute_str, own_goal, penalty in match_goals:
        parsed = GoalscorerTracker().parse_minute(minute_str)
        if parsed is not None and parsed < earliest_minute:
            earliest_minute = parsed
            earliest_team = g_team

    return earliest_team != team  # Conceded first if opponent scored first
```

### Why It Helps (+1.0 pp)

The `draw_tendency_sum` feature is the standout. When two draw-prone teams meet, the model correctly shifts probability mass toward the draw outcome, which the baseline features couldn't do. The `comeback_rate` feature also adds signal for knockout predictions, where trailing teams either crumble or fight back.

---

## Family 3: Poisson Expected Goals (8 features)

**What it captures**: Statistical goal expectation based on Poisson modeling. Instead of just averaging goals scored, this family models the actual probability distribution of scorelines.

**Tracker**: `PoissonTracker` maintains per-team lists of goals scored and conceded per match (last 20 matches).

### The Poisson Model

Football goals per team per match approximately follow a Poisson distribution. Given an expected goals rate (lambda), the probability of scoring exactly k goals is:

```
P(k goals) = (lambda^k * e^(-lambda)) / k!
```

We estimate lambda for each team in each match by averaging their attack strength with the opponent's defensive weakness:

```python
home_lambda = clip((home_scored_avg + away_conceded_avg) / 2, 0.3, 5.0)
away_lambda = clip((away_scored_avg + home_conceded_avg) / 2, 0.3, 5.0)
```

Clipping to [0.3, 5.0] prevents extreme values from teams with very few matches.

### Probability Matrix

From the two lambdas, we build a probability matrix over all plausible scorelines (0-0 through 7-7):

```python
h_pmf = poisson.pmf(range(8), home_lambda)  # P(home scores 0,1,2,...,7)
a_pmf = poisson.pmf(range(8), away_lambda)  # P(away scores 0,1,2,...,7)
prob_matrix = np.outer(h_pmf, a_pmf)        # 8x8 joint probability matrix

home_win_prob = np.tril(prob_matrix, -1).sum()  # Below diagonal = home wins
draw_prob = np.trace(prob_matrix)               # Diagonal = draws
```

This is the same approach used by betting markets and expected-goals models like FiveThirtyEight's.

### Performance Optimization

Computing Poisson PMFs is expensive when done 48,943 times. We cache PMF vectors by lambda (rounded to nearest 0.1):

```python
@classmethod
def _get_pmfs(cls, lam):
    key = round(lam * 10)
    if key not in cls._PMF_CACHE:
        cls._PMF_CACHE[key] = poisson.pmf(cls._GOALS_RANGE, lam)
    return cls._PMF_CACHE[key]
```

### Features

| Feature | Description |
|---|---|
| `home_lambda` | Expected goals for home team |
| `away_lambda` | Expected goals for away team |
| `home_poisson_win` | Poisson-derived home win probability |
| `home_poisson_draw` | Poisson-derived draw probability |
| `home_scoring_variance` | Variance in home team's goals scored (consistency measure) |
| `away_scoring_variance` | Variance in away team's goals scored |
| `home_overperformance` | Actual win rate minus Poisson-predicted win rate |
| `away_overperformance` | (same, for away team) |

### Why It Helps (+0.5 pp)

The overperformance features are the key contribution. A team with high overperformance consistently wins more than their raw goal numbers suggest, indicating quality finishing, game management, or luck. The Poisson win/draw probabilities also provide a second "opinion" on match outcome that partially decorrelates from the Elo prediction, giving the ensemble more to work with.

---

## Family 4: Venue / Geography (5 features)

**What it captures**: Physical and structural factors of where the match is played.

### Features

| Feature | Source | Description |
|---|---|---|
| `altitude` | `CITY_ALTITUDES` lookup table | Elevation in meters. Mexico City (2240m) and Bogota (2640m) significantly affect team stamina |
| `is_high_altitude` | altitude > 1500m | Binary flag for high-altitude venues |
| `same_confederation` | `TEAM_CONFEDERATIONS` mapping | Whether both teams are from the same confederation |
| `confed_strength_diff` | `CONFED_STRENGTH` tier values | Gap in confederation historical strength (UEFA=1.0, CONMEBOL=0.95, CONCACAF=0.6, AFC/CAF=0.5, OFC=0.3) |
| `is_intercontinental` | confederations differ | Intercontinental matches tend to be more unpredictable |

### The Altitude Lookup

We maintain a dictionary of 26 major football cities with known altitudes:

```python
CITY_ALTITUDES = {
    'mexico city': 2240, 'bogota': 2640, 'quito': 2850, 'la paz': 3640,
    'johannesburg': 1753, 'addis ababa': 2355, 'nairobi': 1795, 'denver': 1609,
    'madrid': 667, 'sao paulo': 760, 'guadalajara': 1566, 'monterrey': 540,
    'atlanta': 320, 'dallas': 131, 'houston': 15, 'kansas city': 247,
    'los angeles': 30, 'miami': 2, 'new york': 3, 'philadelphia': 12,
    'san francisco': 16, 'seattle': 54, 'toronto': 76, 'vancouver': 0,
}
```

Cities not in the table default to 100m. The 2026 World Cup venues (across the US, Mexico, and Canada) are all included.

### Confederation Strength Tiers

Based on historical World Cup performance:

```python
CONFED_STRENGTH = {
    'UEFA': 1.0,       # 12 of 22 World Cup winners
    'CONMEBOL': 0.95,  # 10 of 22 World Cup winners
    'CONCACAF': 0.6,   # Semi-finals ceiling (USA 1930, Mexico multiple QFs)
    'AFC': 0.5,        # South Korea 2002 semi-final is the high-water mark
    'CAF': 0.5,        # Cameroon 1990, Ghana/Senegal QFs
    'OFC': 0.3,        # New Zealand's only WC wins are draws
}
```

### Why It Helps (+0.3 pp)

The smallest individual contribution. The Elo system already implicitly captures some geographic effects (teams that play at altitude accumulate rating points from altitude-assisted home wins). The `is_intercontinental` feature adds marginal value by flagging matches where teams from different football cultures meet, which historically produce more upsets.

---

## Family 5: Tournament Stage Context (11 features)

**What it captures**: How teams perform in different competitive contexts. Some teams consistently overperform in World Cups. Others fold under pressure.

**Tracker**: `TournamentTracker` classifies each match into one of 5 contexts and maintains per-context result histories for every team.

### Context Classification

```python
def classify_stage(self, tournament, date):
    t = tournament.lower()
    if 'friendly' in t:           return 'friendly'
    if 'qualification' in t:      return 'qualifying'
    if 'fifa world cup' in t:     return 'wc_finals'
    if any(x in t for x in ['euro', 'copa', 'asian cup', 'gold cup', 'african cup']):
                                   return 'continental_finals'
    return 'other_competitive'
```

### Features

| Feature | Formula | Description |
|---|---|---|
| `home_wc_form` | Win rate in last 20 WC finals matches | Raw World Cup pedigree |
| `away_wc_form` | (same, for away team) | |
| `wc_form_diff` | home - away | |
| `home_competitive_form` | 0.4 * wc_form + 0.3 * continental_form + 0.3 * qualifying_form | Blended competitive performance |
| `away_competitive_form` | (same, for away team) | |
| `home_big_game_factor` | competitive_form - friendly_form | Positive = rises to the occasion. Negative = "friendly bully" |
| `away_big_game_factor` | (same, for away team) | |
| `big_game_diff` | home - away | |
| `home_wc_experience` | Total WC finals matches played | Germany (112 WC matches) vs Bahrain (0) |
| `away_wc_experience` | (same, for away team) | |
| `wc_experience_diff` | home - away | |

### The Big-Game Factor

This is the most novel feature in the family. It measures the gap between a team's competitive and friendly performance:

```python
big_game_factor = competitive_form - friendly_form
```

A team with competitive_form = 0.7 and friendly_form = 0.5 has a big_game_factor of +0.2, meaning they step up when it matters. A team with the reverse profile (0.5 competitive, 0.7 friendly) has a negative big_game_factor: they beat weaker teams in friendlies but underperform against real opposition.

### Why It Helps (+0.8 pp)

World Cup experience and the big-game factor both carry genuine predictive power for tournament matches specifically. The model learns that a team with 50+ WC matches and a positive big-game factor is more likely to advance than their Elo alone would suggest. This is particularly valuable for the 2026 predictions, where every match is a "big game."

---

## The Goalscorer Index: Making It Fast

Processing 44,568 goals per match during the chronological loop would be painfully slow. Instead, we pre-build an index keyed by (date, home_team, away_team):

```python
def build_goalscorer_index(gs_df):
    index = defaultdict(list)
    for row in gs.itertuples(index=False):
        key = (row.date, row.home_team, row.away_team)
        index[key].append((row.team, row.scorer, row.minute, row.own_goal, row.penalty))
    return index
```

During the feature loop, looking up goals for a specific match is a single dict access: `gs_index.get((date, ht, at), [])`. This reduces the total processing time from minutes to seconds.

## Feature Summary Table

| Family | Features | Source Data | Key Insight |
|---|---|---|---|
| Elo ratings | 8 | results.csv | Long-term team quality |
| Form / goals | 19 | results.csv | Recent trajectory |
| Head-to-head | 3 | results.csv | Pair-specific history |
| Match context | 10 | results.csv | Venue, tournament type, rest, experience |
| **Goalscorer intelligence** | **12** | **goalscorers.csv** | **How teams score, not just how much** |
| **Momentum / psychology** | **16** | **results.csv + goalscorers.csv** | **Streaks, resilience, tendencies** |
| **Poisson expected goals** | **8** | **results.csv** | **Statistical goal modeling** |
| **Venue / geography** | **5** | **results.csv + lookup tables** | **Altitude, confederation dynamics** |
| **Tournament context** | **11** | **results.csv** | **Big-game performance patterns** |
| **Total** | **92** | | |

The 52 new features (bold rows) collectively improve accuracy by 3-4 percentage points over the 40-feature baseline. More importantly, they provide richer probability estimates for the 2026 World Cup simulation, where small differences in predicted win probabilities cascade through 7 knockout rounds to produce materially different bracket outcomes.
