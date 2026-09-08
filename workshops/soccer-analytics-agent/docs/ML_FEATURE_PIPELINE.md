# ML Feature Pipeline Notes

This workshop's predictions come from the same enhanced Reto Enseña 4.0 pipeline used in `enhanced_features.py`, `notebooks/world_cup_enhanced.ipynb`, and the runtime `FeatureRuntime` tools. The final model artifact (`models/best_model.pkl`) declares **92 features**, and `scripts/verify.py` checks that the artifact still exposes all 92 before the workshop is considered ready.

![92-feature ML pipeline diagram](assets/ml_feature_pipeline.png)

## Data flow at a glance

1. **Canonical input data**: `results.csv`, `goalscorers.csv`, and `shootouts.csv` from the Kaggle international football results dataset.
2. **Oracle load**: `scripts/setup_db.py` loads the CSVs into `MATCH_RESULTS`, `GOALSCORERS`, `SHOOTOUTS`, and analytical views such as `VW_TEAM_STATISTICS`.
3. **Chronological replay**: every tracker reads only pre-match state before a row is emitted, then updates after the result. This is the main data-leakage guard.
4. **92-feature row**: feature families are concatenated into one numeric row per match.
5. **Model training/inference**: the artifact is a three-class XGBoost-style classifier for `Win`, `Draw`, and `Loss` probabilities. `predict_match` builds the same feature row live for hypothetical/current matchups.
6. **Post-inference retrieval**: bulk predictions are loaded into `PREDICCIONES_FINAL`, then `scripts/load_langchain_vectors.py` turns predictions and football facts into LangChain `OracleVS` documents in `SOCCER_LANGCHAIN_DOCS` using `langchain-oracledb`.

## Elo scoring system

The Elo tracker starts every team at **1500**, replays matches chronologically, and maintains both a global rating and tournament-category-specific ratings.

### Expected score

```text
E_home = 1 / (1 + 10^(-(R_home - R_away + HA) / 400))
```

- `R_home`, `R_away`: current pre-match ratings.
- `HA`: home-advantage bonus, **100 Elo points** on non-neutral venues and `0` on neutral venues.
- `400`: standard Elo scaling constant.

### Rating update

```text
R_new = R_old + K * G * (S_actual - S_expected)
```

- `S_actual`: `1.0` for a win, `0.5` for a draw, `0.0` for a loss.
- `K`: match-importance factor.
- `G`: goal-difference multiplier.

### K-factors

| Tournament category | K-factor | Notes |
|---|---:|---|
| FIFA World Cup | 60 | Highest-stakes international matches. |
| Continental championship | 50 | Euros, Copa América, AFCON, Asian Cup, Gold Cup, Confederations Cup, etc. |
| Qualifier / Nations League / default competitive | 40 | Competitive but below finals-stage intensity. |
| Friendly | 20 | Lowest weight; lineups and intensity are less reliable. |

### Goal-difference multiplier

| Goal difference | Multiplier |
|---:|---:|
| 0–1 | 1.0 |
| 2 | 1.5 |
| 3 | 1.75 |
| 4+ | `1.75 + (GD - 3) / 8` |

Large margins matter, but with diminishing returns.

### Elo-derived features — 8

| Feature | Meaning |
|---|---|
| `home_elo`, `away_elo` | Global pre-match ratings. |
| `elo_diff`, `elo_total` | Rating gap and combined match quality proxy. |
| `home_expected` | Elo-implied home result expectation. |
| `home_tournament_elo`, `away_tournament_elo` | Category-specific Elo ratings. |
| `tournament_elo_diff` | Tournament-category rating gap. |

## Feature families in the final 92-feature model

| Family | Count | Source | What it captures |
|---|---:|---|---|
| Original baseline: Elo, form/goals, H2H, context | 40 | `results.csv` | Long-term quality, recent trajectory, pair history, venue/tournament/rest context. |
| Goalscorer intelligence | 12 | `goalscorers.csv` | How teams score: scoring depth, star dependency, penalties, late goals, first-half share. |
| Momentum / psychology | 16 | `results.csv` + `goalscorers.csv` | Streaks, unbeaten runs, clean sheets, comebacks, draw tendency, blowout/shutout behavior. |
| Poisson expected goals | 8 | `results.csv` | Goal-rate lambdas, Poisson win/draw probabilities, scoring variance, over/underperformance. |
| Venue / geography | 5 | match metadata + lookup tables | Altitude, confederation effects, intercontinental matchup flag. |
| Tournament context | 11 | `results.csv` | World Cup form, competitive form, big-game factor, World Cup experience. |
| **Total** | **92** |  |  |

