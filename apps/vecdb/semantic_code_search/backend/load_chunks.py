import ast
import os
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List

import torch
import torch.nn.functional as F
from langchain.embeddings.base import Embeddings
from langchain_core.documents import Document
from tqdm.auto import tqdm
from transformers import AutoModel, AutoTokenizer

from oracle_vecdb import OracleVecDB, Configuration  # type: ignore[attr-defined]
from oracle_vecdb.services.ords.exceptions import (
    ApiException,
    NotFoundException,
)

from config import (
    ORACLE_VECDB_REST_URL,
    ORACLE_VECDB_USERNAME,
    ORACLE_VECDB_ACCESS_TOKEN,
    ORACLE_VECDB_PASSWORD,
    ORACLE_TABLE_NAME,
    ORACLE_DISTANCE_METRIC,
)


def get_python_files(directory):
    py_files = []

    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".py"):
                py_files.append(os.path.join(root, file))
    return py_files


def extract_function_details(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            code = f.read()
        return ast.parse(code)
    except Exception as exc:  # noqa: BLE001
        print(f"Skipping {file_path}: {exc}")
        return None


TRIVIAL_NODE_TYPES = {
    ast.Load,
    ast.Store,
    ast.Del,
    ast.Pass,
    ast.Name,
    ast.Subscript,
    ast.Attribute,
    ast.Constant,
    ast.UnaryOp,
    ast.BinOp,
    ast.Compare,
    ast.arguments,
    ast.keyword,
    ast.arg,
    ast.withitem,
    ast.comprehension,
}

MIN_CHARS = 10


def get_function_snippets(file_path, base_dir):
    parsed_code = extract_function_details(file_path)
    if parsed_code is None:
        return []

    snippets = []
    abs_path = Path(file_path).resolve()
    rel_path = abs_path.relative_to(base_dir)

    for node in ast.walk(parsed_code):
        if isinstance(node, tuple(TRIVIAL_NODE_TYPES)) or isinstance(
            node, ast.Module
        ):
            continue

        try:
            code = ast.unparse(node)
        except Exception:  # noqa: BLE001
            code = "<unparse_failed>"

        code = code.strip()
        if not code or len(code) < MIN_CHARS:
            continue

        snippet_type = type(node).__name__
        line_from = getattr(node, "lineno", "<anonymous>")
        line_to = getattr(node, "end_lineno", "<anonymous>")
        name = getattr(node, "name", "<anonymous>")

        snippets.append(
            {
                "line_from": line_from,
                "line_to": line_to,
                "context": {
                    "snippet_type": snippet_type,
                    "name": name,
                    "code": code,
                    "file_path": str(rel_path),
                    "file_name": os.path.basename(file_path),
                },
            }
        )
    return snippets


def chunk_codebase_to_jsonl(source_dir, output_jsonl):
    all_functions = []
    base_dir = Path(source_dir).resolve()
    for file_path in get_python_files(source_dir):
        all_functions.extend(get_function_snippets(file_path, base_dir))

    with open(output_jsonl, "w", encoding="utf-8") as out_file:
        for func in all_functions:
            out_file.write(json.dumps(func) + "\n")

    print(f"Extracted {len(all_functions)} functions to {output_jsonl}")


code_dir = os.getenv("CODE_DIR")
if not code_dir:
    raise ValueError("Environment variable 'CODE_DIR' not set.")
chunk_codebase_to_jsonl(code_dir, "snippets_output-new.jsonl")

structures = []
with open("snippets_output-new.jsonl", "r", encoding="utf-8") as fp:
    for row in fp:
        entry = json.loads(row)
        structures.append(entry)


def flatten_structure(structure):
    flat = {}

    for key, value in structure.items():
        if isinstance(value, dict):
            for subkey, subvalue in value.items():
                flat[f"{key}_{subkey}"] = (
                    "" if subvalue is None else str(subvalue)
                )
        else:
            flat[key] = "" if value is None else str(value)
    return flat


def convert_code_snippet_to_doc(structures):
    documents = []
    for structure in structures:
        content = structure["context"]["code"]
        flat_metadata = flatten_structure(structure)
        documents.append(Document(page_content=content, metadata=flat_metadata))

    return documents


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


documents = convert_code_snippet_to_doc(structures)
embedding_model = JinaCodeEmbedding()


def _build_vecdb_client() -> OracleVecDB:
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


vecdb_client = _build_vecdb_client()


def _ensure_vector_table() -> None:
    try:
        vecdb_client.describe_vector_table(name=ORACLE_TABLE_NAME)
    except NotFoundException:
        try:
            vecdb_client.create_vector_table(
                name=ORACLE_TABLE_NAME,
                comment="Semantic Code Search embeddings",
            )
        except ApiException as exc:
            if getattr(exc, "status", None) != 409:
                raise


def _normalize_metadata(raw_metadata: dict, content: str) -> dict:
    normalized = {
        key: ("" if value is None else str(value))
        for key, value in raw_metadata.items()
    }
    normalized.setdefault("context_code", content)
    normalized.setdefault(
        "context_language", normalized.get("context_language", "")
    )
    normalized.setdefault(
        "context_file_name", normalized.get("context_file_name", "")
    )
    normalized.setdefault(
        "context_file_path", normalized.get("context_file_path", "")
    )
    normalized.setdefault(
        "lastIndexedAt", datetime.now(timezone.utc).isoformat()
    )
    return normalized


def _upsert_batch(batch: List[dict]) -> None:
    if not batch:
        return
    try:
        vecdb_client.upsert_vectors(table_name=ORACLE_TABLE_NAME, vectors=batch)
    except ApiException as exc:
        raise RuntimeError(f"Failed to upsert vectors: {exc}")


_ensure_vector_table()

BATCH_SIZE = 256
total_upserted = 0
current_batch: List[dict] = []

for doc in tqdm(documents, desc="Embedding snippets"):
    if "id" not in doc.metadata:
        doc.metadata["id"] = str(uuid.uuid4())

    embedding = embedding_model.embed_documents([doc.page_content])[0]
    vector_values = [float(value) for value in embedding]
    metadata = _normalize_metadata(doc.metadata, doc.page_content)

    current_batch.append(
        {
            "id": metadata["id"],
            "dense_vector": vector_values,
            "metadata": metadata,
        }
    )

    if len(current_batch) >= BATCH_SIZE:
        _upsert_batch(current_batch)
        total_upserted += len(current_batch)
        current_batch = []

if current_batch:
    _upsert_batch(current_batch)
    total_upserted += len(current_batch)

try:
    table = vecdb_client.describe_vector_table(name=ORACLE_TABLE_NAME)
    table_info = table if isinstance(table, dict) else table.to_dict()
    description = (
        table_info.get("description") or "Semantic Code Search embeddings"
    )
    annotations = table_info.get("annotations", {}) or {}
    annotations = {
        key: ("" if value is None else str(value))
        for key, value in annotations.items()
    }
    annotations.update(
        {
            "metric": ORACLE_DISTANCE_METRIC,
            "vector_count": str(total_upserted),
            "lastUpdated": datetime.now(timezone.utc).isoformat(),
        }
    )
    vecdb_client.update_vector_table_annotation(
        name=ORACLE_TABLE_NAME,
        comment=description,
        annotations=annotations,
    )
except NotFoundException:
    pass
except ApiException as exc:
    print(f"Warning: failed to update table annotations: {exc}")

print(
    f"Upserted {total_upserted} vectors into Oracle VecDB table '{ORACLE_TABLE_NAME}'."
)
