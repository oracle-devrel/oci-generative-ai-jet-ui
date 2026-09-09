import hashlib
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Literal, Optional
from uuid import uuid4

import torch
import torch.nn.functional as F
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from langchain.embeddings.base import Embeddings
from oracle_vecdb import OracleVecDB, Configuration  # type: ignore[attr-defined]
from oracle_vecdb.services.ords.exceptions import (
    ApiException,
    NotFoundException,
)
from pydantic import BaseModel
from transformers import AutoModel, AutoTokenizer

from config import (
    ORACLE_VECDB_REST_URL,
    ORACLE_VECDB_USERNAME,
    ORACLE_VECDB_ACCESS_TOKEN,
    ORACLE_VECDB_PASSWORD,
    ORACLE_TABLE_NAME,
    ORACLE_VECTOR_DIM,
    ORACLE_DISTANCE_METRIC,
)


def _build_oracle_client() -> OracleVecDB:
    config_kwargs = {"rest_url": ORACLE_VECDB_REST_URL}
    if ORACLE_VECDB_ACCESS_TOKEN:
        # Bearer-token authentication takes precedence when VECDB_ACCESS_TOKEN is set.
        config_kwargs["access_token"] = ORACLE_VECDB_ACCESS_TOKEN
    else:
        config_kwargs["username"] = ORACLE_VECDB_USERNAME
        config_kwargs["password"] = ORACLE_VECDB_PASSWORD
    config = Configuration(**config_kwargs)

    if os.getenv("VECDB_SELF_SIGNED_SSL", "false").lower() == "true":
        config.verify_ssl = False

    return OracleVecDB(config)


def _normalize_result_item(item: dict) -> dict:
    normalized = {
        key: ("" if value is None else value) for key, value in item.items()
    }
    metadata = normalized.get("metadata", {}) or {}
    if isinstance(metadata, dict):
        normalized["metadata"] = {
            key: ("" if value is None else value)
            for key, value in metadata.items()
        }
    return normalized


def _as_dict(value: object) -> dict:
    if isinstance(value, dict):
        return value
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if hasattr(value, "to_dict"):
        return value.to_dict()
    return {}


def _ensure_vector_table(vecdb_client: OracleVecDB) -> None:
    try:
        vecdb_client.describe_vector_table(name=ORACLE_TABLE_NAME)
    except NotFoundException:
        annotations = {
            "dimension": str(ORACLE_VECTOR_DIM),
            "metric": ORACLE_DISTANCE_METRIC,
            "createdAt": datetime.now(timezone.utc).isoformat(),
        }
        try:
            vecdb_client.create_vector_table(
                name=ORACLE_TABLE_NAME,
                comment="Semantic Code Search embeddings",
                annotations=annotations,
            )
        except ApiException as exc:
            if getattr(exc, "status", None) != 409:
                raise


vecdb_client = _build_oracle_client()


class JinaCodeEmbedding(Embeddings):
    def __init__(self, model_name: str = "jinaai/jina-embeddings-v2-base-code"):
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModel.from_pretrained(
            model_name, trust_remote_code=True
        )
        self.model.eval()

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        embeddings = self._embed(texts)
        return embeddings.tolist()

    def embed_query(self, text: str) -> List[float]:
        embeddings = self._embed([text])
        return embeddings[0].tolist()

    def _embed(self, texts: List[str]) -> torch.Tensor:
        encoded_input = self.tokenizer(
            texts, padding=True, truncation=True, return_tensors="pt"
        )
        with torch.no_grad():
            model_output = self.model(**encoded_input)
        token_embeddings = model_output[0]
        input_mask_expanded = (
            encoded_input["attention_mask"]
            .unsqueeze(-1)
            .expand(token_embeddings.size())
            .float()
        )
        embeddings = torch.sum(
            token_embeddings * input_mask_expanded, 1
        ) / torch.clamp(input_mask_expanded.sum(1), min=1e-9)
        return F.normalize(embeddings, p=2, dim=1)


def _normalize_for_response(metadata: dict) -> "Metadata":
    line_start = metadata.get("line_from")
    line_end = metadata.get("line_to")

    if line_start == "<anonymous>":
        line_start = 0

    if line_end == "<anonymous>":
        line_end = 0

    function_name = metadata.get("context_name", "")
    if function_name == "<anonymous>":
        function_name = metadata.get("context_snippet_type", "")

    return Metadata(
        fileName=metadata.get("context_file_name", ""),
        filePath=metadata.get("context_file_path", ""),
        language=metadata.get("context_language", ""),
        functionName=function_name,
        lineStart=int(line_start or 0),
        lineEnd=int(line_end or 0),
    )


embedding_model = JinaCodeEmbedding()

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class Metadata(BaseModel):
    fileName: str
    filePath: str
    language: str
    functionName: Optional[str]
    lineStart: int
    lineEnd: int


class CodeSearchResult(BaseModel):
    id: str
    content: str
    score: float
    metadata: Metadata


class VectorIndexInfo(BaseModel):
    name: str
    dimension: int
    metric: str
    totalVectors: int
    createdAt: str
    lastUpdated: str


@app.on_event("startup")
async def startup_event() -> None:
    _ensure_vector_table(vecdb_client)


