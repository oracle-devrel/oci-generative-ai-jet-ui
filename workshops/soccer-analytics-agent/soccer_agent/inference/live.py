"""Live (on-demand) prediction using the trained model on disk."""

from __future__ import annotations

import functools
from pathlib import Path
from typing import Any

import joblib
import numpy as np

from soccer_agent.inference.bulk import Prediction

MODEL_PATH = Path(__file__).resolve().parent.parent.parent / "models" / "best_model.pkl"


@functools.lru_cache(maxsize=1)
def _load_model() -> Any:
    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"{MODEL_PATH} not found. Run the training notebook or "
            "scripts/load_predictions.py with --retrain."
        )
    return joblib.load(MODEL_PATH)


def predict(features: dict[str, float],
            home_team: str, away_team: str,
            model_version: str = "live") -> Prediction:
    """Predict win/draw/loss probabilities from a feature dict."""
    bundle = _load_model()
    model = bundle["model"] if isinstance(bundle, dict) else bundle
    feat_names = bundle.get("features") if isinstance(bundle, dict) else None
    if feat_names is None:
        feat_names = sorted(features.keys())

    x = np.array([[features.get(f, 0.0) for f in feat_names]], dtype=np.float32)
    probs = model.predict_proba(x)[0]

    classes = list(bundle.get("classes_", ["Draw", "Loss", "Win"])) if isinstance(bundle, dict) else ["Draw", "Loss", "Win"]
    idx = {c: i for i, c in enumerate(classes)}
    return Prediction(
        home_team=home_team, away_team=away_team,
        prob_home_win=float(probs[idx["Win"]]),
        prob_draw=float(probs[idx["Draw"]]),
        prob_away_win=float(probs[idx["Loss"]]),
        model_version=model_version, source="live",
    )
