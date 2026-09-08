"""Shared pytest fixtures for agentic_rag tests.

Provides fixtures for integration tests that need real services:
- Oracle DB (via docker-compose.test.yml or ORACLE_DB_* env vars)
- Ollama (local install or OLLAMA_HOST env var)
- Backend FastAPI server (subprocess)
- Gradio UI (subprocess)
- Playwright browser (sync API)

Integration tests are marked with @pytest.mark.integration and auto-skip
when their required service isn't reachable. Running `pytest` by default
runs the smoke suite; `pytest -m integration` runs the full stack.

Environment variables recognized:
    ORACLE_DB_USERNAME (default: SYSTEM)
    ORACLE_DB_PASSWORD (default: OraclePW1_)
    ORACLE_DB_DSN (default: localhost:1521/FREEPDB1)
    OLLAMA_HOST (default: http://127.0.0.1:11434)
    OLLAMA_TEST_MODEL (default: gemma3:270m)
    AGENTIC_RAG_BACKEND_URL (override the autostart backend)
    AGENTIC_RAG_GRADIO_URL (override the autostart gradio)
"""
from __future__ import annotations

import hashlib
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest
from langchain_core.embeddings import Embeddings

# ---------------------------------------------------------------------------
# Path setup: make src/ importable for all tests in this project.
# ---------------------------------------------------------------------------
_APP_ROOT = Path(__file__).resolve().parent.parent
_SRC = _APP_ROOT / "src"
if str(_APP_ROOT) not in sys.path:
    sys.path.insert(0, str(_APP_ROOT))
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))


# ---------------------------------------------------------------------------
# Oracle DB configuration helpers.
# ---------------------------------------------------------------------------
def _oracle_config_from_env() -> dict[str, str]:
    """Build an Oracle DB config dict from environment variables.

    Defaults match the docker-compose.test.yml setup so a developer who
    runs `docker compose -f docker-compose.test.yml up` and then `pytest`
    gets a working integration suite with zero extra config.
    """
    return {
        "ORACLE_DB_USERNAME": os.environ.get("ORACLE_DB_USERNAME", "SYSTEM"),
        "ORACLE_DB_PASSWORD": os.environ.get("ORACLE_DB_PASSWORD", "OraclePW1_"),
        "ORACLE_DB_DSN": os.environ.get("ORACLE_DB_DSN", "localhost:1521/FREEPDB1"),
    }


def _oracle_reachable(config: dict[str, str], timeout: float = 2.0) -> bool:
    """Quick TCP probe of the Oracle DSN host:port."""
    dsn = config.get("ORACLE_DB_DSN", "")
    # DSN format: host:port/service
    try:
        host_port, _service = dsn.split("/", 1)
        host, port_str = host_port.split(":", 1)
        port = int(port_str)
    except (ValueError, AttributeError):
        return False
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (TimeoutError, OSError):
        return False


