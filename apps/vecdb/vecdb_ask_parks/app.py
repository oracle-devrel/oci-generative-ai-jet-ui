#!/usr/bin/env python3
"""Ask the Parks: a dependency-free spatial + vector search demo."""

from __future__ import annotations

import csv
import json
import math
import os
import re
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from dotenv import load_dotenv

ROOT = Path(__file__).parent
load_dotenv(ROOT / ".env", override=True)
DATA_FILE = ROOT / "data" / "us_national_parks_dataset_spatial.csv"
TOKEN_RE = re.compile(r"[a-z]{2,}")
VECDB_REST_URL = os.getenv("VECDB_REST_URL")
VECDB_TABLE = os.getenv("VECDB_TABLE")
VECDB_ACCESS_TOKEN = os.getenv("VECDB_ACCESS_TOKEN")
VECDB_USERNAME = os.getenv("VECDB_USERNAME")
VECDB_PASSWORD = os.getenv("VECDB_PASSWORD")
VECDB_SELF_SIGNED_SSL = (
    os.getenv("VECDB_SELF_SIGNED_SSL", "false").lower() == "true"
)
VECDB_CLIENT = None

STOP_WORDS = {
    "and",
    "are",
    "for",
    "from",
    "near",
    "park",
    "parks",
    "the",
    "this",
    "that",
    "with",
    "within",
    "find",
    "show",
    "want",
    "looking",
    "place",
    "places",
}
SYNONYMS = {
    "kid": {"family", "children", "young", "visitor"},
    "family": {"children", "young", "visitor"},
    "hike": {"trail", "trails", "walking"},
    "waterfall": {"falls", "water", "river", "creek"},
    "desert": {"arid", "canyon", "desert"},
    "coast": {"ocean", "coastal", "beach", "shore"},
    "mountain": {"mountains", "alpine", "peak", "peaks"},
    "history": {"historic", "historical", "heritage", "memorial"},
}


def tokens(value: str) -> set[str]:
    result = set(TOKEN_RE.findall(value.lower())) - STOP_WORDS
    for term in list(result):
        result.update(SYNONYMS.get(term, set()))
    return result


def cosine(left: list[float], right: list[float]) -> float:
    numerator = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    return (
        numerator / (left_norm * right_norm)
        if left_norm and right_norm
        else 0.0
    )


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371.0088
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi, delta_lambda = math.radians(lat2 - lat1), math.radians(
        lon2 - lon1
    )
    value = (
        math.sin(delta_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    )
    return radius * 2 * math.atan2(math.sqrt(value), math.sqrt(1 - value))


def json_safe(value):
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, list):
        return [json_safe(item) for item in value]
    if isinstance(value, dict):
        return {key: json_safe(item) for key, item in value.items()}
    return value


def load_parks() -> list[dict]:
    parks = []
    with DATA_FILE.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            metadata = json_safe(json.loads(row["METADATA"]))
            location = metadata.get("location", {})
            coordinates = location.get("coordinates")
            if not coordinates or len(coordinates) != 2:
                continue
            park = {
                "id": row["ID"],
                "vector": json.loads(row["DENSE_VECTOR"]),
                "metadata": metadata,
                "name": metadata.get("NAME", "Unnamed park"),
                "full_name": metadata.get(
                    "FULL_NAME", metadata.get("NAME", "Unnamed park")
                ),
                "description": metadata.get("DESCRIPTION", ""),
                "designation": metadata.get("DESIGNATION")
                or "National Park Service site",
                "states": metadata.get("STATES", ""),
                "url": metadata.get("URL", ""),
                "longitude": float(coordinates[0]),
                "latitude": float(coordinates[1]),
            }
            park["search_terms"] = tokens(
                " ".join(
                    [
                        park["name"],
                        park["full_name"],
                        park["description"],
                        park["designation"],
                        park["states"],
                    ]
                )
            )
            parks.append(park)
    return parks


PARKS = load_parks()


