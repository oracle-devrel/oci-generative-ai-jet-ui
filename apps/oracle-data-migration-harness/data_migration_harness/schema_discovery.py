"""MongoDB schema discovery and migration profile selection."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from typing import Any

from data_migration_harness import source_config


@dataclass
class FieldInfo:
    path: str
    types: dict[str, int]
    examples: list[Any] = field(default_factory=list)
    array: bool = False
    vector_dim: int | None = None
    coverage: float = 0.0


@dataclass
class MigrationProfile:
    mode: str
    document_count: int
    sample_size: int
    source: dict
    fields: list[dict]
    vectors: list[dict]
    strategy: dict
    warnings: list[str]

    def to_dict(self) -> dict:
        return asdict(self)


def _type_name(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int) and not isinstance(value, bool):
        return "int"
    if isinstance(value, float):
        return "float"
    if isinstance(value, str):
        return "string"
    if isinstance(value, datetime | date):
        return "date"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return type(value).__name__


def _safe_example(value: Any):
    if isinstance(value, datetime | date):
        return value.isoformat()
    if isinstance(value, list):
        if _is_numeric_vector(value):
            return f"[{len(value)} numeric values]"
        return value[:2]
    if isinstance(value, dict):
        return {k: _safe_example(v) for k, v in list(value.items())[:6]}
    return value


def _is_numeric_vector(value: Any) -> bool:
    return (
        isinstance(value, list)
        and len(value) >= 32
        and all(
            isinstance(v, int | float) and not isinstance(v, bool)
            for v in value[: min(len(value), 256)]
        )
    )


def _walk(value: Any, path: str, seen: dict[str, list[Any]]) -> None:
    if path:
        seen[path].append(value)
    if isinstance(value, dict):
        for k, v in value.items():
            child = f"{path}.{k}" if path else k
            _walk(v, child, seen)
    elif isinstance(value, list):
        arr_path = f"{path}[]" if path else "[]"
        for item in value[:3]:
            seen[arr_path].append(item)
            if isinstance(item, dict):
                for k, v in item.items():
                    _walk(v, f"{arr_path}.{k}", seen)


def assess(sample_size: int = 100) -> MigrationProfile:
    col = source_config.collection()
    count = col.count_documents({})
    docs = list(col.find().limit(sample_size))
    seen: dict[str, list[Any]] = defaultdict(list)
    for doc in docs:
        _walk(doc, "", seen)

    fields: list[dict] = []
    vectors: list[dict] = []
    for path, values in sorted(seen.items()):
        if not path or path == "_id":
            continue
        types = Counter(_type_name(v) for v in values)
        info = {
            "path": path,
            "types": dict(types),
            "examples": [_safe_example(v) for v in values[:2]],
            "coverage": round(len(values) / max(len(docs), 1), 3),
        }
        vector_values = [v for v in values if _is_numeric_vector(v)]
        if vector_values:
            dims = Counter(len(v) for v in vector_values)
            dim, dim_count = dims.most_common(1)[0]
            info["vector_dim"] = dim
            info["vector_coverage"] = round(dim_count / max(len(docs), 1), 3)
            vectors.append({"field": path, "dim": dim, "coverage": info["vector_coverage"]})
        fields.append(info)

    paths = {f["path"] for f in fields}
    rich = all(
        p in paths
        for p in ("name", "category", "price", "reviews[]", "reviews[].rating", "reviews[].text")
    )
    warnings: list[str] = []
    if not vectors:
        warnings.append(
            "No vector-like fields detected. Vector migration will be skipped unless embeddings are generated first."
        )
    if not rich:
        warnings.append(
            "Source does not match the product-review demo shape. The harness will use generic JSON landing and scalar projection."
        )

    mode = "rich_product_reviews" if rich else "generic_json"
    strategy = {
        "landing": "oracle_json_table",
        "relational_projection": True if rich else "scalar_fields_only",
        "duality_view": bool(rich),
        "vector_columns": bool(vectors),
        "memory": True,
    }
    return MigrationProfile(
        mode=mode,
        document_count=count,
        sample_size=len(docs),
        source=source_config.get_source_dict(),
        fields=fields,
        vectors=vectors,
        strategy=strategy,
        warnings=warnings,
    )


def assess_dict(sample_size: int = 100) -> dict:
    return assess(sample_size=sample_size).to_dict()
