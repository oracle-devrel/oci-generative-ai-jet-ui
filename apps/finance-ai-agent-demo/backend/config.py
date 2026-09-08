"""Application configuration loaded from environment variables."""

import os

from dotenv import load_dotenv

load_dotenv()

# Architecture mode: "converged" | "sprawl" (Compare button works automatically when both are up)
ARCH_MODE = os.getenv("ARCH_MODE", "converged")

# Oracle Database (converged mode)
DB_CONFIG = {
    "user": os.getenv("ORACLE_USER", "VECTOR"),
    "password": os.getenv("ORACLE_PASSWORD", "VectorPwd_2025"),
    "dsn": os.getenv("ORACLE_DSN", "127.0.0.1:1521/FREEPDB1"),
    "program": "finance_ai_agent_demo",
}

ORACLE_ADMIN_PWD = os.getenv("ORACLE_ADMIN_PWD", "OraclePwd_2025")

# Sprawl mode databases
POSTGRES_CONFIG = {
    "host": os.getenv("POSTGRES_HOST", "127.0.0.1"),
    "port": int(os.getenv("POSTGRES_PORT", "5432")),
    "user": os.getenv("POSTGRES_USER", "vector"),
    "password": os.getenv("POSTGRES_PASSWORD", "VectorPwd_2025"),
    "dbname": os.getenv("POSTGRES_DB", "financedb"),
}

NEO4J_CONFIG = {
    "uri": os.getenv("NEO4J_URI", "bolt://127.0.0.1:7687"),
    "user": os.getenv("NEO4J_USER", "neo4j"),
    "password": os.getenv("NEO4J_PASSWORD", "Neo4jPwd_2025"),
}

MONGO_CONFIG = {
    "uri": os.getenv("MONGO_URI", "mongodb://root:MongoPwd_2025@127.0.0.1:27017"),
    "db": os.getenv("MONGO_DB", "financedb"),
}

QDRANT_CONFIG = {
    "host": os.getenv("QDRANT_HOST", "127.0.0.1"),
    "port": int(os.getenv("QDRANT_PORT", "6333")),
}

# OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")

# Tavily
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")

# Embeddings
EMBEDDING_MODEL_NAME = os.getenv(
    "EMBEDDING_MODEL", "sentence-transformers/paraphrase-mpnet-base-v2"
)
EMBEDDING_DIM = 768

# Flask
FLASK_SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "dev-secret-key")
FLASK_DEBUG = os.getenv("FLASK_DEBUG", "false").lower() == "true"
FLASK_PORT = int(os.getenv("FLASK_PORT", "5001"))

# Agent
MAX_AGENT_ITERATIONS = 10
MAX_AGENT_EXECUTION_TIME_S = 60.0

# Model token limits
MODEL_TOKEN_LIMITS = {
    "gpt-5": 128_000,
    "gpt-4o": 128_000,
    "gpt-4o-mini": 128_000,
    "gpt-4-turbo": 128_000,
}