def vecdb_is_configured() -> bool:
    return bool(
        VECDB_REST_URL
        and VECDB_TABLE
        and (VECDB_ACCESS_TOKEN or (VECDB_USERNAME and VECDB_PASSWORD))
    )


def vecdb_client():
    """Create the hosted Oracle VecDB client only when the app is configured."""
    global VECDB_CLIENT
    if not vecdb_is_configured():
        return None
    if VECDB_CLIENT is None:
        try:
            from oracle_vecdb import Configuration, OracleVecDB
        except ImportError as error:
            raise RuntimeError(
                "Oracle VecDB is configured, but the oracle_vecdb SDK is unavailable."
            ) from error
        credentials = (
            {"access_token": VECDB_ACCESS_TOKEN}
            if VECDB_ACCESS_TOKEN
            else {"username": VECDB_USERNAME, "password": VECDB_PASSWORD}
        )
        configuration = Configuration(rest_url=VECDB_REST_URL, **credentials)
        if VECDB_SELF_SIGNED_SSL:
            configuration.verify_ssl = False
        VECDB_CLIENT = OracleVecDB(configuration)
    return VECDB_CLIENT


def query_vector(
    query_terms: set[str],
) -> tuple[list[float] | None, dict[str, float]]:
    lexical_scores = {}
    weighted = [0.0] * len(PARKS[0]["vector"])
    total_weight = 0.0
    for park in PARKS:
        overlap = len(query_terms & park["search_terms"])
        score = overlap / max(len(query_terms), 1)
        lexical_scores[park["id"]] = score
        if score:
            for index, value in enumerate(park["vector"]):
                weighted[index] += value * score
            total_weight += score
    if not total_weight:
        return None, lexical_scores
    return [value / total_weight for value in weighted], lexical_scores


def search_arguments(args: dict[str, list[str]]) -> dict:
    query = args.get("q", [""])[0].strip()
    state = args.get("state", [""])[0].strip().upper()
    designation = args.get("designation", [""])[0].strip().lower()
    raw_latitude = args.get("lat", [""])[0].strip()
    raw_longitude = args.get("lon", [""])[0].strip()
    has_location = bool(raw_latitude or raw_longitude)
    if has_location and not (raw_latitude and raw_longitude):
        raise ValueError(
            "Provide both latitude and longitude, or leave both blank."
        )
    latitude = float(raw_latitude) if has_location else None
    longitude = float(raw_longitude) if has_location else None
    radius = float(args.get("radius", ["500"])[0]) if has_location else None
    if radius is not None and radius <= 0:
        raise ValueError("Radius must be greater than zero.")
    raw_qbe = args.get("qbe", [""])[0].strip()
    try:
        qbe_filter = json.loads(raw_qbe) if raw_qbe else None
    except json.JSONDecodeError as error:
        raise ValueError(
            f"Metadata QBE must be valid JSON: {error.msg}."
        ) from error
    if qbe_filter is not None and not isinstance(qbe_filter, dict):
        raise ValueError("Metadata QBE must be a JSON object.")
    limit = min(max(int(args.get("limit", ["24"])[0]), 1), 100)
    return {
        "query": query,
        "state": state,
        "designation": designation,
        "has_location": has_location,
        "radius": radius,
        "latitude": latitude,
        "longitude": longitude,
        "limit": limit,
        "qbe_filter": qbe_filter,
    }


