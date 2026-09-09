from __future__ import annotations

import io
import json
import logging
import os
from typing import Any, Dict, List, Optional, Union

import numpy as np
import torch
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from PIL import Image
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer
from transformers import AutoImageProcessor, AutoModel

from oracle_vecdb import OracleVecDB, Configuration  # type: ignore[attr-defined]
from oracle_vecdb.services.ords.exceptions import (
    ApiException,
    NotFoundException,
)

from config import (
    ORACLE_DISTANCE_METRIC,
    ORACLE_IMAGE_TABLE,
    ORACLE_ACCESS_TOKEN,
    ORACLE_PASSWORD,
    ORACLE_TEXT_TABLE,
    ORACLE_USERNAME,
    ORACLE_VECDB_REST_URL,
)

BACKEND_ORIGIN = os.getenv("BACKEND_ORIGIN", "http://localhost:8000")
IMAGE_CACHE: Dict[str, str] = {}

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------- Oracle VecDB clients ----------


def _build_vecdb_client() -> OracleVecDB:
    config_kwargs: Dict[str, Any] = {"rest_url": ORACLE_VECDB_REST_URL}
    if ORACLE_ACCESS_TOKEN:
        # Bearer-token authentication takes precedence when VECDB_ACCESS_TOKEN is set.
        config_kwargs["access_token"] = ORACLE_ACCESS_TOKEN
    else:
        config_kwargs["username"] = ORACLE_USERNAME
        config_kwargs["password"] = ORACLE_PASSWORD
    config = Configuration(**config_kwargs)

    if os.getenv("VECDB_SELF_SIGNED_SSL", "false").lower() == "true":
        config.verify_ssl = False

    return OracleVecDB(config)


def _ensure_vector_table(
    client: OracleVecDB, table_name: str, dimension: int
) -> None:
    try:
        client.describe_vector_table(name=table_name)
    except NotFoundException:
        try:
            client.create_vector_table(
                name=table_name,
                comment=f"Fashion search vectors ({table_name})",
                annotations={
                    "dimension": str(dimension),
                    "metric": ORACLE_DISTANCE_METRIC,
                },
                index_params={
                    "metadata_index_params": {
                        "auto_index": True,
                        "include_paths": [
                            "gender",
                            "masterCategory",
                            "subCategory",
                        ],
                    },
                },
            )
        except ApiException as exc:  # table may already exist concurrently
            if getattr(exc, "status", None) != 409:
                raise


vecdb_client = _build_vecdb_client()

# ensure both tables exist at startup
_ensure_vector_table(vecdb_client, ORACLE_TEXT_TABLE, 384)
_ensure_vector_table(vecdb_client, ORACLE_IMAGE_TABLE, 768)


# ---------- Embedding models ----------
iprocessor = AutoImageProcessor.from_pretrained(
    "google/vit-base-patch16-224-in21k", use_fast=True
)
imodel = AutoModel.from_pretrained("google/vit-base-patch16-224-in21k")
imodel.eval()

tmodel = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")


def embed_text(queries: List[str]) -> List[List[float]]:
    arr = tmodel.encode(queries, normalize_embeddings=True)
    return arr.astype(np.float32).tolist()


def embed_images(inputs: List[Image.Image]) -> List[List[float]]:
    img_inputs = iprocessor(images=inputs, return_tensors="pt")
    with torch.no_grad():
        outputs = imodel(**img_inputs)
        last_hidden_state = outputs.last_hidden_state[:, 0, :]
        features = last_hidden_state / last_hidden_state.norm(
            dim=1, keepdim=True
        )
        features = features.cpu().numpy().astype(np.float32)
        return [f.tolist() for f in features]


def embed_image(img: Image.Image) -> List[float]:
    return embed_images([img])[0]


# ---------- Schemas ----------
class TextQuery(BaseModel):
    query: str
    top_k: int = 8
    filters: Optional[Dict[str, Any]] = None


# ---------- Filtering helpers ----------
def _norm_list(val: Union[str, List[str], None]) -> List[str]:
    if val is None:
        return []
    if isinstance(val, str):
        return [p.strip() for p in val.split(",") if p.strip()]
    return [str(p).strip() for p in val if str(p).strip()]


def build_filter(
    gender: Union[str, List[str], None] = None,
    master_category: Union[str, List[str], None] = None,
    sub_category: Union[str, List[str], None] = None,
) -> Optional[Dict[str, Any]]:
    clauses: List[Dict[str, Any]] = []

    gvals = _norm_list(gender)
    if gvals:
        clauses.append(
            {"gender": {"$eq": gvals[0]}}
            if len(gvals) == 1
            else {"gender": {"$in": gvals}}
        )

    mvals = _norm_list(master_category)
    if mvals:
        clauses.append(
            {"masterCategory": {"$eq": mvals[0]}}
            if len(mvals) == 1
            else {"masterCategory": {"$in": mvals}}
        )

    svals = _norm_list(sub_category)
    if svals:
        clauses.append(
            {"subCategory": {"$eq": svals[0]}}
            if len(svals) == 1
            else {"subCategory": {"$in": svals}}
        )

    if not clauses:
        return None
    return clauses[0] if len(clauses) == 1 else {"$and": clauses}


