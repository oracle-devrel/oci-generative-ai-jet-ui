from __future__ import annotations

import io
import json
import math
import os
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import requests
from fastapi import (
    FastAPI,
    File,
    HTTPException,
    Query,
    Request,
    UploadFile,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from PIL import Image
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer

from oracle_vecdb import OracleVecDB, Configuration  # type: ignore[attr-defined]
from oracle_vecdb.services.ords.exceptions import (
    ApiException,
    NotFoundException,
)

from config import (
    ORACLE_ACCESS_TOKEN,
    ORACLE_DISTANCE_METRIC,
    ORACLE_PASSWORD,
    ORACLE_TEXT_TABLE,
    ORACLE_USERNAME,
    ORACLE_VECDB_REST_URL,
)

VECTOR_DIMENSION = 512
CATEGORIES_FILE = Path(__file__).with_name("categories.json")


class SearchResult(BaseModel):
    id: str
    score: float
    title: str
    description: str
    price: float
    image: str
    text: str = ""
    category: str = ""
    specification: str = ""


vector_search_history: deque[Dict[str, Any]] = deque(maxlen=5)

model = SentenceTransformer("clip-ViT-B-32")


def _build_client() -> OracleVecDB:
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


def _ensure_table(client: OracleVecDB, table_name: str, dimension: int) -> None:
    try:
        client.describe_vector_table(name=table_name)
    except NotFoundException:
        try:
            client.create_vector_table(
                name=table_name,
                comment=f"Product recommendations ({table_name})",
                annotations={
                    "dimension": str(dimension),
                    "metric": ORACLE_DISTANCE_METRIC,
                },
                index_params={
                    "metadata_index_params": {
                        "auto_index": True,
                        "include_paths": ["main_category_normalized", "price"],
                    },
                },
            )
        except ApiException as exc:
            if getattr(exc, "status", None) != 409:
                raise


vecdb_client = _build_client()
_ensure_table(vecdb_client, ORACLE_TEXT_TABLE, VECTOR_DIMENSION)

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _embed_text(text: str) -> List[float]:
    if not text:
        return [0.0] * VECTOR_DIMENSION
    return model.encode(text).tolist()


def _embed_image(image: Image.Image) -> List[float]:
    return model.encode(image).tolist()


def _zero_vector() -> List[float]:
    return [0.0] * VECTOR_DIMENSION


def _sanitize_price(value: Any) -> float:
    try:
        candidate = float(value)
        if math.isnan(candidate) or math.isinf(candidate):
            return 0.0
        return candidate
    except (TypeError, ValueError):
        return 0.0


def _score_from_distance(distance: Any) -> float:
    try:
        dist = float(distance)
    except (TypeError, ValueError):
        return 0.0
    return round(max(0.0, 1.0 - dist), 4)


def _extract_metadata(item: Any) -> Dict[str, Any]:
    if isinstance(item, dict):
        return item.get("metadata", {}) or {}
    return getattr(item, "metadata", {}) or {}


def _extract_id(item: Any) -> str:
    if isinstance(item, dict):
        return str(item.get("id", ""))
    return str(getattr(item, "id", ""))


def _extract_distance(item: Any) -> Optional[float]:
    value = None
    if isinstance(item, dict):
        value = item.get("distance")
    else:
        value = getattr(item, "distance", None)
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _as_search_result(item: Any) -> SearchResult:
    metadata = _extract_metadata(item)
    distance = _extract_distance(item)
    score = _score_from_distance(distance)
    price = _sanitize_price(metadata.get("price"))

    return SearchResult(
        id=_extract_id(item),
        score=score,
        title=str(metadata.get("title", "")),
        description=str(metadata.get("description", "")),
        price=price,
        image=str(metadata.get("image", "")),
        text=str(metadata.get("text", "")),
        category=str(metadata.get("category", "")),
        specification=str(metadata.get("specification", "")),
    )


def _extract_matches(response: Any) -> List[Any]:
    if isinstance(response, list):
        return list(response)
    if isinstance(response, dict):
        matches = response.get("results")
        return list(matches or [])
    if hasattr(response, "results"):
        return list(response.results or [])
    return []


def _build_filters(
    categories: Iterable[str] | None,
    min_price: float,
    max_price: float,
) -> Optional[Dict[str, Any]]:
    clauses: List[Dict[str, Any]] = []

    if categories:
        normalized = sorted(
            {
                part.strip().lower()
                for part in categories
                if part and part.strip()
            }
        )
        if normalized:
            clauses.append({"main_category_normalized": {"$in": normalized}})

    clauses.append(
        {
            "price": {
                "$gte": float(min_price),
                "$lte": float(max_price),
            }
        }
    )

    if not clauses:
        return None
    if len(clauses) == 1:
        return clauses[0]
    return {"$and": clauses}


def _query_oracle(
    vector: List[float],
    top_k: int,
    filters: Optional[Dict[str, Any]] = None,
    min_price: float = 0.0,
    max_price: float = float("inf"),
) -> List[SearchResult]:

    try:

        response = vecdb_client.query(
            table_name=ORACLE_TEXT_TABLE,
            query_by={"vector": vector},
            top_k=top_k,
            filters=filters,
            include_vectors=False,
        )

    except ApiException as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=502, detail=f"Oracle VecDB query failed: {exc}"
        )

    matches = _extract_matches(response)
    results = [_as_search_result(match) for match in matches]
    bounded: List[SearchResult] = []
    for item in results:
        if item.price < min_price or item.price > max_price:
            continue
        bounded.append(item)
        if len(bounded) >= top_k:
            break

    if len(bounded) < top_k:
        bounded.extend(results[: top_k - len(bounded)])

    return bounded