def rank_local(search: dict) -> dict:
    query = search["query"]
    state = search["state"]
    designation = search["designation"]
    radius = search["radius"]
    latitude = search["latitude"]
    longitude = search["longitude"]
    limit = search["limit"]
    query_terms = tokens(query)
    vector, lexical_scores = (
        query_vector(query_terms) if query_terms else (None, {})
    )

    results = []
    for park in PARKS:
        if state and state not in {
            part.strip() for part in park["states"].split(",")
        }:
            continue
        if designation and designation not in park["designation"].lower():
            continue
        distance = (
            haversine_km(
                latitude, longitude, park["latitude"], park["longitude"]
            )
            if search["has_location"]
            else None
        )
        if distance is not None and distance > radius:
            continue
        lexical = lexical_scores.get(park["id"], 0.0)
        vector_score = (
            (cosine(vector, park["vector"]) + 1) / 2 if vector else 0.5
        )
        semantic = (
            (0.65 * vector_score) + (0.35 * lexical) if query_terms else 0.5
        )
        proximity = (
            max(0.0, 1 - (distance / radius)) if distance is not None else None
        )
        score = semantic
        results.append(
            {
                "id": park["id"],
                "name": park["name"],
                "full_name": park["full_name"],
                "description": park["description"],
                "designation": park["designation"],
                "states": park["states"],
                "url": park["url"],
                "latitude": park["latitude"],
                "longitude": park["longitude"],
                "distance_km": (
                    round(distance, 1) if distance is not None else None
                ),
                "semantic_score": round(semantic * 100),
                "proximity_score": (
                    round(proximity * 100) if proximity is not None else None
                ),
                "score": round(score * 100),
                "matched_terms": sorted(query_terms & park["search_terms"])[:6],
            }
        )
    results.sort(key=lambda park: park["score"], reverse=True)
    return {
        "engine": "Local vector + GeoJSON fallback",
        "query": query,
        "center": (
            {"latitude": latitude, "longitude": longitude, "radius_km": radius}
            if search["has_location"]
            else None
        ),
        "result_count": len(results),
        "results": results[:limit],
        "db_latency_ms": None,
    }


def item_value(item, key, default=None):
    return (
        item.get(key, default)
        if isinstance(item, dict)
        else getattr(item, key, default)
    )


def rank_vecdb(search: dict) -> dict:
    """Query Oracle VecDB using its hosted text embedding and spatial QBE filter."""
    query = search["query"] or "National Park Service site"
    radius = search["radius"]
    latitude = search["latitude"]
    longitude = search["longitude"]
    limit = search["limit"]
    filters = search["qbe_filter"]
    if search["has_location"]:
        spatial_filter = {
            "location": {
                "$near": {
                    "$geometry": {
                        "type": "Point",
                        "coordinates": [longitude, latitude],
                    },
                    "$distance": radius,
                    "$unit": "KM",
                }
            }
        }
        filters = (
            {"$and": [filters, spatial_filter]} if filters else spatial_filter
        )
    database_started = time.perf_counter()
    response = vecdb_client().query(
        table_name=VECDB_TABLE,
        query_by={"text": query},
        top_k=max(
            limit, 100 if search["state"] or search["designation"] else limit
        ),
        filters=filters,
    )
    database_latency_ms = round(
        (time.perf_counter() - database_started) * 1000, 1
    )
    results = []
    hits = item_value(response, "items", []) or []
    for rank, item in enumerate(hits):
        metadata = item_value(item, "metadata", {}) or {}
        location = metadata.get("location", {})
        coordinates = location.get("coordinates", [])
        if len(coordinates) != 2:
            continue
        park_state = metadata.get("STATES", "")
        park_designation = (
            metadata.get("DESIGNATION") or "National Park Service site"
        )
        if search["state"] and search["state"] not in {
            part.strip() for part in park_state.split(",")
        }:
            continue
        if (
            search["designation"]
            and search["designation"] not in park_designation.lower()
        ):
            continue
        park_latitude, park_longitude = float(coordinates[1]), float(
            coordinates[0]
        )
        distance = (
            haversine_km(latitude, longitude, park_latitude, park_longitude)
            if search["has_location"]
            else None
        )
        if distance is not None and distance > radius:
            continue
        raw_score = item_value(item, "score", None)
        semantic = (
            max(0.0, min(1.0, float(raw_score)))
            if raw_score is not None
            else 1 - (rank / max(len(hits), 1))
        )
        proximity = (
            max(0.0, 1 - (distance / radius)) if distance is not None else None
        )
        score = semantic
        results.append(
            {
                "id": item_value(
                    item, "id", metadata.get("PARK_CODE", str(rank))
                ),
                "name": metadata.get("NAME", "Unnamed park"),
                "full_name": metadata.get(
                    "FULL_NAME", metadata.get("NAME", "Unnamed park")
                ),
                "description": metadata.get("DESCRIPTION", ""),
                "designation": park_designation,
                "states": park_state,
                "url": metadata.get("URL", ""),
                "latitude": park_latitude,
                "longitude": park_longitude,
                "distance_km": (
                    round(distance, 1) if distance is not None else None
                ),
                "semantic_score": round(semantic * 100),
                "proximity_score": (
                    round(proximity * 100) if proximity is not None else None
                ),
                "score": round(score * 100),
                "matched_terms": [],
            }
        )
    results.sort(key=lambda park: park["score"], reverse=True)
    return {
        "engine": f"Oracle VecDB · {VECDB_TABLE}",
        "query": query,
        "center": (
            {"latitude": latitude, "longitude": longitude, "radius_km": radius}
            if search["has_location"]
            else None
        ),
        "result_count": len(results),
        "results": results[:limit],
        "qbe_warning": None,
        "db_latency_ms": database_latency_ms,
    }