@app.get("/code-search", response_model=List[CodeSearchResult])
def code_search(
    query: str = Query(..., description="Search query"),
    top_k: int = Query(5, description="Number of top results to return"),
):
    embedding = embedding_model.embed_query(query)
    try:
        response = vecdb_client.query(
            table_name=ORACLE_TABLE_NAME,
            query_by={"vector": embedding},
            top_k=top_k,
            include_vectors=False,
        )
    except NotFoundException:
        raise HTTPException(status_code=404, detail="Vector table not found")
    except ApiException as exc:
        raise HTTPException(
            status_code=502, detail=f"Oracle VecDB query failed: {exc}"
        )

    results = []
    if isinstance(response, list):
        items = response
    else:
        response_dict = _as_dict(response)
        items = (
            response_dict.get("items")
            or response_dict.get("result")
            or response_dict.get("results")
            or []
        )

    for item in items:
        normalized = _as_dict(item)
        normalized = _normalize_result_item(normalized)
        metadata = normalized.get("metadata", {})
        doc_content = metadata.get("context_code", "")
        distance = normalized.get("distance")
        if distance is None:
            distance = 1.0
        score_value = float(max(0.0, min(1.0, distance)))

        results.append(
            CodeSearchResult(
                id=str(normalized.get("id", uuid4())),
                content=doc_content,
                score=round(score_value, 4),
                metadata=_normalize_for_response(metadata),
            )
        )

    print(f"Returning {len(results)} results")
    return results


@app.get("/vector-db-info", response_model=VectorIndexInfo)
def vector_db_info():
    try:
        table = vecdb_client.describe_vector_table(name=ORACLE_TABLE_NAME)
        print(table)
        table_info = table if isinstance(table, dict) else table.to_dict()

        annotations = table_info.get("annotations", {}) or {}
        dimension = annotations.get("dimension", ORACLE_VECTOR_DIM)
        metric = annotations.get("metric", ORACLE_DISTANCE_METRIC)
        total_vectors = annotations.get("vector_count")

        if total_vectors is None:
            summary = vecdb_client.describe_vector_database()
            summary_info = (
                summary if isinstance(summary, dict) else summary.to_dict()
            )
            total_vectors = summary_info.get("total_vectors", 0)

        created_at = (
            annotations.get("createdAt")
            or datetime.now(timezone.utc).isoformat()
        )
        last_updated = (
            annotations.get("lastUpdated")
            or datetime.now(timezone.utc).isoformat()
        )

        return VectorIndexInfo(
            name=ORACLE_TABLE_NAME,
            dimension=int(dimension),
            metric=str(metric),
            totalVectors=int(total_vectors or 0),
            createdAt=str(created_at),
            lastUpdated=str(last_updated),
        )
    except NotFoundException:
        raise HTTPException(
            status_code=404,
            detail=f"Vector table '{ORACLE_TABLE_NAME}' not found.",
        )
    except ApiException as exc:
        raise HTTPException(
            status_code=500, detail=f"Failed to read vector stats: {exc}"
        )


code_dir = os.getenv("CODE_DIR")
if not code_dir:
    raise EnvironmentError("The CODE_DIR environment variable is not set.")

BASE_CODE_DIR = Path(code_dir).resolve()
IGNORE_DIRS = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    ".idea",
    ".vscode",
}

EXT_TO_LANG = {
    ".py": "python",
    ".ts": "typescript",
    ".tsx": "tsx",
    ".js": "javascript",
    ".jsx": "jsx",
    ".json": "json",
    ".md": "markdown",
    ".txt": "text",
}


class FileNodeModel(BaseModel):
    id: str
    name: str
    type: Literal["file", "folder"]
    path: str
    children: Optional[List["FileNodeModel"]] = None
    content: Optional[str] = None
    language: Optional[str] = None


FileNodeModel.model_rebuild()


def _hash_path(path: Path) -> str:
    return hashlib.sha256(str(path).encode("utf-8")).hexdigest()


def _lang_for(path: Path) -> Optional[str]:
    return EXT_TO_LANG.get(path.suffix.lower())


def build_file_tree(root: Path) -> FileNodeModel:
    root = root.resolve()
    children: List[FileNodeModel] = []

    for entry in sorted(
        root.iterdir(), key=lambda p: (p.is_file(), p.name.lower())
    ):
        if entry.name in IGNORE_DIRS:
            continue

        if entry.is_dir():
            children.append(build_file_tree(entry))
        else:
            children.append(
                FileNodeModel(
                    id=_hash_path(entry),
                    name=entry.name,
                    type="file",
                    path=str(entry),
                    language=_lang_for(entry),
                )
            )

    return FileNodeModel(
        id=_hash_path(root),
        name=root.name,
        type="folder",
        path=str(root),
        children=children or None,
    )


def _ensure_inside_base(requested: Path) -> Path:
    requested = requested.resolve()
    if BASE_CODE_DIR not in requested.parents and requested != BASE_CODE_DIR:
        raise HTTPException(
            status_code=400,
            detail="Path is outside the allowed base directory.",
        )
    return requested


@app.get("/file-tree", response_model=FileNodeModel)
def get_file_tree():
    if not BASE_CODE_DIR.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Base code directory '{BASE_CODE_DIR}' does not exist.",
        )
    return build_file_tree(BASE_CODE_DIR)


@app.get("/file-content")
def get_file_content(path: str):
    requested = _ensure_inside_base(BASE_CODE_DIR / path)
    if not requested.exists() or not requested.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    return {
        "path": str(requested),
        "language": _lang_for(requested),
        "content": requested.read_text(encoding="utf-8", errors="ignore"),
    }


@app.get("/code-context")
def get_code_context(
    path: str, start: int, end: int, pre: int = 6, post: int = 5
):
    requested = _ensure_inside_base(BASE_CODE_DIR / path)
    if not requested.exists() or not requested.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    try:
        lines = requested.read_text(
            encoding="utf-8", errors="ignore"
        ).splitlines()
        start_line = max(0, int(start) - int(pre))
        end_line = min(len(lines), int(end) + int(post))
        context = "\n".join(lines[start_line:end_line])
        return {"context": context}
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc))
