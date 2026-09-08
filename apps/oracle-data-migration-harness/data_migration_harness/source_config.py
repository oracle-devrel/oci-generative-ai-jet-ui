"""Runtime MongoDB source connection management.

The Developer Hub app starts with the .env Mongo source, but users can replace
it at runtime with another MongoDB URI/database/collection. The active source is
process-local by design: restarting the FastAPI app returns to .env defaults.
"""

from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from threading import RLock
from typing import Any

from pymongo import MongoClient


@dataclass
class SourceConfig:
    kind: str = "mongodb"
    uri: str = "mongodb://localhost:27017"
    database: str = "reviews_demo"
    collection: str = "products"
    status: str = "connected"
    document_count: int | None = None
    error: str | None = None


_lock = RLock()
_source = SourceConfig(
    uri=os.environ.get("MONGO_URI", "mongodb://localhost:27017"),
    database=os.environ.get("MONGO_DB", "reviews_demo"),
    collection=os.environ.get("MONGO_COLLECTION", "products"),
)
_client: MongoClient | None = None


def _new_client(uri: str) -> MongoClient:
    return MongoClient(uri, serverSelectionTimeoutMS=5000)


def _ping_and_count(uri: str, database: str, collection_name: str) -> tuple[MongoClient, int]:
    client = _new_client(uri)
    client.admin.command("ping")
    db = client[database]
    if collection_name not in db.list_collection_names():
        raise ValueError(f"Collection '{database}.{collection_name}' does not exist")
    return client, db[collection_name].count_documents({})


def get_source() -> SourceConfig:
    with _lock:
        out = SourceConfig(**asdict(_source))
    if out.status == "connected":
        try:
            out.document_count = collection().count_documents({})
            out.error = None
        except Exception as e:
            out.status = "error"
            out.error = f"{type(e).__name__}: {str(e)[:200]}"
    return out


def get_source_dict() -> dict[str, Any]:
    return asdict(get_source())


def test_source(uri: str, database: str, collection_name: str) -> dict:
    try:
        client, count = _ping_and_count(uri, database, collection_name)
        col = client[database][collection_name]
        vector_count = col.count_documents(
            {
                "$or": [
                    {"review_embedding": {"$exists": True}},
                    {"embedding": {"$exists": True}},
                ]
            }
        )
        client.close()
        return {
            "ok": True,
            "kind": "mongodb",
            "uri": uri,
            "database": database,
            "collection": collection_name,
            "document_count": count,
            "vector_count_hint": vector_count,
        }
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {str(e)[:500]}"}


def set_source(uri: str, database: str, collection_name: str) -> SourceConfig:
    global _source, _client
    client, count = _ping_and_count(uri, database, collection_name)
    with _lock:
        if _client is not None:
            try:
                _client.close()
            except Exception:
                pass
        _client = client
        _source = SourceConfig(
            uri=uri,
            database=database,
            collection=collection_name,
            status="connected",
            document_count=count,
        )
    return get_source()


def disconnect_source() -> SourceConfig:
    global _source, _client
    with _lock:
        if _client is not None:
            try:
                _client.close()
            except Exception:
                pass
        _client = None
        _source = SourceConfig(
            uri=_source.uri,
            database=_source.database,
            collection=_source.collection,
            status="disconnected",
            document_count=None,
        )
    return get_source()


def client() -> MongoClient:
    global _client
    with _lock:
        if _source.status != "connected":
            raise RuntimeError("No MongoDB source is connected")
        if _client is None:
            _client = _new_client(_source.uri)
        return _client


def database():
    with _lock:
        db_name = _source.database
    return client()[db_name]


def collection():
    with _lock:
        name = _source.collection
    return database()[name]


def collection_name() -> str:
    with _lock:
        return _source.collection


def reset_to_env() -> SourceConfig:
    return set_source(
        os.environ.get("MONGO_URI", "mongodb://localhost:27017"),
        os.environ.get("MONGO_DB", "reviews_demo"),
        os.environ.get("MONGO_COLLECTION", "products"),
    )