def rank_parks(args: dict[str, list[str]]) -> dict:
    started = time.perf_counter()
    search = search_arguments(args)
    result = rank_vecdb(search) if vecdb_is_configured() else rank_local(search)
    total_latency_ms = round((time.perf_counter() - started) * 1000, 1)
    result["latency_ms"] = total_latency_ms
    result["processing_latency_ms"] = max(
        0.0, round(total_latency_ms - (result["db_latency_ms"] or 0), 1)
    )
    if search["qbe_filter"] and not vecdb_is_configured():
        result["qbe_warning"] = (
            "Custom Metadata QBE is sent to Oracle VecDB only; configure VecDB to apply it."
        )
    return result


def park_details(park_id: str) -> dict:
    """Fetch complete metadata for a selected park, using VecDB when configured."""
    if vecdb_is_configured():
        response = vecdb_client().list_vectors(
            table_name=VECDB_TABLE, ids=[park_id]
        )
        items = item_value(response, "items", []) or []
        if not items:
            raise KeyError("Park not found.")
        item = items[0]
        metadata = item_value(item, "metadata", {}) or {}
        return {
            "id": item_value(item, "id", park_id),
            "metadata": metadata,
            "source": "Oracle VecDB",
        }
    for park in PARKS:
        if park["id"] == park_id:
            return {
                "id": park_id,
                "metadata": park["metadata"],
                "source": "Local CSV fallback",
            }
    raise KeyError("Park not found.")


class AppHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/search":
            try:
                body = json.dumps(rank_parks(parse_qs(parsed.query))).encode(
                    "utf-8"
                )
                self.send_response(200)
                self.send_header(
                    "Content-Type", "application/json; charset=utf-8"
                )
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            except (ValueError, KeyError) as error:
                body = json.dumps({"error": str(error)}).encode("utf-8")
                self.send_response(400)
                self.send_header(
                    "Content-Type", "application/json; charset=utf-8"
                )
                self.end_headers()
                self.wfile.write(body)
            return
        if parsed.path.startswith("/api/park/"):
            try:
                body = json.dumps(
                    park_details(
                        unquote(parsed.path.removeprefix("/api/park/"))
                    )
                ).encode("utf-8")
                self.send_response(200)
                self.send_header(
                    "Content-Type", "application/json; charset=utf-8"
                )
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            except (ValueError, KeyError) as error:
                body = json.dumps({"error": str(error)}).encode("utf-8")
                self.send_response(404)
                self.send_header(
                    "Content-Type", "application/json; charset=utf-8"
                )
                self.end_headers()
                self.wfile.write(body)
            return
        if parsed.path == "/":
            self.path = "/static/index.html"
        return super().do_GET()

    def log_message(self, format, *args):
        print("[Ask the Parks]", format % args)


if __name__ == "__main__":
    print("Ask the Parks is running at http://127.0.0.1:8000")
    ThreadingHTTPServer(("127.0.0.1", 8000), AppHandler).serve_forever()
