# ML Model Selection: From Decision Trees to Stacking Ensembles

## Overview

Predicting international football outcomes is a 3-class classification problem: Win, Draw, or Loss (from the home team's perspective). We tested 6 models in a deliberate progression from simple to complex, measuring each one's contribution. The final pipeline uses XGBoost as its primary model, with a stacking ensemble as the ceiling benchmark.

This document explains every model we tried, why we chose it, and what we learned from the progression.

## The Evaluation Framework

Before talking about models, the evaluation setup matters more than the model choice.

**Time-based split**: Train on matches before 2020, test on matches from 2020 onward. This is realistic. In production, you're always predicting the future from the past. A random 80/20 split would leak temporal patterns and inflate accuracy by 3-5 percentage points.

**Data range**: Only matches from 1990 onward are used for training. Pre-1990 football operates under different rules (back-pass rule changed in 1992, golden goal era, different substitution rules). Including 1950s matches adds noise, not signal.

**Primary metric**: Overall accuracy on the 3-class problem. We also tracked per-class precision/recall because the model's ability to predict draws is the hardest part and most diagnostic of quality.

## Model 1: Decision Tree

**Why**: Baseline sanity check. If a decision tree can't do better than random (33%) or naive majority-class prediction (~45%), the features have problems.

```python
DecisionTreeClassifier(max_depth=10, min_samples_leaf=20, random_state=42)
```

**Result**: ~54% accuracy

**What we learned**: The features carry real signal. Elo difference alone gets you to ~50%, so the tree is picking up on form and context features too. But decision trees overfit badly on tabular data this wide (92 features), even with depth limits. The decision boundaries are too rigid.

**Why we moved on**: Unstable. Small data perturbations produce wildly different trees. No probability calibration.

## Model 2: Random Forest

**Why**: The natural next step. Averaging 500 independent trees reduces variance without increasing bias much. Random forests are the standard "first serious model" for tabular classification.

```python
RandomForestClassifier(
    n_estimators=500, max_depth=15, min_samples_leaf=10,
    max_features='sqrt', random_state=42, n_jobs=-1
)
```

**Result**: ~57% accuracy

**What we learned**: 3-point jump over the single tree confirms the variance reduction is working. Feature importance rankings started showing Elo difference and form metrics as dominant. The forest struggles with draws (precision around 30-35%), which makes sense: draws are rare (~25% of outcomes) and the features that predict them are subtle.

**Why we moved on**: Random forests treat all 500 trees equally. They can't learn from their own mistakes. Boosting can.

## Model 3: XGBoost

**Why**: Gradient boosting builds trees sequentially, with each tree correcting the errors of the previous ensemble. XGBoost specifically handles missing values natively, supports regularization, and is fast. It's been the dominant algorithm on tabular data benchmarks since 2015.

```python
XGBClassifier(
    n_estimators=500, max_depth=6, learning_rate=0.05,
    subsample=0.8, colsample_bytree=0.8, min_child_weight=5,
    reg_alpha=0.1, reg_lambda=1.0, random_state=42,
    n_jobs=-1, eval_metric='mlogloss'
)
```

**Result**: ~59-60% accuracy

**What we learned**: The sequential error correction matters. XGBoost found interaction effects between features that the random forest missed, like the combination of Elo difference + momentum streak + tournament type. The `colsample_bytree=0.8` parameter (only use 80% of features per tree) acts as implicit feature selection, reducing noise from weaker features.

Key hyperparameter choices:
- `max_depth=6`: Deep enough to capture interactions, shallow enough to avoid memorizing specific matchups
- `learning_rate=0.05`: Conservative. Each tree contributes a small correction, so we need more trees but get better generalization
- `min_child_weight=5`: Prevents splits on tiny leaf nodes, which are usually noise in match data
- `reg_alpha=0.1, reg_lambda=1.0`: L1 + L2 regularization. L1 drives unimportant feature weights to zero. L2 smooths the remaining ones.

**Why we moved on**: We wanted to see if LightGBM's different tree-building strategy could find something XGBoost missed.

## Model 4: LightGBM

**Why**: LightGBM uses leaf-wise tree growth instead of XGBoost's level-wise approach. It grows the leaf with the highest loss reduction first, which can produce deeper, more specialized trees. Also 2-3x faster training on this dataset size.

```python
LGBMClassifier(
    n_estimators=500, max_depth=6, learning_rate=0.05,
    subsample=0.8, colsample_bytree=0.8, min_child_samples=20,
    reg_alpha=0.1, reg_lambda=1.0, random_state=42,
    n_jobs=-1, verbose=-1
)
```

**Result**: ~59-60% accuracy (comparable to XGBoost)

**What we learned**: On this dataset, XGBoost and LightGBM perform within 0.5 percentage points of each other. The dataset isn't large enough (tens of thousands, not millions) for LightGBM's speed advantage to matter. The leaf-wise vs level-wise distinction washes out at `max_depth=6`.

`min_child_samples=20` (LightGBM's equivalent of `min_child_weight`) is set higher than XGBoost's 5 because LightGBM's aggressive leaf-wise growth needs stronger regularization to avoid overfitting on small leaf populations.

**Why we kept both**: Since they're comparable, we use both in the ablation study and stacking ensemble. Different tree-growth strategies sometimes capture complementary patterns.

## Model 5: Tuned XGBoost

**Why**: After confirming XGBoost as the strongest single model, we tuned it more aggressively.

```python
XGBClassifier(
    n_estimators=800, max_depth=7, learning_rate=0.03,
    subsample=0.85, colsample_bytree=0.75, min_child_weight=5,
    reg_alpha=0.15, reg_lambda=1.5, random_state=42,
    n_jobs=-1, eval_metric='mlogloss'
)
```

Changes from the base XGBoost:
- **800 trees** (up from 500): More trees compensate for the lower learning rate
- **learning_rate=0.03** (down from 0.05): Smaller steps, better convergence
- **max_depth=7** (up from 6): One extra level of interaction capture
- **colsample_bytree=0.75** (down from 0.8): Slightly more aggressive feature subsampling
- **reg_lambda=1.5** (up from 1.0): Stronger L2 to compensate for the deeper trees

**Result**: ~60-61% accuracy

**What we learned**: The tuning squeezed out another 0.5-1 percentage point. The deeper trees (depth 7) helped with tournament context features, which involve multi-way interactions (is it a World Cup + knockout stage + intercontinental matchup?). Diminishing returns are visible: further tuning produced <0.1% gains.

## Model 6: Stacking Ensemble

**Why**: Stacking combines multiple base models through a meta-learner that learns which model to trust in which situations. If XGBoost is better at predicting wins and LightGBM is better at detecting draws, the meta-learner can blend them optimally.

```python
from sklearn.ensemble import StackingClassifier

estimators = [
    ('rf', RandomForestClassifier(n_estimators=300, max_depth=12, random_state=42, n_jobs=-1)),
    ('xgb', XGBClassifier(n_estimators=500, max_depth=6, learning_rate=0.05, random_state=42, n_jobs=-1)),
    ('lgb', LGBMClassifier(n_estimators=500, max_depth=6, learning_rate=0.05, random_state=42, n_jobs=-1, verbose=-1)),
]

stacking = StackingClassifier(
    estimators=estimators,
    final_estimator=LogisticRegression(max_iter=1000, random_state=42),
    cv=5, n_jobs=-1
)
```

**Result**: ~60-61% accuracy

**What we learned**: The stacking ensemble matches or barely exceeds the tuned XGBoost. This tells us the models are capturing largely the same signal, the features are the bottleneck, not the model architecture.

The meta-learner (logistic regression) is deliberately simple. Using a complex meta-learner on top of already-complex base models leads to overfitting on the meta-level.

## Why XGBoost Won

The tuned XGBoost is the production model for 2026 predictions. Here's why:

1. **Best single-model accuracy** (~60-61% on time-based split)
2. **Probability calibration**: XGBoost's softmax outputs are reasonably well-calibrated, meaning a 70% predicted win probability actually corresponds to roughly 70% empirical win rate
3. **Feature importance**: XGBoost's `feature_importances_` array cleanly ranks which features matter, enabling the ablation study
4. **Speed**: Predictions take milliseconds, important for simulating 10,000 tournament brackets
5. **Handles missing data**: Some features (like H2H records) are legitimately missing for team pairs that have never played

## The Accuracy Ceiling

Three-class international football prediction has a hard ceiling around 62-65% with pre-match features alone. Here's why:

- **Draws are inherently unpredictable**: ~25% of matches end in draws, but pre-match features can only predict them at ~35% precision. The difference between a 1-0 win and a 1-1 draw often comes down to a single moment of individual brilliance or error.
- **Squad selection is unknown pre-match**: Injuries, tactical surprises, and rotation aren't captured.
- **In-match dynamics**: Red cards, penalties, weather, refereeing decisions.

Our ~60-61% accuracy on a time-based split is competitive with published academic results on similar datasets. The baseline notebook achieved ~59% with a random split, which would inflate to roughly 56-57% on a time-based split. The enhanced features provide a genuine 3-4 percentage point improvement.

## Ablation Study Results

The ablation study tests each new feature family individually against the 37-feature baseline:

| Feature Set | Features | Accuracy | Delta |
|---|---|---|---|
| Original baseline | 40 | ~57-58% | -- |
| + Goalscorer Intelligence | 52 | ~58-59% | +1.0 pp |
| + Momentum/Psychology | 56 | ~58-59% | +1.0 pp |
| + Poisson Expected Goals | 48 | ~58-59% | +0.5 pp |
| + Venue/Geography | 45 | ~57-58% | +0.3 pp |
| + Tournament Context | 51 | ~58-59% | +0.8 pp |
| **ALL COMBINED** | **92** | **~60-61%** | **+3.0 pp** |

The combined improvement is larger than any single family's contribution, which confirms the feature families capture complementary signal. Goalscorer intelligence and momentum/psychology contribute the most individually. Venue/geography contributes least, probably because the Elo system already implicitly captures some geographic effects through home advantage.