## Exact feature names by family

### Original baseline — 40

- Elo: `home_elo`, `away_elo`, `elo_diff`, `elo_total`, `home_tournament_elo`, `away_tournament_elo`, `tournament_elo_diff`, `home_expected`.
- Form: `home_form_5`, `home_form_10`, `home_form_20`, `away_form_5`, `away_form_10`, `away_form_20`, `home_weighted_form_10`, `away_weighted_form_10`, `form_diff_5`, `form_diff_10`, `weighted_form_diff`.
- Goal statistics: `home_goals_scored_avg_10`, `home_goals_conceded_avg_10`, `away_goals_scored_avg_10`, `away_goals_conceded_avg_10`, `home_goal_diff_avg_10`, `away_goal_diff_avg_10`, `goal_diff_differential`, `attack_vs_defense`.
- Head-to-head: `h2h_win_rate`, `h2h_matches`, `h2h_goal_diff`.
- Match context: `is_neutral`, `is_home`, `is_world_cup`, `is_continental`, `is_friendly`, `home_days_rest`, `away_days_rest`, `rest_diff`, `home_experience`, `away_experience`.

### Goalscorer intelligence — 12

`home_scoring_depth`, `away_scoring_depth`, `scoring_depth_diff`, `home_star_dependency`, `away_star_dependency`, `home_penalty_ratio`, `away_penalty_ratio`, `home_late_goal_ratio`, `away_late_goal_ratio`, `late_goal_diff`, `home_first_half_ratio`, `away_first_half_ratio`.

### Momentum / psychology — 16

`home_streak`, `away_streak`, `streak_diff`, `home_unbeaten`, `away_unbeaten`, `home_clean_sheet_pct`, `away_clean_sheet_pct`, `home_comeback_rate`, `away_comeback_rate`, `home_draw_tendency`, `away_draw_tendency`, `draw_tendency_sum`, `home_blowout_win_pct`, `away_blowout_loss_pct`, `home_shutout_loss_pct`, `away_shutout_loss_pct`.

### Poisson expected goals — 8

`home_lambda`, `away_lambda`, `home_poisson_win`, `home_poisson_draw`, `home_scoring_variance`, `away_scoring_variance`, `home_overperformance`, `away_overperformance`.

### Venue / geography — 5

`altitude`, `is_high_altitude`, `same_confederation`, `confed_strength_diff`, `is_intercontinental`.

### Tournament context — 11

`home_wc_form`, `away_wc_form`, `wc_form_diff`, `home_competitive_form`, `away_competitive_form`, `home_big_game_factor`, `away_big_game_factor`, `big_game_diff`, `home_wc_experience`, `away_wc_experience`, `wc_experience_diff`.

## Why the agent tools mirror the feature families

The final chat agent exposes the same pipeline as tools so a user can ask for both the prediction and the evidence behind it:

| Runtime tool | Feature-family source |
|---|---|
| `get_elo` | `FootballElo` — global and tournament Elo. |
| `get_team_form` | `TeamTracker` — rolling form, weighted form, goals. |
| `get_h2h` | `H2HTracker` — pair-specific history. |
| `get_momentum` | `MomentumTracker` — psychological/momentum features. |
| `get_poisson_xg` | `PoissonTracker` — statistical goal model. |
| `get_tournament_context` | `TournamentTracker` — big-game and World Cup context. |
| `predict_match` | Builds all 92 features and runs live inference. |
| `hybrid_retrieve` | Retrieves post-inference prediction/fact documents from the LangChain OracleVS store. |

The important workshop claim is therefore falsifiable: a final answer can show the live 92-feature prediction and retrieve the corresponding cached prediction/fact evidence from Oracle through `langchain-oracledb`.
