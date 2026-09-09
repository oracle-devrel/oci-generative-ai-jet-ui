from __future__ import annotations

import os

from dotenv import load_dotenv

# The sample's backend/.env is the source of truth for its local connection.
load_dotenv(override=True)

ORACLE_VECDB_REST_URL = os.getenv("VECDB_REST_URL")
ORACLE_USERNAME = os.getenv("VECDB_USERNAME")
ORACLE_PASSWORD = os.getenv("VECDB_PASSWORD")
ORACLE_ACCESS_TOKEN = os.getenv("VECDB_ACCESS_TOKEN")

ORACLE_TEXT_TABLE = os.getenv("ORACLE_TEXT_TABLE", "PRODUCT_TEXT_VECTORS")
ORACLE_DISTANCE_METRIC = os.getenv("ORACLE_DISTANCE_METRIC", "cosine")
