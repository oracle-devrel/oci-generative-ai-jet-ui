from __future__ import annotations

from pathlib import Path
import argparse
import os
from typing import Dict, Iterable, List

import kagglehub
import numpy as np
import pandas as pd
import torch
import tqdm
from PIL import Image
from sentence_transformers import SentenceTransformer
from transformers import AutoImageProcessor, AutoModel

from oracle_vecdb import OracleVecDB, Configuration  # type: ignore[attr-defined]
from oracle_vecdb.services.ords.exceptions import (
    ApiException,
    NotFoundException,
)

from config import (
    ORACLE_IMAGE_TABLE,
    ORACLE_ACCESS_TOKEN,
    ORACLE_DISTANCE_METRIC,
    ORACLE_PASSWORD,
    ORACLE_TEXT_TABLE,
    ORACLE_USERNAME,
    ORACLE_VECDB_REST_URL,
)

# ---------- Oracle VecDB helpers ----------


def _build_vecdb_client() -> OracleVecDB:
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
        except ApiException as exc:
            if getattr(exc, "status", None) != 409:
                raise


def _upsert_vectors(
    client: OracleVecDB, table_name: str, vectors: List[Dict[str, object]]
) -> None:
    if not vectors:
        return
    try:
        client.upsert_vectors(table_name=table_name, vectors=vectors)
    except ApiException as exc:
        debug_ids = [str(item.get("id", "")) for item in vectors[:5]]
        raise RuntimeError(
            f"Failed to upsert vectors into {table_name}: {exc}; sample ids={debug_ids}"
        ) from exc


vecdb_client = _build_vecdb_client()
try:
    _ensure_table(vecdb_client, ORACLE_IMAGE_TABLE, 768)
    _ensure_table(vecdb_client, ORACLE_TEXT_TABLE, 384)
except ApiException as exc:
    raise RuntimeError(
        "Failed to ensure Oracle VecDB tables. Confirm the service URL and credentials."
    ) from exc

# ---------- Dataset preparation ----------

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}


def parse_args():
    parser = argparse.ArgumentParser(
        description="Load and upsert fashion dataset into VecDB"
    )
    parser.add_argument(
        "--dataset",
        choices=["small", "high"],
        default="small",
        help="Which dataset to use: small (low-res Myntra) or high (high-res Myntra)",
    )
    return parser.parse_args()


def _download_dataset(variant: str) -> Path:
    if variant == "small":
        root = Path(
            kagglehub.dataset_download(
                "paramaggarwal/fashion-product-images-small"
            )
        )
        # small variant root contains `myntradataset` folder
        return (root / "myntradataset").resolve()
    # high (full dataset)
    dataset_root = Path(
        kagglehub.dataset_download(
            "paramaggarwal/fashion-product-images-dataset"
        )
    )
    for styles_file in dataset_root.rglob("styles.csv"):
        return styles_file.parent
    raise RuntimeError(
        "Could not locate styles.csv in the downloaded Kaggle dataset"
    )


def _load_metadata(dataset_root: Path) -> pd.DataFrame:
    images_dir = dataset_root / "images"
    styles_path = dataset_root / "styles.csv"

    if not images_dir.is_dir():
        raise RuntimeError(f"Expected images directory at {images_dir}")
    if not styles_path.is_file():
        raise RuntimeError(f"Expected styles.csv at {styles_path}")

    image_records = [
        (p.stem, str(p))
        for p in images_dir.iterdir()
        if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS
    ]
    if not image_records:
        raise RuntimeError("No image files found in Kaggle dataset")

    images_df = pd.DataFrame(image_records, columns=["source_id", "path"])

    styles_df = pd.read_csv(styles_path, dtype={"id": str}, on_bad_lines="skip")
    styles_df["source_id"] = styles_df["id"].astype(str).str.strip()

    merged_df = images_df.merge(styles_df, on="source_id", how="inner")

    merged_df = merged_df[
        merged_df["productDisplayName"].fillna("").str.len() > 0
    ]
    merged_df = merged_df[merged_df["source_id"].str.len() > 0]
    merged_df = merged_df.reset_index(drop=True)

    merged_df["gender"] = merged_df["gender"].fillna("").astype(str).str.title()
    merged_df["masterCategory"] = (
        merged_df["masterCategory"].fillna("").astype(str).str.title()
    )
    merged_df["subCategory"] = (
        merged_df["subCategory"].fillna("").astype(str).str.title()
    )
    merged_df["articleType"] = merged_df["articleType"].fillna("").astype(str)
    merged_df["baseColour"] = merged_df["baseColour"].fillna("").astype(str)
    merged_df["productDisplayName"] = (
        merged_df["productDisplayName"].fillna("").astype(str)
    )
    merged_df["season"] = merged_df.get("season", "").fillna("").astype(str)
    merged_df["year"] = merged_df.get("year", "").fillna("").astype(str)
    merged_df["usage"] = merged_df.get("usage", "").fillna("").astype(str)

    merged_df = merged_df.reset_index(drop=True)
    merged_df["id"] = (merged_df.index + 1).astype(str)

    columns = [
        "id",
        "source_id",
        "path",
        "gender",
        "masterCategory",
        "subCategory",
        "articleType",
        "baseColour",
        "season",
        "year",
        "usage",
        "productDisplayName",
    ]

    return merged_df[columns].fillna("")


