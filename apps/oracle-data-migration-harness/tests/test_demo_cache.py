import importlib


def test_cache_hit_returns_payload(tmp_path, monkeypatch):
    monkeypatch.setenv("DEMO_CACHE_PATH", str(tmp_path / "demo_cache.json"))

    import data_migration_harness.app as app_module

    app_module = importlib.reload(app_module)
    app_module.save_demo_cache("mongo", "test question", {"text": "cached"})
    assert app_module.demo_cache_lookup("mongo", "test question") == {"text": "cached"}


def test_cache_miss_returns_none(tmp_path, monkeypatch):
    monkeypatch.setenv("DEMO_CACHE_PATH", str(tmp_path / "demo_cache.json"))

    import data_migration_harness.app as app_module

    app_module = importlib.reload(app_module)
    assert app_module.demo_cache_lookup("oracle", "definitely not cached") is None
