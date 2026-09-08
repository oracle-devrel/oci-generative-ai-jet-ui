"""Retrain the soccer prediction model on the real Kaggle dataset.

Runs in isolation under test_retrain/. Does NOT touch models/ until the
caller promotes artifacts. Reuses enhanced_features.build_features().
"""

from __future__ import annotations

import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, log_loss
from sklearn.preprocessing import LabelEncoder
from xgboost import XGBClassifier

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from enhanced_features import ALL_FEATURES, build_features  # noqa: E402
from soccer_agent.db import get_connection  # noqa: E402

OUT = Path(__file__).parent
OUT.mkdir(parents=True, exist_ok=True)


def load_from_oracle() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Same shape as enhanced_features.load_from_oracle but using soccer_agent.db."""
    with get_connection() as conn:
        df = pd.read_sql(
            """SELECT DATE_RW, HOME_TEAM, AWAY_TEAM, HOME_SCORE, AWAY_SCORE,
                      TOURNAMENT, CITY, COUNTRY, NEUTRAL
                 FROM MATCH_RESULTS
                WHERE HOME_SCORE IS NOT NULL AND AWAY_SCORE IS NOT NULL
                ORDER BY DATE_RW""",
            conn,
        )
        gs = pd.read_sql(
            """SELECT DATE_RW, HOME_TEAM, AWAY_TEAM, TEAM, SCORER, MINUTE,
                      OWN_GOAL, PENALTY
                 FROM GOALSCORERS
                ORDER BY DATE_RW""",
            conn,
        )

    df.columns = [c.lower() for c in df.columns]
    gs.columns = [c.lower() for c in gs.columns]
    df = df.rename(columns={"date_rw": "date"})
    gs = gs.rename(columns={"date_rw": "date"})

    df["date"] = pd.to_datetime(df["date"])
    if df["neutral"].dtype != bool:
        df["neutral"] = df["neutral"].map({"TRUE": True, "FALSE": False}).fillna(False).astype(bool)
    df["result"] = np.where(
        df["home_score"] > df["away_score"], "Win",
        np.where(df["home_score"] < df["away_score"], "Loss", "Draw"),
    )
    df["year"] = df["date"].dt.year
    df = df.sort_values("date").reset_index(drop=True)
    gs["date"] = pd.to_datetime(gs["date"])
    print(f"Loaded {len(df):,} played matches, {len(gs):,} goals from Oracle")
    return df, gs


def main() -> None:
    df, gs = load_from_oracle()

    print("\nBuilding features (this takes a few minutes on 49k matches)...")
    df_feat, *_trackers = build_features(df, gs, verbose=True)

    df_ml = df_feat[df_feat["year"] >= 1990].copy()
    train_mask = df_ml["year"] < 2020
    test_mask = df_ml["year"] >= 2020
    available = [f for f in ALL_FEATURES if f in df_ml.columns]
    print(f"\nUsing {len(available)} features out of {len(ALL_FEATURES)} declared in ALL_FEATURES")

    X_train = df_ml.loc[train_mask, available].fillna(0)
    X_test = df_ml.loc[test_mask, available].fillna(0)
    y_train = df_ml.loc[train_mask, "result"]
    y_test = df_ml.loc[test_mask, "result"]

    le = LabelEncoder()
    y_train_enc = le.fit_transform(y_train)
    y_test_enc = le.transform(y_test)
    print(f"Train: {len(X_train):,}  Test: {len(X_test):,}")
    print(f"Classes: {list(le.classes_)}")

    clf = XGBClassifier(
        n_estimators=400, max_depth=6, learning_rate=0.05,
        subsample=0.85, colsample_bytree=0.8, min_child_weight=5,
        reg_alpha=0.1, reg_lambda=1.0, random_state=42,
        n_jobs=-1, eval_metric="mlogloss", tree_method="hist",
    )
    clf.fit(X_train, y_train_enc, eval_set=[(X_test, y_test_enc)], verbose=False)
    proba = clf.predict_proba(X_test)
    pred = le.inverse_transform(clf.predict(X_test))
    acc = accuracy_score(y_test, pred)
    ll = log_loss(y_test_enc, proba)
    print(f"\nAccuracy: {acc:.4f}   log-loss: {ll:.4f}")

    bundle = {
        "model": clf,
        "features": available,
        "classes_": [str(c) for c in le.classes_],
        "label_encoder": le,
        "trained_on": "kaggle martj42 international football results (real)",
        "n_train": int(len(X_train)),
        "n_test": int(len(X_test)),
        "accuracy": float(acc),
        "log_loss": float(ll),
    }
    joblib.dump(bundle, OUT / "best_model.pkl")
    print(f"Saved {OUT / 'best_model.pkl'} ({(OUT / 'best_model.pkl').stat().st_size / 1024:.0f} KB)")

    print("\nBuilding predictions.parquet for recent unique matchups...")
    recent = df_ml[df_ml["year"] >= 2022].copy()
    recent["pair"] = recent[["home_team", "away_team"]].apply(
        lambda r: tuple(sorted([r["home_team"], r["away_team"]])), axis=1,
    )
    recent_unique = recent.drop_duplicates("pair", keep="last")
    Xp = recent_unique[available].fillna(0)
    probs = clf.predict_proba(Xp)

    classes_list = list(le.classes_)
    idx_win = classes_list.index("Win")
    idx_draw = classes_list.index("Draw")
    idx_loss = classes_list.index("Loss")

    preds_df = pd.DataFrame({
        "home_team": recent_unique["home_team"].values,
        "away_team": recent_unique["away_team"].values,
        "prob_home_win": probs[:, idx_win],
        "prob_draw": probs[:, idx_draw],
        "prob_away_win": probs[:, idx_loss],
        "model_version": "v2-real",
    })
    preds_df.to_parquet(OUT / "predictions.parquet", index=False)
    print(f"Saved {OUT / 'predictions.parquet'} with {len(preds_df):,} unique matchups")
    print("\nSample predictions:")
    print(preds_df.head(5).to_string(index=False))


if __name__ == "__main__":
    main()