def _parse_categories_param(value: Optional[str]) -> List[str]:
    if not value:
        return []
    return [part.strip() for part in value.split(",") if part.strip()]


def _load_categories_from_file() -> List[str]:
    if not CATEGORIES_FILE.exists():
        return []
    try:
        payload = json.loads(CATEGORIES_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):  # noqa: BLE001
        return []

    categories = []
    for entry in payload.get("categories", []):
        name = str(entry.get("name", "")).strip()
        uploaded = entry.get("uploaded_records", 0)
        if name and uploaded:
            categories.append(name)

    return sorted(set(categories))


@app.get("/categories", response_model=List[str])
def get_categories() -> List[str]:
    categories = _load_categories_from_file()
    if not categories:
        raise HTTPException(
            status_code=503,
            detail="No categories available. Ensure load_dataset.py has been run and categories.json exists.",
        )

    return categories


@app.get("/products", response_model=List[SearchResult])
def get_products(
    top_k: int = Query(25, ge=1, le=200),
    min_price: float = Query(0.0, ge=0.0),
    max_price: float = Query(10000.0, ge=0.0),
    categories: Optional[str] = Query(None),
) -> List[SearchResult]:
    filters = _build_filters(
        _parse_categories_param(categories), min_price, max_price
    )
    # Cosine distance is undefined for an all-zero query vector.  Use a stable
    # non-zero embedding for the initial, unfiltered product listing instead.
    return _query_oracle(
        _embed_text("product"), top_k, filters, min_price, max_price
    )


class RichVectorSearchRequest(BaseModel):
    title: str = ""
    description: str = ""
    image: str = ""
    price: float = 0.0
    top_k: int = 20
    min_price: float = 0.0
    max_price: float = 10000.0
    categories: str = ""


def _combine_embeddings(
    text_embedding: List[float], image_embedding: Optional[List[float]]
) -> List[float]:
    if not image_embedding:
        return text_embedding
    return [(t + i) / 2 for t, i in zip(text_embedding, image_embedding)]


@app.post("/vector-search", response_model=List[SearchResult])
async def vector_search_rich(
    request: RichVectorSearchRequest,
) -> List[SearchResult]:
    combined_text = f"{request.title}. {request.description}".strip()

    try:
        text_embedding = _embed_text(combined_text)
    except Exception as exc:  # noqa: BLE001
        return JSONResponse(
            status_code=500, content={"detail": f"Text embedding failed: {exc}"}
        )

    image_embedding: Optional[List[float]] = None
    if request.image:
        try:
            response = requests.get(request.image, timeout=10)
            response.raise_for_status()
            image = Image.open(io.BytesIO(response.content)).convert("RGB")
            image_embedding = _embed_image(image)
        except Exception:  # noqa: BLE001
            image_embedding = None

    embedding = _combine_embeddings(text_embedding, image_embedding)
    filters = _build_filters(
        _parse_categories_param(request.categories),
        request.min_price,
        request.max_price,
    )

    results = _query_oracle(
        embedding, request.top_k, filters, request.min_price, request.max_price
    )

    vector_search_history.append(
        {
            "timestamp": datetime.utcnow().isoformat(),
            "title": request.title,
            "description": request.description,
            "image": request.image,
            "categories": request.categories,
            "min_price": request.min_price,
            "max_price": request.max_price,
            "results": [item.model_dump() for item in results],
        }
    )

    return results


@app.get("/search", response_model=List[SearchResult])
def search(
    query: str = Query(..., description="Search query"),
    top_k: int = Query(20, ge=1, le=200),
    min_price: float = Query(0.0, ge=0.0),
    max_price: float = Query(10000.0, ge=0.0),
    categories: Optional[str] = Query(None),
) -> List[SearchResult]:
    try:
        embedding = _embed_text(query)
    except Exception as exc:  # noqa: BLE001
        return JSONResponse(
            status_code=500, content={"detail": f"Text embedding failed: {exc}"}
        )

    filters = _build_filters(
        _parse_categories_param(categories), min_price, max_price
    )
    return _query_oracle(embedding, top_k, filters, min_price, max_price)


@app.post("/image-search", response_model=List[SearchResult])
async def image_search(
    request: Request,
    file: UploadFile = File(...),
) -> List[SearchResult]:
    form = await request.form()
    top_k = int(form.get("top_k", "20"))
    min_price = float(form.get("min_price", "0"))
    max_price = float(form.get("max_price", "10000"))
    categories = form.get("categories")

    image_bytes = await file.read()
    try:
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=400, detail="Invalid image file"
        ) from exc

    try:
        embedding = _embed_image(image)
    except Exception as exc:  # noqa: BLE001
        return JSONResponse(
            status_code=500,
            content={"detail": f"Image embedding failed: {exc}"},
        )

    filters = _build_filters(
        _parse_categories_param(categories), min_price, max_price
    )
    return _query_oracle(embedding, top_k, filters, min_price, max_price)


@app.get("/vector-search/history")
def get_last_vector_searches() -> List[Dict[str, Any]]:
    if not vector_search_history:
        return []
    latest = vector_search_history[-1].get("results", [])
    return [
        item if isinstance(item, dict) else item.model_dump() for item in latest
    ]
