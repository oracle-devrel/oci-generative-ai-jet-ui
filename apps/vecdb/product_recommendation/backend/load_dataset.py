from __future__ import annotations

import sys
import time
import os
from collections import Counter, defaultdict
from datetime import datetime, timezone
import json
import math
from numbers import Real
from pathlib import Path
from typing import Dict, Iterable, List

from datasets import load_dataset
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
BATCH_SIZE = 256
MAX_UPSERT_RETRIES = 3
RETRY_BASE_SECONDS = 5

CATEGORY_MIN_COUNT = 1000
CATEGORIES_OUTPUT = Path(__file__).with_name("categories.json")


def _build_client() -> OracleVecDB:
    config_kwargs = {"rest_url": ORACLE_VECDB_REST_URL}
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


def _upsert(client: OracleVecDB, vectors: List[Dict[str, object]]) -> None:
    if not vectors:
        return
    for attempt in range(1, MAX_UPSERT_RETRIES + 1):
        try:
            client.upsert_vectors(table_name=ORACLE_TEXT_TABLE, vectors=vectors)
            return
        except ApiException as exc:  # noqa: BLE001
            if attempt == MAX_UPSERT_RETRIES:
                raise RuntimeError(
                    f"Failed to upsert vectors into {ORACLE_TEXT_TABLE}: {exc}"
                ) from exc
            sleep_for = RETRY_BASE_SECONDS * attempt
            print(
                f"Upsert attempt {attempt} failed ({exc}); retrying in {sleep_for}s...",
                flush=True,
            )
            time.sleep(sleep_for)


def _format_text(record: Dict[str, object]) -> str:
    title = str(record.get("Product Name", "[No Title]")).strip()
    description = str(record.get("Description", "[No Description]")).strip()
    return f"{title} - {description}".strip()


def _clean_price(value: object) -> float:
    candidate: float
    if isinstance(value, str):
        cleaned = value.replace("$", "").replace(",", "").strip()
        if not cleaned:
            return 0.0
        try:
            candidate = float(cleaned)
        except ValueError:
            return 0.0
    elif isinstance(value, Real):
        candidate = float(value)
    else:
        return 0.0

    if math.isnan(candidate) or math.isinf(candidate):
        return 0.0
    return candidate


def _clean_text(value: object, fallback: str = "") -> str:
    text = "" if value is None else str(value)
    text = text.strip()
    return text or fallback


def _category_terms(category: str) -> List[str]:
    return [
        part.strip().lower() for part in category.split("|") if part.strip()
    ]


def _main_category(raw_category: object) -> str:
    text = _clean_text(raw_category, "")
    if not text:
        return ""
    return text.split("|")[0].strip()


def _eligible_categories(dataset) -> Dict[str, int]:
    counts: Counter[str] = Counter()
    total = len(dataset)
    for idx in range(total):
        record = dataset[idx]
        main = _main_category(record.get("Category"))
        if main:
            counts[main] += 1

    return {
        category: count
        for category, count in counts.items()
        if count >= CATEGORY_MIN_COUNT
    }


def _batched(iterable: Iterable[int], batch_size: int) -> Iterable[List[int]]:
    batch: List[int] = []
    for idx in iterable:
        batch.append(idx)
        if len(batch) >= batch_size:
            yield batch
            batch = []
    if batch:
        yield batch


if __name__ == "__main__":
    print("Loading dataset from Hugging Face...")
    dataset = load_dataset("ckandemir/amazon-products", split="train")
    total = len(dataset)
    print(f"Loaded {total} records")

    eligible_categories = _eligible_categories(dataset)

    if not eligible_categories:
        print(
            "No categories met the minimum threshold; nothing to upload.",
            file=sys.stderr,
        )
        sys.exit(1)

    print(
        f"Eligible categories (min {CATEGORY_MIN_COUNT} records): {len(eligible_categories)}"
    )

    model = SentenceTransformer("clip-ViT-B-32")

    client = _build_client()
    _ensure_table(client, ORACLE_TEXT_TABLE, VECTOR_DIMENSION)

    uploaded_counts: Dict[str, int] = defaultdict(int)
    total_uploaded = 0

    for batch_indices in _batched(range(total), BATCH_SIZE):
        prepared: List[Dict[str, object]] = []

        for idx in batch_indices:
            record = dataset[idx]
            category_full = _clean_text(record.get("Category"), "").strip()
            main_category = _main_category(category_full)

            if not main_category or main_category not in eligible_categories:
                continue

            product_name = _clean_text(record.get("Product Name"), "").strip()
            description = _clean_text(record.get("Description"), "").strip()
            price = _clean_price(record.get("Selling Price"))
            specification = _clean_text(
                record.get("Product Specification"), ""
            ).strip()
            image_url = _clean_text(record.get("Image"), "").strip()
            category_terms = _category_terms(category_full)

            if not (
                product_name
                and description
                and category_terms
                and price > 0.0
                and image_url
            ):
                continue

            prepared.append(
                {
                    "idx": idx,
                    "main_category": main_category,
                    "category_full": category_full,
                    "product_name": product_name,
                    "description": description,
                    "price": price,
                    "specification": specification,
                    "image_url": image_url,
                    "category_terms": category_terms,
                    "text": _format_text(record),
                }
            )

        if not prepared:
            continue

        batch_texts = [item["text"] for item in prepared]
        embeddings = model.encode(batch_texts, show_progress_bar=False).tolist()

        payload: List[Dict[str, object]] = []
        for item, embedding in zip(prepared, embeddings):
            main_category = str(item["main_category"])
            metadata = {
                "title": item["product_name"],
                "description": item["description"],
                "category": item["category_full"],
                "category_terms": item["category_terms"],
                "main_category": main_category,
                "main_category_normalized": main_category.lower(),
                "price": item["price"],
                "specification": item["specification"],
                "image": item["image_url"],
                "text": item["text"],
            }

            payload.append(
                {
                    "id": f"prod-{item['idx']}",
                    "dense_vector": embedding,
                    "metadata": metadata,
                }
            )

            uploaded_counts[main_category] += 1
            total_uploaded += 1

        _upsert(client, payload)
        last_index = prepared[-1]["idx"]
        print(f"Upserted {len(payload)} records (last index {last_index})")

    category_summary = [
        {
            "name": category,
            "total_records": eligible_categories[category],
            "uploaded_records": uploaded_counts.get(category, 0),
        }
        for category in sorted(
            eligible_categories,
            key=lambda name: uploaded_counts.get(name, 0),
            reverse=True,
        )
    ]

    metadata = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "min_count_threshold": CATEGORY_MIN_COUNT,
        "categories": category_summary,
    }

    try:
        CATEGORIES_OUTPUT.write_text(
            json.dumps(metadata, indent=2), encoding="utf-8"
        )
        print(f"Wrote category summary to {CATEGORIES_OUTPUT}")
    except OSError as exc:  # noqa: BLE001
        print(f"Failed to write category summary: {exc}", file=sys.stderr)

    uploaded_category_count = sum(
        1
        for category in eligible_categories
        if uploaded_counts.get(category, 0) > 0
    )
    print(
        "Dataset upload complete. Uploaded "
        f"{total_uploaded} records across {uploaded_category_count} categories."
    )
