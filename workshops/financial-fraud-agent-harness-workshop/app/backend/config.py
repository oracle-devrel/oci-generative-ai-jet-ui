"""Environment-driven configuration. Mirrors the notebook's §2.4 credentials cell
and §3.x DSN setup, but reads from .env / process env instead of getpass prompts."""

import os
import sys
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))


# Flask
FLASK_PORT = int(os.environ.get("FLASK_PORT", "8000"))
FLASK_DEBUG = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
FLASK_SECRET_KEY = os.environ.get("FLASK_SECRET_KEY", "dev-secret-change-me")

# Oracle DB
SYS_USER = os.environ.get("ORACLE_SYS_USER", "sys")
SYS_PASS = os.environ.get("ORACLE_SYS_PASS", "OraclePwd_2025")
SYS_DSN = os.environ.get("ORACLE_DSN", "localhost:1521/FREEPDB1")

AGENT_USER = os.environ.get("ORACLE_AGENT_USER", "AGENT")
AGENT_PASS = os.environ.get("ORACLE_AGENT_PASS", "AgentPwd_2025")

DEMO_USER = os.environ.get("ORACLE_DEMO_USER", "FINANCE")
DEMO_PASS = os.environ.get("ORACLE_DEMO_PASS", "FinancePwd_2025")

# In-DB ONNX embedder model name (registered in notebook §3.4)
ONNX_EMBED_MODEL = os.environ.get("ONNX_EMBED_MODEL", "ALL_MINILM_L12_V2")
ONNX_EMBED_DIM = int(os.environ.get("ONNX_EMBED_DIM", "384"))

# LLM
# Lanes (agent/llm.py -> shared ModelRouter in oci_key_rotation.py):
#   grok-phx -> grok-chi -> gptoss-chi. Lanes with missing env are skipped.
LLM_MODEL = os.environ.get("LLM_MODEL", "xai.grok-4.3").strip()

# oci_key_rotation.py lives at the workshop repo root (shared with the notebook).
_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if os.path.exists(os.path.join(_ROOT, "oci_key_rotation.py")) and _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


# ----- OCI credential normalization ----------------------------------------
# The notebook (§3.3) hard-codes
#     https://inference.generativeai.<region>.oci.oraclecloud.com/openai/v1
# and prompts for a single API key. In production .env files we've seen two
# kinds of damage that quietly break OCI:
#   1. Endpoint missing the OpenAI-compatible suffix (`/openai/v1`).
#      The OpenAI SDK appends `/chat/completions` to whatever you give it, so
#      a bare host hits the wrong URL and 404s before auth even runs.
#   2. API key field with multiple keys joined by " and " or "," — the dotenv
#      parser treats the whole string as one secret, and OCI rejects it as
#      malformed.
# Normalize both at import time so downstream code sees clean values.

def _normalize_oci_endpoint(url: str) -> str:
    url = (url or "").strip().rstrip("/")
    if not url:
        return url
    # Already pointing at one of OCI GenAI's accepted OpenAI-compatible paths.
    if url.endswith("/openai/v1") or url.endswith("/20231130/openai"):
        return url
    if url.endswith("/openai"):
        return url + "/v1"
    if url.endswith("/20231130"):
        return url + "/openai"
    # Anything else (bare host, custom path, …) — append the canonical
    # /openai/v1 suffix the notebook uses.
    return url + "/openai/v1"


def _normalize_api_key(raw: str) -> str:
    """Pick the first non-empty key out of a value that may contain multiple
    keys joined by ' and ' / ',' / ';' / whitespace."""
    if not raw:
        return ""
    s = raw.strip()
    # Split on ' and ' first (most likely human-pasted separator), then
    # fall back to comma / semicolon / whitespace.
    for sep in [" and ", ",", ";"]:
        if sep in s:
            s = s.split(sep, 1)[0].strip()
            break
    return s.split()[0] if s else ""


OCI_GENAI_API_KEY_RAW = os.environ.get("OCI_GENAI_API_KEY", "")
OCI_GENAI_ENDPOINT_RAW = os.environ.get(
    "OCI_GENAI_ENDPOINT",
    "https://inference.generativeai.us-phoenix-1.oci.oraclecloud.com/openai/v1",
)
OCI_GENAI_ENDPOINT = _normalize_oci_endpoint(OCI_GENAI_ENDPOINT_RAW)

