import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")


def env(key, default=""):
    return os.environ.get(key, default)


DSN = env("HF_DSN", "localhost:1523/FREEPDB1")
OWNER = "HF_OWNER"
EMBED = "HF_OWNER.HF_EMBED"
# Optional in-database ONNX cross-encoder (schema.model). Empty keeps vector-distance order.
RERANK = env("HF_RERANK_MODEL", "")
PERSONAS = {
    "Credit": {
        "user": "hf_credit",
        "memory_user": "HF_CREDIT_MEM",
        "password": env("HF_CREDIT_PASSWORD"),
    },
    "Markets": {
        "user": "hf_markets",
        "memory_user": "HF_MARKETS_MEM",
        "password": env("HF_MARKETS_PASSWORD"),
    },
}
MODELS = [
    {
        "id": "privateai",
        "label": "Private AI · Qwen 2.5 3B Q4",
        "provider": "privateai",
        "model": env("PRIVATE_AI_MODEL", "qwen2.5-3b-instruct-q4_k_m"),
        "context": 8192,
        "input_price": 0,
        "output_price": 0,
        "note": "$0 inference API fee; laptop power and hardware excluded.",
    },
    {
        "id": "ollama",
        "label": "Local fallback · Llama 3.2 3B (Ollama)",
        "provider": "ollama",
        "model": env("OLLAMA_MODEL", "llama3.2:latest"),
        "context": 8192,
        "input_price": 0,
        "output_price": 0,
        "note": "Fallback runtime: not Oracle Private AI Services. $0 API fee; hardware excluded.",
    },
    {
        "id": "openai",
        "label": "OpenAI · GPT-6.1 Sol",
        "provider": "openai",
        "model": env("OPENAI_MODEL", "gpt-6.1-sol"),
        "context": 1050000,
        "input_price": 2.00,
        "cached_input_price": 0.10,
        "output_price": 10.00,
        "key": "OPENAI_API_KEY",
        "note": "OpenAI list price, USD per million tokens (≤272K context), checked 12 Oct 2026. Reasoning effort low.",
    },
    {
        "id": "anthropic",
        "label": "Anthropic · Claude Opus 5.5",
        "provider": "anthropic",
        "model": env("ANTHROPIC_MODEL", "claude-opus-5-5"),
        "context": 1000000,
        "input_price": 4.00,
        "cached_input_price": 0.20,
        "cache_write_price": 5.00,
        "output_price": 20.00,
        "key": "ANTHROPIC_API_KEY",
        "note": "Anthropic list price, USD per million tokens. Effort low; server-side refusal fallback enabled.",
    },
    {
        "id": "oci",
        "label": "OCI Generative AI · xAI Grok 4.3",
        "provider": "oci",
        "model": env("OCI_GENAI_MODEL", "xai.grok-4.3"),
        "context": int(env("OCI_CONTEXT", "1000000")),
        "input_price": float(env("OCI_INPUT_PRICE", "1.25")),
        "cached_input_price": float(env("OCI_CACHED_INPUT_PRICE", "0.20")),
        "output_price": float(env("OCI_OUTPUT_PRICE", "2.50")),
        "key": "OCI_GENAI_API_KEY",
        "note": "Cost uses xAI’s published Grok 4.3 list price as a reference; the OCI rate card was not verified.",
    },
]
# Same reasoning depth for both agents; low keeps live-demo latency down.
REASONING_EFFORT = env("HF_REASONING_EFFORT", "low")
