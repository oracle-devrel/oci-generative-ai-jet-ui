#!/usr/bin/env python3
"""Create and load the Ask the Parks Oracle VecDB table from a CSV URL."""

from __future__ import annotations

import argparse
import csv
import io
import json
import math
import os
import sys
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

from dotenv import load_dotenv

csv.field_size_limit(10_000_000)
load_dotenv(Path(__file__).with_name(".env"), override=True)


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--table", default=os.getenv("VECDB_TABLE", "national_parks")
    )
    parser.add_argument(
        "--embed-model",
        default=os.getenv("VECDB_EMBED_MODEL", "all_MiniLM_L12_v2"),
    )
    parser.add_argument("--csv-url", default=os.getenv("PARKS_CSV_URL"))
    parser.add_argument(
        "--csv-file",
        help="Use a local QBE-ready parks CSV instead of the configured URL.",
    )
    parser.add_argument("--batch-size", type=int, default=50)
    parser.add_argument(
        "--retries",
        type=int,
        default=3,
        help="CSV download attempts before failing.",
    )
    parser.add_argument(
        "--recreate",
        action="store_true",
        help="Drop the named table before creating it.",
    )
    parser.add_argument(
        "--skip-create",
        action="store_true",
        help="Upsert into an existing table without creating it.",
    )
    return parser.parse_args()


def client_from_environment():
    rest_url = os.getenv("VECDB_REST_URL")
    token = os.getenv("VECDB_ACCESS_TOKEN")
    username = os.getenv("VECDB_USERNAME")
    password = os.getenv("VECDB_PASSWORD")
    self_signed_ssl = (
        os.getenv("VECDB_SELF_SIGNED_SSL", "false").lower() == "true"
    )
    if not rest_url or not (token or (username and password)):
        raise SystemExit(
            "Set VECDB_REST_URL and VECDB_ACCESS_TOKEN, or VECDB_REST_URL, VECDB_USERNAME, and VECDB_PASSWORD."
        )
    try:
        from oracle_vecdb import Configuration, OracleVecDB
    except ImportError as error:
        raise SystemExit(
            "The oracle_vecdb SDK is required to run this script."
        ) from error
    credentials = (
        {"access_token": token}
        if token
        else {"username": username, "password": password}
    )
    configuration = Configuration(rest_url=rest_url, **credentials)
    if self_signed_ssl:
        configuration.verify_ssl = False
    return OracleVecDB(configuration)


def strict_json(value):
    """Normalize NaN values that are permitted by Python but not strict JSON."""
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, list):
        return [strict_json(item) for item in value]
    if isinstance(value, dict):
        return {key: strict_json(item) for key, item in value.items()}
    return value


def open_csv(csv_url, csv_file, retries):
    if csv_file:
        path = Path(csv_file).expanduser()
        if not path.is_file():
            raise FileNotFoundError(f"CSV file not found: {path}")
        print(f"Reading local CSV: {path}")
        return path.open("rb")
    if not csv_url:
        raise SystemExit(
            "Set PARKS_CSV_URL in .env or pass --csv-url or --csv-file."
        )

    request = Request(
        csv_url, headers={"User-Agent": "AskTheParksVecDBLoader/1.0"}
    )
    last_error = None
    for attempt in range(1, retries + 1):
        try:
            print(f"Downloading parks CSV (attempt {attempt}/{retries}).")
            return urlopen(request, timeout=60)
        except URLError as error:
            last_error = error
            if attempt < retries:
                time.sleep(2 ** (attempt - 1))
    raise RuntimeError(
        "Could not download the parks CSV from PARKS_CSV_URL."
    ) from last_error


def records(csv_url, csv_file=None, retries=3):
    with open_csv(csv_url, csv_file, retries) as response:
        reader = csv.DictReader(
            io.TextIOWrapper(response, encoding="utf-8-sig", newline="")
        )
        required = {"ID", "DENSE_VECTOR", "METADATA"}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError(
                f"Expected CSV columns {sorted(required)}; found {reader.fieldnames}."
            )
        for row in reader:
            metadata = strict_json(json.loads(row["METADATA"]))
            location = metadata.get("location", {})
            coordinates = location.get("coordinates", [])
            if location.get("type") != "Point" or len(coordinates) != 2:
                raise ValueError(
                    f"Record {row['ID']} does not contain a GeoJSON Point at metadata.location."
                )
            yield {
                "id": row["ID"],
                "dense_vector": json.loads(row["DENSE_VECTOR"]),
                "metadata": metadata,
            }


def batches(items, batch_size):
    batch = []
    for item in items:
        batch.append(item)
        if len(batch) == batch_size:
            yield batch
            batch = []
    if batch:
        yield batch


def create_table(client, args):
    if args.recreate:
        print(f"Dropping {args.table} because --recreate was supplied.")
        client.drop_vector_table(name=args.table)
    print(f"Creating {args.table} with {args.embed_model} for text queries.")
    client.create_vector_table(
        name=args.table,
        embed_params={
            "model": args.embed_model,
            "embed_metadata_jsonpath": "DESCRIPTION",
        },
    )


def main():
    args = parse_args()
    if args.batch_size < 1:
        raise SystemExit("--batch-size must be at least 1.")
    if args.recreate and args.skip_create:
        raise SystemExit("Use either --recreate or --skip-create, not both.")

    client = client_from_environment()
    if not args.skip_create:
        create_table(client, args)

    total = 0
    vector_dimension = None
    for batch in batches(
        records(args.csv_url, args.csv_file, args.retries), args.batch_size
    ):
        dimensions = {len(item["dense_vector"]) for item in batch}
        if len(dimensions) != 1:
            raise ValueError(
                "A batch contains vectors with different dimensions."
            )
        batch_dimension = dimensions.pop()
        if vector_dimension is None:
            vector_dimension = batch_dimension
        elif vector_dimension != batch_dimension:
            raise ValueError(
                "The CSV contains vectors with different dimensions."
            )
        client.upsert_vectors(table_name=args.table, vectors=batch)
        total += len(batch)
        print(f"Upserted {total} parks.")

    print(
        f"Loaded {total} parks into {args.table} ({vector_dimension}-dimension vectors)."
    )
    print(
        "The Ask the Parks app will use this table when VECDB_TABLE matches the table name."
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"Load failed: {error}", file=sys.stderr)
        raise
