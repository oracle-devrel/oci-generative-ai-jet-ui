"""Code search, model and indexes: the in-database embedding model, the hybrid vector index and the code lexer.

One hybrid vector index over ccctx_symbols.search_text serves both keyword and semantic matching. The database
computes every vector with the ONNX model; only the published model file is downloaded, once, and no source
code or question text ever leaves the database to be embedded.
"""

import shutil
import urllib.request
from collections.abc import Mapping
from pathlib import Path

import oracledb

from golestan_code_mcp import db
from golestan_code_mcp.config import model_cache, model_url

MODEL = "ALL_MINILM_L12_V2"
DIMENSION = 384

INDEX = "CCCTX_SYMBOLS_HYBRID_IX"
LEXER = "CCCTX_CODE_LEXER"

MODEL_FILE = "all_MiniLM_L12_v2.onnx"
METADATA = '{"function":"embedding","embeddingOutput":"embedding","input":{"input":["DATA"]}}'


class ModelError(ValueError):
    """The embedding model or the hybrid index is missing or could not be set up. Safe to show the user."""


def _state(cur) -> tuple[bool, int | None, bool]:
    """(model loaded, recorded dimension, hybrid index exists)."""
    loaded = cur.execute("select count(*) from user_mining_models where model_name = :m", m=MODEL).fetchone()[0]
    row = cur.execute("select dimension from ccctx_embedding_model where model_name = :m", m=MODEL).fetchone()
    index = cur.execute("select count(*) from user_indexes where index_name = :i", i=INDEX).fetchone()[0]
    return bool(loaded), row[0] if row else None, bool(index)


def require_model(conn) -> None:
    with conn.cursor() as cur:
        loaded, dimension, index = _state(cur)
    if dimension not in (None, DIMENSION):
        raise ModelError(f"model {MODEL} has {dimension} dimensions, expected {DIMENSION}")
    if not (loaded and dimension and index):
        raise ModelError(f"embedding model {MODEL} is not set up; run `ccctx model load`")


def fetch_model(env: Mapping[str, str]) -> Path:
    """The model file in the local cache, downloaded once. A partial download never counts as cached."""
    dest = model_cache(env) / MODEL_FILE
    if dest.is_file() and dest.stat().st_size:
        return dest
    url = model_url(env)
    part = dest.with_name(dest.name + ".part")
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        with urllib.request.urlopen(url, timeout=60) as response, part.open("wb") as out:
            shutil.copyfileobj(response, out, 1 << 20)
    except (OSError, ValueError) as e:
        part.unlink(missing_ok=True)
        raise ModelError(f"could not download the model from {url}: {e}") from None
    part.replace(dest)
    return dest


def _ensure_lexer(cur) -> None:
    """A text lexer that keeps `_` inside words, so `url_for` is one token and not `url` plus the stopword `for`."""
    if cur.execute("select count(*) from ctx_user_preferences where pre_name = :p", p=LEXER).fetchone()[0]:
        return
    cur.execute(f"""begin
                      ctx_ddl.create_preference('{LEXER}', 'BASIC_LEXER');
                      ctx_ddl.set_attribute('{LEXER}', 'PRINTJOINS', '_');
                    end;""")


def load_model(conn, env: Mapping[str, str]) -> str:
    """Load, record and index the model, skipping whatever is already done. Returns a status line."""
    from golestan_code_mcp.wiki import store  # wiki imports this module

    with conn.cursor() as cur:
        loaded, dimension, index = _state(cur)
        if loaded and dimension == DIMENSION and index:
            store.ensure_index(cur)  # an index built before the wiki existed gets its page index here
            return f"model {MODEL} already present ({DIMENSION} dimensions)"
        if not loaded:
            data = fetch_model(env).read_bytes()
            cur.setinputsizes(b=oracledb.DB_TYPE_BLOB)
            cur.execute("begin dbms_vector.load_onnx_model(:m, :b, json(:j)); end;", m=MODEL, b=data, j=METADATA)
        actual = cur.execute(
            f"select vector_dimension_count(vector_embedding({MODEL} using 'hello world' as data)) from dual"
        ).fetchone()[0]
        if actual != DIMENSION:
            raise ModelError(f"model {MODEL} has {actual} dimensions, expected {DIMENSION}")
        if dimension is None:
            cur.execute("insert into ccctx_embedding_model (model_name, dimension) values (:m, :d)",
                        m=MODEL, d=DIMENSION)
            conn.commit()
        if not index:
            _ensure_lexer(cur)
            try:  # SYNC (ON COMMIT): a committed ingest is searchable at once, never half-visible
                cur.execute(
                    f"create hybrid vector index {INDEX} on ccctx_symbols (search_text)"
                    f" parameters ('MODEL {MODEL} VECTOR_IDXTYPE HNSW SYNC (ON COMMIT) LEXER {LEXER}')"
                )
            except oracledb.DatabaseError as e:
                if getattr(e.args[0], "full_code", "") != "ORA-00955":
                    raise ModelError(f"could not build the hybrid index: {db.describe(e)}") from None
        store.ensure_index(cur)
    return f"model {MODEL} loaded ({DIMENSION} dimensions)"
