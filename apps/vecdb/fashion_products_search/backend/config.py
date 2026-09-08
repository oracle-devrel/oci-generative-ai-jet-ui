from __future__ import annotations

import os
from dotenv import load_dotenv

load_dotenv(override=True)

ORACLE_VECDB_REST_URL = os.getenv("VECDB_REST_URL")
ORACLE_USERNAME = os.getenv("VECDB_USERNAME")
ORACLE_PASSWORD = os.getenv("VECDB_PASSWORD")
ORACLE_ACCESS_TOKEN = os.getenv("VECDB_ACCESS_TOKEN")

# Default to SMALL tables; override via env for HIGH (high-res)
ORACLE_TEXT_TABLE = os.getenv("ORACLE_TEXT_TABLE", "FASHION_TEXT_SMALL")
ORACLE_IMAGE_TABLE = os.getenv("ORACLE_IMAGE_TABLE", "FASHION_IMAGE_SMALL")
ORACLE_DISTANCE_METRIC = os.getenv("ORACLE_DISTANCE_METRIC", "cosine")
