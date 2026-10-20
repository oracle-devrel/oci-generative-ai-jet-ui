"""Configuration: settings from the environment and .env, their defaults, and refused values."""

import pytest

from golestan_code_mcp.config import (
    MODEL_URL,
    PROJECT_ROOT,
    ConfigError,
    environment,
    load,
    max_file_bytes,
    memory_model,
    model_cache,
    model_url,
    feedback_cap,
    feedback_half_life,
    search_candidates,
    text_weight,
    vector_weight,
    repos_dir,
    vendor_dirs,
)


def test_model_settings_defaults_and_overrides(tmp_path):
    assert model_url({}) == MODEL_URL and MODEL_URL.endswith("/all_MiniLM_L12_v2.onnx")
    assert model_url({"CCCTX_MODEL_URL": " https://example.test/m.onnx "}) == "https://example.test/m.onnx"
    assert model_cache({}) == (PROJECT_ROOT / ".cache/models").resolve()
    assert model_cache({"CCCTX_MODEL_CACHE": str(tmp_path)}) == tmp_path.resolve()

SECRET = "s3cr3t-Pa55"
BASE = {"DB_USER": "ccctx", "DB_PASSWORD": SECRET}


def test_defaults_applied():
    cfg = load(BASE, dotenv_path=None)
    assert (cfg.db_host, cfg.db_port, cfg.db_service) == ("localhost", 1521, "FREEPDB1")
    assert cfg.dsn == "localhost:1521/FREEPDB1"
    assert repos_dir({}) == (PROJECT_ROOT / "../ccctx-repos").resolve()


def test_all_missing_and_blank_named_together():
    with pytest.raises(ConfigError) as e:
        load({"DB_PASSWORD": "   "}, dotenv_path=None)
    assert "DB_USER" in str(e.value) and "DB_PASSWORD" in str(e.value)


@pytest.mark.parametrize("port", ["abc", "0", "70000"])
def test_bad_port_named(port):
    with pytest.raises(ConfigError, match="DB_PORT"):
        load({**BASE, "DB_PORT": port}, dotenv_path=None)


def test_password_never_shown():
    cfg = load(BASE, dotenv_path=None)
    assert SECRET not in repr(cfg) and SECRET not in str(cfg)
    with pytest.raises(ConfigError) as e:
        load({**BASE, "DB_PORT": "x"}, dotenv_path=None)
    assert SECRET not in str(e.value)


def test_absolute_repos_dir_kept(tmp_path):
    assert repos_dir({"CCCTX_REPOS_DIR": str(tmp_path / "my repos")}) == (tmp_path / "my repos").resolve()


def test_environment_wins_over_dotenv(tmp_path, monkeypatch):
    dotenv = tmp_path / ".env"
    dotenv.write_text("DB_USER=from_file\nDB_PASSWORD=file_pw\n")
    monkeypatch.setenv("DB_USER", "from_env")
    cfg = load(dotenv_path=dotenv)
    assert cfg.db_user == "from_env"
    assert cfg.db_password  # filled from the file or the environment


def test_ingest_limits_defaults_and_overrides():
    assert max_file_bytes({}) == 1048576
    assert max_file_bytes({"CCCTX_MAX_FILE_BYTES": "2048"}) == 2048
    assert vendor_dirs({}) == {"vendor", "node_modules", "third_party"}
    assert vendor_dirs({"CCCTX_VENDOR_DIRS": " deps , ,lib "}) == {"deps", "lib"}
    assert vendor_dirs({"CCCTX_VENDOR_DIRS": ""}) == set()


@pytest.mark.parametrize("bad", ["0", "-5", "1MB"])
def test_bad_max_file_bytes_named(bad):
    with pytest.raises(ConfigError, match="CCCTX_MAX_FILE_BYTES"):
        max_file_bytes({"CCCTX_MAX_FILE_BYTES": bad})


def test_search_settings_defaults_and_overrides():
    assert (search_candidates({}), text_weight({}), vector_weight({})) == (100, 1.0, 1.0)
    env = {"CCCTX_SEARCH_CANDIDATES": "250", "CCCTX_TEXT_WEIGHT": "2.5", "CCCTX_VECTOR_WEIGHT": " 0.5 "}
    assert (search_candidates(env), text_weight(env), vector_weight(env)) == (250, 2.5, 0.5)


@pytest.mark.parametrize(("accessor", "name", "bad"), [
    (search_candidates, "CCCTX_SEARCH_CANDIDATES", "0"),
    (search_candidates, "CCCTX_SEARCH_CANDIDATES", "many"),
    (text_weight, "CCCTX_TEXT_WEIGHT", "-1"),
    (vector_weight, "CCCTX_VECTOR_WEIGHT", "heavy"),
    (vector_weight, "CCCTX_VECTOR_WEIGHT", "nan"),
])
def test_bad_search_settings_named(accessor, name, bad):
    with pytest.raises(ConfigError, match=name):
        accessor({name: bad})


def test_memory_model_unset_or_blank_means_none():
    assert memory_model({}) is None
    assert memory_model({"CCCTX_MEMORY_MODEL": "   "}) is None


def test_memory_model_settings_and_hidden_key():
    m = memory_model({"CCCTX_MEMORY_MODEL": " anthropic/claude-sonnet-5-5 ", "CCCTX_MEMORY_MODEL_BASE": "http://x:1",
                      "CCCTX_MEMORY_MODEL_KEY": SECRET})
    assert (m.model, m.base, m.key) == ("anthropic/claude-sonnet-5-5", "http://x:1", SECRET)
    assert SECRET not in repr(m)
    bare = memory_model({"CCCTX_MEMORY_MODEL": "ollama/qwen3"})
    assert (bare.model, bare.base, bare.key) == ("ollama/qwen3", None, None)


def test_memory_model_environment_wins_over_dotenv(tmp_path, monkeypatch):
    dotenv = tmp_path / ".env"
    dotenv.write_text("CCCTX_MEMORY_MODEL=from/dotenv\n")
    monkeypatch.delenv("CCCTX_MEMORY_MODEL", raising=False)
    assert memory_model(environment(dotenv)).model == "from/dotenv"
    monkeypatch.setenv("CCCTX_MEMORY_MODEL", "from/env")
    assert memory_model(environment(dotenv)).model == "from/env"


def test_feedback_settings_defaults_and_overrides():
    assert (feedback_cap({}), feedback_half_life({})) == (0.2, 30.0)
    assert feedback_cap({"CCCTX_FEEDBACK_CAP": "0"}) == 0.0 and feedback_cap({"CCCTX_FEEDBACK_CAP": " 1 "}) == 1.0
    assert feedback_half_life({"CCCTX_FEEDBACK_HALF_LIFE_DAYS": "7.5"}) == 7.5


@pytest.mark.parametrize(("accessor", "name", "bad"), [
    (feedback_cap, "CCCTX_FEEDBACK_CAP", "-0.1"),
    (feedback_cap, "CCCTX_FEEDBACK_CAP", "1.5"),
    (feedback_cap, "CCCTX_FEEDBACK_CAP", "lots"),
    (feedback_cap, "CCCTX_FEEDBACK_CAP", "nan"),
    (feedback_half_life, "CCCTX_FEEDBACK_HALF_LIFE_DAYS", "0"),
    (feedback_half_life, "CCCTX_FEEDBACK_HALF_LIFE_DAYS", "-30"),
    (feedback_half_life, "CCCTX_FEEDBACK_HALF_LIFE_DAYS", "month"),
])
def test_bad_feedback_settings_named(accessor, name, bad):
    with pytest.raises(ConfigError, match=name):
        accessor({name: bad})