def build_filter_from_payload(
    filters: Optional[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    if not filters:
        return None
    return build_filter(
        gender=filters.get("gender"),
        master_category=filters.get("masterCategory"),
        sub_category=filters.get("subCategory"),
    )


def _item_to_dict(item: Any) -> Dict[str, Any]:
    if isinstance(item, dict):
        return item
    if hasattr(item, "model_dump"):
        return item.model_dump()
    if hasattr(item, "to_dict"):
        return item.to_dict()
    return {
        "id": getattr(item, "id", ""),
        "distance": getattr(item, "distance", None),
        "metadata": getattr(item, "metadata", {}) or {},
    }


def match_to_payload(item: Dict[str, Any]) -> Dict[str, Any]:
    metadata = item.get("metadata", {}) or {}
    pid = str(item.get("id", ""))
    distance = item.get("distance")
    similarity = 1.0 - float(distance) if distance is not None else 0.0
    path = metadata.get("image_path", "") or metadata.get("path", "")
    if path:
        IMAGE_CACHE[pid] = path

    return {
        "id": pid,
        "similarityScore": similarity,
        "imageUrl": f"{BACKEND_ORIGIN}/images/{pid}",
        "gender": metadata.get("gender", ""),
        "masterCategory": metadata.get("masterCategory", ""),
        "subCategory": metadata.get("subCategory", ""),
        "articleType": metadata.get("articleType", ""),
        "baseColour": metadata.get("baseColour", ""),
        "season": metadata.get("season", ""),
        "year": metadata.get("year", ""),
        "usage": metadata.get("usage", ""),
        "productDisplayName": metadata.get("productDisplayName", ""),
        "path": path,
    }


# ---------- Query helpers ----------
def _query_oracle(
    table_name: str,
    vector: List[float],
    top_k: int,
    filters: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    try:
        response = vecdb_client.query(
            table_name=table_name,
            query_by={"vector": vector},
            top_k=top_k,
            include_vectors=False,
            filters=filters or None,
        )
    except ApiException as exc:
        raise HTTPException(
            status_code=502, detail=f"Oracle VecDB query failed: {exc}"
        ) from exc

    if isinstance(response, dict):
        results = response.get("results") or response.get("items") or []
    elif hasattr(response, "results"):
        results = response.results or []
    elif hasattr(response, "items"):
        results = response.items or []
    else:
        results = response if isinstance(response, list) else []

    return results


# ---------- Endpoints ----------
@app.post("/search/text")
def search_text(q: TextQuery):
    print("Inside search")
    vector = embed_text([q.query])[0]
    filters = build_filter_from_payload(q.filters)
    items = _query_oracle(ORACLE_TEXT_TABLE, vector, q.top_k, filters)
    return {
        "results": [match_to_payload(_item_to_dict(item)) for item in items]
    }


@app.post("/search/image")
async def search_image(
    file: UploadFile = File(...),
    top_k: int = Form(8),
    filters: Optional[str] = Form(None),
):
    content = await file.read()
    try:
        image = Image.open(io.BytesIO(content)).convert("RGB")
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=400, detail="Invalid image file"
        ) from exc

    vector = embed_image(image)
    filters_payload = json.loads(filters) if filters else None
    filters_obj = build_filter_from_payload(filters_payload)

    items = _query_oracle(ORACLE_IMAGE_TABLE, vector, top_k, filters_obj)
    return {
        "results": [match_to_payload(_item_to_dict(item)) for item in items]
    }


@app.get("/images/{item_id}")
def serve_image(item_id: str):
    cached_path = IMAGE_CACHE.get(item_id)
    if cached_path and os.path.isfile(cached_path):
        return FileResponse(cached_path)

    for table_name in (ORACLE_IMAGE_TABLE, ORACLE_TEXT_TABLE):
        try:
            response = vecdb_client.list_vectors(
                table_name=table_name, ids=[item_id], limit=1
            )
        except ApiException as exc:
            raise HTTPException(
                status_code=502, detail=f"Failed to fetch metadata: {exc}"
            ) from exc
        except Exception as exc:
            logging.debug(
                "VecDB list_vectors failed for %s: %s", table_name, exc
            )
            continue

        vectors: List[Dict[str, Any]] = []
        if isinstance(response, dict):
            raw_vectors = response.get("items") or response.get("vectors") or []
            if isinstance(raw_vectors, list):
                vectors = [v for v in raw_vectors if isinstance(v, dict)]
        elif hasattr(response, "items"):
            raw_iterable = getattr(response, "items", None)
            if isinstance(raw_iterable, list):
                vectors = [v for v in raw_iterable if isinstance(v, dict)]

        if not vectors:
            continue

        record = vectors[0]
        metadata = (
            record.get("metadata", {})
            if isinstance(record, dict)
            else getattr(record, "metadata", {})
        )
        path = metadata.get("image_path") or metadata.get("path")
        if path and os.path.isfile(path):
            IMAGE_CACHE[item_id] = path
            return FileResponse(path)

    raise HTTPException(
        status_code=404, detail="Image file not available on server"
    )
