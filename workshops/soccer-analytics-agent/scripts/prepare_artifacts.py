#!/usr/bin/env python3
"""Ensure workshop model artifacts exist under models/.

The hub workshop ships production artifacts, and this script keeps the
bootstrap deterministic if they are replaced, removed, or intentionally
retrained:

1. Use existing files in models/ when they look real.
2. Copy cached retraining artifacts from test_retrain/ when available.
3. Otherwise train from the loaded Oracle dataset and promote the artifacts.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

import joblib
import pandas as pd

REPO = Path(__file__).resolve().parent.parent
MODELS = REPO / "models"
CACHE = REPO / "test_retrain"

MODEL = MODELS / "best_model.pkl"
PREDICTIONS = MODELS / "predictions.parquet"

CACHED_MODEL = CACHE / "best_model.pkl"
CACHED_PREDICTIONS = CACHE / "predictions.parquet"

MIN_MODEL_BYTES = 1_000_000
MIN_PREDICTION_ROWS = 2_500


def _model_ready(path: Path) -> bool:
    if not path.exists() or path.stat().st_size < MIN_MODEL_BYTES:
        return False
    try:
        bundle = joblib.load(path)
    except Exception:
        return False
    return isinstance(bundle, dict) and len(bundle.get("features", [])) == 92


def _predictions_ready(path: Path) -> bool:
    if not path.exists():
        return False
    try:
        df = pd.read_parquet(path, columns=["home_team"])
    except Exception:
        return False
    return len(df) >= MIN_PREDICTION_ROWS


def _copy_if_ready(src: Path, dst: Path, check) -> bool:
    if not check(src):
        return False
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    print(f"Copied {src.relative_to(REPO)} -> {dst.relative_to(REPO)}")
    return True


def _train() -> None:
    print("Training workshop model artifacts from Oracle data...")
    subprocess.run(
        [sys.executable, str(REPO / "test_retrain" / "train_real_model.py")],
        cwd=REPO,
        check=True,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--force-retrain",
        action="store_true",
        help="Ignore existing artifacts and retrain from Oracle data.",
    )
    args = parser.parse_args()

    MODELS.mkdir(parents=True, exist_ok=True)

    if args.force_retrain:
        _train()

    if not _model_ready(MODEL):
        _copy_if_ready(CACHED_MODEL, MODEL, _model_ready)
    if not _predictions_ready(PREDICTIONS):
        _copy_if_ready(CACHED_PREDICTIONS, PREDICTIONS, _predictions_ready)

    if not _model_ready(MODEL) or not _predictions_ready(PREDICTIONS):
        _train()
        _copy_if_ready(CACHED_MODEL, MODEL, _model_ready)
        _copy_if_ready(CACHED_PREDICTIONS, PREDICTIONS, _predictions_ready)

    failures = []
    if not _model_ready(MODEL):
        failures.append("models/best_model.pkl is missing or not a 92-feature model")
    if not _predictions_ready(PREDICTIONS):
        failures.append(
            f"models/predictions.parquet is missing or has fewer than "
            f"{MIN_PREDICTION_ROWS} rows"
        )

    if failures:
        for failure in failures:
            print(f"ERROR: {failure}", file=sys.stderr)
        return 1

    pred_rows = len(pd.read_parquet(PREDICTIONS, columns=["home_team"]))
    print("Workshop artifacts ready:")
    print(f"  {MODEL.relative_to(REPO)} ({MODEL.stat().st_size / 1024:.0f} KB, 92 features)")
    print(f"  {PREDICTIONS.relative_to(REPO)} ({pred_rows:,} prediction rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
