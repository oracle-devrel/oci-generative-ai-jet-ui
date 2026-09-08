# The Elo Rating System: Quantifying International Football Strength

## Overview

At the core of our World Cup 2026 prediction engine sits a custom Elo rating system adapted from [eloratings.net](https://www.eloratings.net/). Every national team starts at 1500 and drifts up or down after each match. The system processes 48,943 international matches chronologically, so by the time we reach 2026, each team's rating encodes decades of competitive history into a single number.

This document explains how the system works, why each design decision matters, and what the resulting ratings actually capture.

## The Core Formula

Elo ratings follow a simple loop: predict, observe, correct.

Before each match, the system computes an **expected score** for the home team:

```
E_home = 1 / (1 + 10^(-(R_home - R_away + HA) / 400))
```

Where:
- `R_home` and `R_away` are the current ratings
- `HA` is a home advantage bonus (100 points for non-neutral venues, 0 for neutral)
- 400 is the standard Elo scaling constant

After the match, ratings update based on how far the actual result deviated from the prediction:

```
R_new = R_old + K * G * (S_actual - S_expected)
```

The actual score `S` is 1.0 for a win, 0.5 for a draw, 0.0 for a loss. If a 1700-rated team was expected to beat a 1400-rated team 85% of the time and actually wins, the rating barely moves. If the underdog pulls off the upset, both ratings shift significantly.

## K-Factors: Not All Matches Are Equal

The K-factor controls how much a single result can move a team's rating. We use tournament-specific K-factors because a World Cup final should carry more weight than a random friendly in March.

| Tournament Type | K-Factor | Rationale |
|---|---|---|
| FIFA World Cup | 60 | Highest stakes, strongest squads, maximum effort |
| Continental (Euros, Copa America, AFCON, etc.) | 50 | Regional championships, near-World Cup intensity |
| Qualifiers / Nations League | 40 | Competitive matches but with rotation and experimentation |
| Friendlies | 20 | Lowest weight, often experimental lineups |

The classification logic maps tournament names to categories using substring matching:

```python
TOURNAMENT_CATEGORIES = {
    'FIFA World Cup': 'world_cup',
    'Copa America': 'continental',
    'UEFA Euro': 'continental',
    'African Cup of Nations': 'continental',
    'AFC Asian Cup': 'continental',
    'CONCACAF Gold Cup': 'continental',
    'Oceania Nations Cup': 'continental',
    'Confederations Cup': 'continental',
    'UEFA Nations League': 'qualifier',
}
```

Anything with "qualification" or "qualifier" in the name gets K=40. Anything with "friendly" gets K=20. Everything else defaults to K=40 (qualifier tier), which is a conservative fallback.

## Goal Difference Multiplier

A 1-0 win and a 5-0 win shouldn't update ratings by the same amount. The goal difference multiplier `G` amplifies the update for convincing victories:

| Goal Difference | Multiplier |
|---|---|
| 0-1 | 1.0 |
| 2 | 1.5 |
| 3 | 1.75 |
| 4+ | 1.75 + (GD - 3) / 8 |

The formula uses diminishing returns for large margins. Going from 3-0 to 7-0 adds progressively less information, since that gap usually reflects squad depth rather than a meaningful quality difference.

```python
def goal_diff_multiplier(self, gd):
    gd = abs(gd)
    if gd <= 1: return 1.0
    elif gd == 2: return 1.5
    elif gd == 3: return 1.75
    else: return 1.75 + (gd - 3) / 8
```

## Home Advantage

Home advantage in international football is real and measurable. Teams playing at home benefit from crowd support, familiar climate, no travel fatigue, and (sometimes) referee bias.

We model this as a flat +100 rating bonus for the home team in non-neutral venues. On neutral ground (tournament finals, for example), the bonus drops to 0.

```python
ha = 0 if is_neutral else self.HOME_ADVANTAGE  # HOME_ADVANTAGE = 100
```

The 100-point bonus translates to roughly a 14% increase in expected win probability for an evenly-matched pair. That aligns well with empirical home win rates in international football (~55-58% for home wins in non-neutral matches).

## Tournament-Specific Ratings

Beyond the global Elo, we maintain **separate rating tracks per tournament category**. A team's World Cup Elo updates only from World Cup matches. Their continental Elo updates only from continental championships.

This captures teams that "show up" for big tournaments but coast through qualifiers (or vice versa). The `update()` method runs both calculations in parallel:

```python
# Global update
self.ratings[ht] += k * g * (h_actual - home_exp)
self.ratings[at] += k * g * (a_actual - (1 - home_exp))

# Tournament-category-specific update
self.tournament_ratings[cat][ht] += k * g * (h_actual - home_t_exp)
self.tournament_ratings[cat][at] += k * g * (a_actual - (1 - home_t_exp))
```

This gives us 8 Elo-derived features per match:

| Feature | Description |
|---|---|
| `home_elo` | Home team's global Elo before the match |
| `away_elo` | Away team's global Elo before the match |
| `elo_diff` | Rating gap (home - away) |
| `elo_total` | Combined rating (proxy for match quality) |
| `home_expected` | Predicted home win probability |
| `home_tournament_elo` | Home team's category-specific Elo |
| `away_tournament_elo` | Away team's category-specific Elo |
| `tournament_elo_diff` | Category-specific rating gap |

## Data Leakage Prevention

A critical design choice: features are extracted from the **pre-match state** of each tracker, then the trackers update **after** the features are recorded.

```python
# EXTRACT features (pre-match state)
elo_feats = elo.update(ht, at, hs, as_, tournament, is_neutral, date)

# ... build all features from current tracker states ...

# UPDATE state (post-match)
ht_t.add_match(date, hs, as_)
at_t.add_match(date, as_, hs)
```

The `elo.update()` call is a slight exception: it returns the pre-match ratings as features but internally updates to post-match values. This is handled correctly because the returned dictionary captures the ratings *before* the internal update modifies them.

Without this discipline, the model would "see" future information during training and produce inflated accuracy numbers that collapse on real predictions.

## What Elo Captures (and What It Misses)

**Captures well:**
- Long-term team quality trajectories
- The weight of different competition tiers
- Home advantage effects
- Margin of victory significance

**Misses entirely:**
- Player-level changes (injuries, transfers, retirements)
- Tactical evolution within a team
- Manager appointments and style shifts
- Squad depth and fatigue during tournaments

These gaps are exactly why we built 4 additional feature families on top of Elo. The rating system provides a strong baseline, roughly 55% accuracy on its own, but the ceiling is real. Breaking past 60% required looking at goalscoring patterns, psychological momentum, expected goals models, and tournament-specific behavior.

## Validation

The Elo system was validated by comparing its rankings against FIFA's official rankings for recent periods. The correlation is strong (Spearman rho > 0.90), with the main divergences coming from FIFA's confederate weighting scheme, which our system handles differently through the K-factor tiers.

The top-10 Elo ratings heading into 2026 generally align with consensus expectations: Argentina, France, Brazil, England, Spain, Germany, Netherlands, Portugal, Belgium, and Italy cluster near the top, with the exact ordering depending on recent results.
