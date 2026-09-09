import pytest
import numpy as np
from pathlib import Path
from soccer_agent.inference.live import predict, _load_model


@pytest.fixture(scope="session")
def dummy_model_on_disk():
    """Swap a tiny sklearn pipeline into the live-predict load path.

    Preserves the real models/best_model.pkl by backing it up before the
    fixture runs and restoring afterwards. Without this, running the test
    suite would clobber the 92-feature production model with a 4-feature
    stub and silently break predict_match in the rest of the suite.
    """
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.preprocessing import LabelEncoder
    import joblib
    import shutil

    rng = np.random.default_rng(42)
    X = rng.standard_normal((300, 4)).astype(np.float32)
    y = rng.choice(["Win", "Draw", "Loss"], size=300)
    le = LabelEncoder().fit(y)
    clf = RandomForestClassifier(n_estimators=20, random_state=42).fit(X, le.transform(y))

    bundle = {"model": clf, "features": ["a", "b", "c", "d"], "classes_": list(le.classes_)}
    path = Path(__file__).resolve().parent.parent / "models" / "best_model.pkl"
    path.parent.mkdir(exist_ok=True)
    backup = path.with_suffix(".pkl.realbackup")
    if path.exists():
        shutil.copy2(path, backup)
    joblib.dump(bundle, path)
    _load_model.cache_clear()
    try:
        yield path
    finally:
        if backup.exists():
            shutil.move(str(backup), str(path))
        _load_model.cache_clear()


def test_predict_returns_normalized_probs(dummy_model_on_disk):
    p = predict({"a": 0.1, "b": -0.5, "c": 0.3, "d": 0.2}, "Spain", "Brazil")
    total = p.prob_home_win + p.prob_draw + p.prob_away_win
    assert abs(total - 1.0) < 1e-5
    assert p.source == "live"


def test_predict_team_with_no_features_works(dummy_model_on_disk):
    p = predict({}, "Andorra", "Spain")
    assert 0.0 <= p.prob_home_win <= 1.0