# Write cleaned values back so the shared router (load_lanes reads os.environ)
# sees them. Fallback (Chicago) endpoint is normalized the same way.
os.environ["OCI_GENAI_ENDPOINT"] = OCI_GENAI_ENDPOINT
for _name in ["OCI_GENAI_API_KEY", "OCI_GENAI_API_KEY_2", "OCI_GENAI_API_KEY_3",
              "OCI_GENAI_API_KEY_4", "OCI_GENAI_API_KEY_5", "OCI_GENAI_API_KEY_6",
              "OCI_GENAI_FALLBACK_API_KEY", "OCI_GENAI_FALLBACK_API_KEY_2",
              "OCI_GENAI_FALLBACK_API_KEY_3", "OCI_GENAI_FALLBACK_API_KEY_4",
              "OCI_GENAI_FALLBACK_API_KEY_5", "OCI_GENAI_FALLBACK_API_KEY_6"]:
    if os.environ.get(_name):
        os.environ[_name] = _normalize_api_key(os.environ[_name])
if os.environ.get("OCI_GENAI_FALLBACK_ENDPOINT"):
    os.environ["OCI_GENAI_FALLBACK_ENDPOINT"] = _normalize_oci_endpoint(
        os.environ["OCI_GENAI_FALLBACK_ENDPOINT"])

# Capture whether the .env had to be cleaned, so build_llm_client can note it.
_k1 = os.environ.get("OCI_GENAI_API_KEY", "")
OCI_API_KEY_WAS_CLEANED = bool(OCI_GENAI_API_KEY_RAW) and (_k1 != OCI_GENAI_API_KEY_RAW.strip())
OCI_ENDPOINT_WAS_CLEANED = bool(OCI_GENAI_ENDPOINT_RAW) and (OCI_GENAI_ENDPOINT != OCI_GENAI_ENDPOINT_RAW.strip().rstrip("/"))

# Tavily — gives the agent real-time web/news access. When the key is unset
# the search_tavily tool returns a friendly error instead of crashing.
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY", "").strip()

# Agent loop
AGENT_MAX_ITERATIONS = int(os.environ.get("AGENT_MAX_ITERATIONS", "8"))
AGENT_BUDGET_SECONDS = float(os.environ.get("AGENT_BUDGET_SECONDS", "60"))

# Maximum context window for the configured LLM (override via env). Used by
# the front-end's token meter to render a "X / max" bar. Reasonable defaults
# below cover common GPT / Claude / Grok lines.
def _default_model_max(model: str) -> int:
    m = (model or "").lower()
    if m.startswith("gpt-5") or m.startswith("gpt-4.1") or m.startswith("o1") or m.startswith("o3"):
        return 200_000
    if m.startswith("gpt-4o"):
        return 128_000
    if "claude" in m:
        return 200_000
    if "grok" in m:
        return 131_072
    return 128_000


LLM_MODEL_MAX_TOKENS = int(os.environ.get("LLM_MODEL_MAX_TOKENS", str(_default_model_max(LLM_MODEL))))

# OAMP scoping (every memory carries these)
USER_ID = os.environ.get("EDA_USER_ID", "enterprise-operator")
AGENT_ID = os.environ.get("EDA_AGENT_ID", "enterprise-data-agent")


# Live data simulator — streams new banking activity into FINANCE so the app
# feels like a production system under real-time load. Set LIVE_FEED=false to
# disable entirely; the front-end can also pause/resume it at runtime.
LIVE_FEED = os.environ.get("LIVE_FEED", "true").strip().lower() in ("1", "true", "yes", "on")
LIVE_FEED_INTERVAL = float(os.environ.get("LIVE_FEED_INTERVAL", "6"))    # mean seconds between events at peak hours
LIVE_FEED_MAX = int(os.environ.get("LIVE_FEED_MAX", "300"))              # most live rows kept at once
LIVE_FEED_TTL_MIN = int(os.environ.get("LIVE_FEED_TTL_MIN", "25"))       # age at which live rows are purged
LIVE_FEED_FLAG_RATE = float(os.environ.get("LIVE_FEED_FLAG_RATE", "0.35"))  # share that hit an AML rule
LIVE_FEED_SPOTLIGHT = float(os.environ.get("LIVE_FEED_SPOTLIGHT", "0.6"))   # share of flagged events that spotlight a captured AML case
LIVE_FEED_BURST = float(os.environ.get("LIVE_FEED_BURST", "0.10"))          # chance of entering a burst after an event

# World globe caps. The flagged layer has ~hundreds of rows across the 120-day
# window; drawing every home-branch → merchant arc saturates the globe, so the
# API returns only the *most recent* N arcs. The flagged dots are left uncapped
# (they read as a heat map); override the arc cap with WORLD_ARC_LIMIT.
WORLD_ARC_LIMIT = int(os.environ.get("WORLD_ARC_LIMIT", "10"))
