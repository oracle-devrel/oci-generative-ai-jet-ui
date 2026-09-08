"""Layer 4: process environment, connections, sandbox boundaries."""

import os
from functools import lru_cache

import oracledb
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()


@lru_cache(maxsize=1)
def oracle_pool() -> oracledb.ConnectionPool:
    return oracledb.create_pool(
        user=os.environ["ORACLE_USER"],
        password=os.environ["ORACLE_PASSWORD"],
        dsn=os.environ["ORACLE_DSN"],
        min=1,
        max=4,
        increment=1,
    )


@lru_cache(maxsize=1)
def mongo_client() -> MongoClient:
    return MongoClient(os.environ["MONGO_URI"])


def mongo_db():
    return mongo_client()[os.environ.get("MONGO_DB", "reviews_demo")]