# ---------------------------------------------------------------------------
# Deterministic fake embeddings: bypass Oracle's ONNX model requirement.
#
# The production code uses OracleEmbeddings with an in-DB ONNX model
# (ALL_MINILM_L12_V2) that has to be pre-loaded via a SQL procedure. Oracle
# Free containers don't ship with it. For integration tests we swap in a
# deterministic hash-based embedding so the vector store table / query
# pipeline is exercised without needing the real model.
# ---------------------------------------------------------------------------
class DeterministicEmbedding(Embeddings):
    """Minimal embedding function compatible with langchain_oracledb.OracleVS.

    Maps each input string to a 384-dim vector derived from its SHA-256 hash.
    Same input -> same vector, so similarity search is stable across runs.
    384 matches the ALL_MINILM_L12_V2 dimensionality so the vector column
    width is unchanged.
    """

    DIM = 384

    def _vec(self, text: str) -> list[float]:
        # Hash the text into enough bytes, then map each byte to [-1, 1].
        h = hashlib.sha256(text.encode("utf-8")).digest()
        # Expand to DIM bytes by repeating the digest.
        repeats = (self.DIM + len(h) - 1) // len(h)
        expanded = (h * repeats)[: self.DIM]
        return [(b / 127.5) - 1.0 for b in expanded]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._vec(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._vec(text)


# ---------------------------------------------------------------------------
# Session-scoped config patching: replace load_config() with one that pulls
# from environment variables, so src.OraDBVectorStore.__init__ doesn't need
# a real config.yaml to exist on disk.
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session", autouse=True)
def _patch_load_config():
    """Patch src.db_utils.load_config to read env vars for the test session.

    Autouse so every test that imports OraDBVectorStore picks up env-based
    config automatically. No-op if src.db_utils isn't importable (e.g. the
    smoke test session that stubs everything).
    """
    try:
        from src import db_utils  # noqa: F401
    except Exception:
        yield
        return

    from src import db_utils as _db_utils

    original = _db_utils.load_config
    _db_utils.load_config = _oracle_config_from_env
    try:
        yield
    finally:
        _db_utils.load_config = original


# ---------------------------------------------------------------------------
# Service availability fixtures.
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session")
def oracle_config() -> dict[str, str]:
    return _oracle_config_from_env()


@pytest.fixture(scope="session")
def oracle_available(oracle_config) -> bool:
    return _oracle_reachable(oracle_config)


@pytest.fixture(scope="session")
def oracle_vector_store(oracle_available, oracle_config):
    """Session-scoped OraDBVectorStore connected to a real Oracle DB.

    Uses DeterministicEmbedding so the test doesn't need the in-DB ONNX
    model. Skips the test gracefully if Oracle DB isn't reachable.
    """
    if not oracle_available:
        pytest.skip(
            f"Oracle DB not reachable at {oracle_config['ORACLE_DB_DSN']}. "
            "Start it with `docker compose -f docker-compose.test.yml up -d` "
            "or set ORACLE_DB_DSN/USERNAME/PASSWORD."
        )
    try:
        from src.OraDBVectorStore import OraDBVectorStore
    except ImportError as e:
        pytest.skip(f"OraDBVectorStore import failed: {e}")

    store = OraDBVectorStore(embedding_function=DeterministicEmbedding())
    yield store
    try:
        store.connection.close()
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Ollama fixtures.
# ---------------------------------------------------------------------------
OLLAMA_TEST_MODEL = os.environ.get("OLLAMA_TEST_MODEL", "gemma3:270m")


@pytest.fixture(scope="session")
def ollama_host() -> str:
    return os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")


@pytest.fixture(scope="session")
def ollama_available(ollama_host) -> bool:
    try:
        import urllib.request
        with urllib.request.urlopen(f"{ollama_host}/api/tags", timeout=2) as r:
            return r.status == 200
    except Exception:
        return False


@pytest.fixture(scope="session")
def ollama_test_model(ollama_available, ollama_host) -> str:
    """Ensure the test model is pulled. Returns the model name to use."""
    if not ollama_available:
        pytest.skip(
            f"Ollama not reachable at {ollama_host}. "
            "Start it with `ollama serve` or set OLLAMA_HOST."
        )
    import json
    import urllib.request

    # Check if model is already present.
    try:
        with urllib.request.urlopen(f"{ollama_host}/api/tags", timeout=5) as r:
            tags = json.loads(r.read())
        present = any(m.get("name", "").startswith(OLLAMA_TEST_MODEL) for m in tags.get("models", []))
    except Exception:
        present = False

    if not present:
        # Pull the model. This may take a while on first run.
        import subprocess as sp
        pull = sp.run(
            ["ollama", "pull", OLLAMA_TEST_MODEL],
            env={**os.environ, "OLLAMA_HOST": ollama_host},
            capture_output=True,
            text=True,
            timeout=600,
        )
        if pull.returncode != 0:
            pytest.skip(f"Failed to pull {OLLAMA_TEST_MODEL}: {pull.stderr}")

    return OLLAMA_TEST_MODEL


# ---------------------------------------------------------------------------
# Backend + Gradio subprocess fixtures.
# ---------------------------------------------------------------------------
def _wait_for_http(url: str, timeout: float = 60.0) -> bool:
    import urllib.request
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as r:
                if r.status < 500:
                    return True
        except Exception:
            pass
        time.sleep(0.5)
    return False


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="session")
def backend_server(oracle_available, ollama_available):
    """Launch the FastAPI backend as a subprocess for integration tests.

    Returns the base URL, e.g. 'http://127.0.0.1:8765'. Skips if required
    services aren't up. If AGENTIC_RAG_BACKEND_URL is set, uses that
    instead of spawning.
    """
    override = os.environ.get("AGENTIC_RAG_BACKEND_URL")
    if override:
        yield override.rstrip("/")
        return

    if not oracle_available:
        pytest.skip("Oracle DB required for backend")
    if not ollama_available:
        pytest.skip("Ollama required for backend")

    port = _free_port()
    env = {**os.environ, **_oracle_config_from_env()}
    proc = subprocess.Popen(
        [sys.executable, "run_app.py", "--api-only", "--api-port", str(port)],
        cwd=str(_APP_ROOT),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    url = f"http://127.0.0.1:{port}"
    try:
        if not _wait_for_http(f"{url}/v1/health", timeout=90):
            proc.terminate()
            out, _ = proc.communicate(timeout=5)
            pytest.skip(f"Backend failed to start:\n{out.decode(errors='ignore')[-2000:]}")
        yield url
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()


@pytest.fixture(scope="session")
def gradio_server(backend_server):
    """Launch the Gradio UI as a subprocess. Depends on backend_server."""
    override = os.environ.get("AGENTIC_RAG_GRADIO_URL")
    if override:
        yield override.rstrip("/")
        return

    port = _free_port()
    env = {**os.environ, **_oracle_config_from_env()}
    proc = subprocess.Popen(
        [sys.executable, "run_app.py", "--gradio", "--gradio-port", str(port)],
        cwd=str(_APP_ROOT),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    url = f"http://127.0.0.1:{port}"
    try:
        if not _wait_for_http(url, timeout=90):
            proc.terminate()
            out, _ = proc.communicate(timeout=5)
            pytest.skip(f"Gradio failed to start:\n{out.decode(errors='ignore')[-2000:]}")
        yield url
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()


# ---------------------------------------------------------------------------
# Playwright fixtures (sync API).
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session")
def playwright_browser():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        pytest.skip("playwright not installed. `pip install playwright && playwright install chromium`")

    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=True)
        except Exception as e:
            pytest.skip(f"Failed to launch chromium: {e}. Run `playwright install chromium`")
        try:
            yield browser
        finally:
            browser.close()


@pytest.fixture
def playwright_page(playwright_browser):
    context = playwright_browser.new_context()
    page = context.new_page()
    try:
        yield page
    finally:
        context.close()


# ---------------------------------------------------------------------------
# Marker registration happens in pyproject.toml.
# ---------------------------------------------------------------------------
