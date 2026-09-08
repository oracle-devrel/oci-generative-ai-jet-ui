"""Environment configuration for the chat-app backend."""

from __future__ import annotations

import os
from dataclasses import dataclass

# ─── LLM provider ─────────────────────────────────────────────────────────
LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "openai").lower()
if LLM_PROVIDER not in ("openai", "oci"):
    raise RuntimeError(f"LLM_PROVIDER must be 'openai' or 'oci', got {LLM_PROVIDER!r}")

if LLM_PROVIDER == "oci":
    LLM_MODEL = os.environ.get("LLM_MODEL", "xai.grok-4-1-fast-reasoning")
    OCI_GENAI_ENDPOINT = os.environ.get(
        "OCI_GENAI_ENDPOINT",
        "https://inference.generativeai.us-phoenix-1.oci.oraclecloud.com",
    )
    OCI_GENAI_API_KEY = os.environ.get("OCI_GENAI_API_KEY")
    if not OCI_GENAI_API_KEY:
        raise RuntimeError("LLM_PROVIDER=oci requires OCI_GENAI_API_KEY")
else:
    LLM_MODEL = os.environ.get("LLM_MODEL", "gpt-5.5")
    OCI_GENAI_ENDPOINT = None
    OCI_GENAI_API_KEY = None
    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError("LLM_PROVIDER=openai requires OPENAI_API_KEY")


def chat_model_kwargs(**extra) -> dict:
    """Provider-aware kwargs for `ChatOpenAI`."""
    kwargs = dict(extra)
    if LLM_PROVIDER == "oci":
        kwargs.setdefault("base_url", OCI_GENAI_ENDPOINT)
        kwargs.setdefault("api_key", OCI_GENAI_API_KEY)
    return kwargs


# ─── Oracle ───────────────────────────────────────────────────────────────
ORACLE_USER = os.environ.get("ORACLE_USER", "AGENT")
ORACLE_PASSWORD = os.environ.get("ORACLE_PASSWORD", "AgentPwd_2025")
ORACLE_DSN = os.environ.get("ORACLE_DSN", "localhost:1521/FREEPDB1")
ORACLE_AUTH_SYSDBA = ORACLE_USER.lower() == "sys"


# ─── In-DB embedder ───────────────────────────────────────────────────────
ONNX_EMBED_MODEL = os.environ.get("ONNX_EMBED_MODEL", "ALL_MINILM_L12_V2")
ONNX_EMBED_DIM = int(os.environ.get("ONNX_EMBED_DIM", "384"))


# ─── Tables ───────────────────────────────────────────────────────────────
VS_TABLE = os.environ.get("VS_TABLE", "supplychain_demand")
STORE_SUFFIX = os.environ.get("STORE_SUFFIX", "agent_memory")
CACHE_TABLE = os.environ.get("CACHE_TABLE", "langchain_demand_cache")


@dataclass(frozen=True)
class Settings:
    llm_provider: str = LLM_PROVIDER
    llm_model: str = LLM_MODEL
    oracle_user: str = ORACLE_USER
    oracle_dsn: str = ORACLE_DSN
    onnx_model: str = ONNX_EMBED_MODEL
    onnx_dim: int = ONNX_EMBED_DIM
    vs_table: str = VS_TABLE
    store_suffix: str = STORE_SUFFIX

    def public(self) -> dict:
        return {
            "llm_provider": self.llm_provider,
            "llm_model": self.llm_model,
            "onnx_model": self.onnx_model,
            "onnx_dim": self.onnx_dim,
        }


SETTINGS = Settings()
