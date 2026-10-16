"""Shared configuration for the two token demos.

Everything runs 100% local:
  - LLM:        llama3.1:8b via Ollama        (http://127.0.0.1:11434)
  - Embeddings: nomic-embed-text via Ollama
  - Database:   Oracle AI Database Free container `oracle26ai` (localhost:1521/FREEPDB1)
Override anything with environment variables.
"""

import os

import oracledb

# Identify this app's connections the way the rest of the Developer Hub does.
oracledb.defaults.program = "devrel-developerhub-memory-illusion"

# --- Ollama ---------------------------------------------------------------
OLLAMA_BASE = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
CHAT_MODEL = os.getenv("CHAT_MODEL", "ollama/llama3.1:8b")
EMBED_MODEL = os.getenv("EMBED_MODEL", "ollama/nomic-embed-text")
EMBED_DIM = int(os.getenv("EMBED_DIM", "768"))

# --- Oracle ---------------------------------------------------------------
ORACLE_DSN = os.getenv("ORACLE_DSN", "localhost:1521/FREEPDB1")
ORACLE_USER = os.getenv("ORACLE_USER", "memdemo")
ORACLE_PASSWORD = os.getenv("ORACLE_PASSWORD", "Welcome_123")

# --- demo identity --------------------------------------------------------
USER_ID = "rahul_17"
AGENT_ID = "travel_bot"

# --- generation settings (identical for BOTH demos — fair comparison) -----
SYSTEM_PROMPT = (
    "You are a helpful travel assistant. Answer concisely in at most 4 sentences. "
    "Use what you know about the user when relevant."
)
MAX_TOKENS = 180
TEMPERATURE = 0.3


def estimate_tokens(text: str) -> int:
    """Token estimate used throughout: characters / 4.

    Same convention as the Oracle Agent Memory technical report
    (arXiv:2607.13157, Fig. 5), so the two demos are comparable with the paper.
    """
    return max(1, len(text) // 4)


def payload_tokens(messages: list[dict]) -> int:
    """Estimated input tokens for one chat request payload."""
    return sum(estimate_tokens(m["content"]) for m in messages)