# ---------- Embedding models ----------
iprocessor = AutoImageProcessor.from_pretrained(
    "google/vit-base-patch16-224-in21k"
)
imodel = AutoModel.from_pretrained("google/vit-base-patch16-224-in21k")
tmodel = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")


def _embed_images(images: Iterable[Image.Image]) -> List[List[float]]:
    img_inputs = iprocessor(images=list(images), return_tensors="pt")
    with torch.no_grad():
        outputs = imodel(**img_inputs)
        last_hidden_state = outputs.last_hidden_state[:, 0, :]
        features = last_hidden_state / last_hidden_state.norm(
            dim=1, keepdim=True
        )
        features = features.cpu().numpy().astype(np.float32)
        return [f.tolist() for f in features]


def _embed_text(texts: List[str]) -> List[List[float]]:
    embeddings = tmodel.encode(texts, normalize_embeddings=True)
    return embeddings.astype(np.float32).tolist()


def _row_metadata(row: pd.Series) -> Dict[str, object]:
    return {
        "sourceId": getattr(row, "source_id", ""),
        "gender": row.gender,
        "masterCategory": row.masterCategory,
        "subCategory": row.subCategory,
        "articleType": row.articleType,
        "baseColour": row.baseColour,
        "season": row.season,
        "year": row.year,
        "usage": row.usage,
        "productDisplayName": row.productDisplayName,
        "image_path": row.path,
    }


# ---------- Main upsert routine ----------
def create_and_upload_vectors(df: pd.DataFrame, batch_size: int = 128) -> None:
    for start in tqdm.tqdm(
        range(0, len(df), batch_size), desc="Embedding + Upsert"
    ):
        batch = df.iloc[start : start + batch_size]

        images_batch = [Image.open(p).convert("RGB") for p in batch["path"]]
        text_batch = batch["productDisplayName"].tolist()

        image_vectors = _embed_images(images_batch)
        text_vectors = _embed_text(text_batch)

        img_payload: List[Dict[str, object]] = []
        txt_payload: List[Dict[str, object]] = []

        for row, img_vec, txt_vec in zip(
            batch.itertuples(), image_vectors, text_vectors
        ):
            metadata = _row_metadata(row)
            vector_id = str(row.id).strip()
            if not vector_id:
                raise ValueError(f"Empty vector id for row index {row.Index}")
            img_payload.append(
                {"id": vector_id, "dense_vector": img_vec, "metadata": metadata}
            )
            txt_payload.append(
                {"id": vector_id, "dense_vector": txt_vec, "metadata": metadata}
            )

        _upsert_vectors(vecdb_client, ORACLE_IMAGE_TABLE, img_payload)
        _upsert_vectors(vecdb_client, ORACLE_TEXT_TABLE, txt_payload)


if __name__ == "__main__":
    args = parse_args()
    dataset_root = _download_dataset(args.dataset)

    # Build final table names without reassigning globals before function defs
    image_table = ORACLE_IMAGE_TABLE
    text_table = ORACLE_TEXT_TABLE
    if args.dataset == "small":
        image_table = (
            f"{image_table}_SMALL"
            if not image_table.endswith("_SMALL")
            else image_table
        )
        text_table = (
            f"{text_table}_SMALL"
            if not text_table.endswith("_SMALL")
            else text_table
        )
    else:
        image_table = (
            f"{image_table}_HIGH"
            if not image_table.endswith("_HIGH")
            else image_table
        )
        text_table = (
            f"{text_table}_HIGH"
            if not text_table.endswith("_HIGH")
            else text_table
        )

    _ensure_table(vecdb_client, image_table, 768)
    _ensure_table(vecdb_client, text_table, 384)

    # Monkey-patch table names locally for upsert calls in this run
    ORACLE_IMAGE_TABLE = image_table
    ORACLE_TEXT_TABLE = text_table

    dataframe = _load_metadata(dataset_root)
    create_and_upload_vectors(dataframe)
