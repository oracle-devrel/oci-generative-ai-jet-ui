"""verify.py — the gate every build-paths project must pass before "done".

Run this after `docker compose up -d --wait`. It exits non-zero on any failure
and prints exactly one line on success: `verify: OK (...)`.

PLACEHOLDERS the scaffolding skill replaces (in order they appear):
  {{embedder_init}}      — full embedder constructor expression, e.g.
                           HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
                           InDBEmbeddings(model_db_name="MY_MINILM_V1")  (intermediate/advanced)
  {{embedding_dim}}      — integer literal, e.g. 384 for MiniLM-L6-v2
  {{llm_call}}            — chat call expression that returns a non-empty string,
                           e.g. inference.chat_complete([{"role":"user","content":"Reply OK."}])
  {{inference_enabled}}  — Python literal True or False.

The skill ALSO injects the right `import` lines at the top of the file plus
the metadata-as-string monkeypatch from shared/references/langchain-oracledb.md.

Do not edit by hand unless you know what you're doing.
"""
from __future__ import annotations

import os
import sys

import oracledb


def _connect():
    return oracledb.connect(
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        dsn=os.environ["DB_DSN"],
    )


def check_db() -> str:
    with _connect() as conn, conn.cursor() as cur:
        cur.execute("SELECT 1 FROM DUAL")
        if cur.fetchone()[0] != 1:
            raise RuntimeError("DB connect succeeded but SELECT 1 returned wrong value")
    return "db"


def check_vector() -> str:
    """Round-trip one known string through OracleVS and assert it comes back.

    The skill replaces {{embedder_init}} with the concrete embedder and
    {{embedding_dim}} with the integer dim of that embedder.
    """
    from langchain_oracledb.vectorstores.oraclevs import OracleVS
    from langchain_community.vectorstores.utils import DistanceStrategy

    embedder = {{embedder_init}}

    qv = embedder.embed_query("dim check")
    if len(qv) != {{embedding_dim}}:
        raise RuntimeError(
            f"embedder dim mismatch: got {len(qv)}, expected {{embedding_dim}}"
        )

    with _connect() as conn:
        vs = OracleVS.from_texts(
            texts=["build-paths verify smoke test"],
            embedding=embedder,
            client=conn,
            table_name="CYP_VERIFY_SMOKE",
            distance_strategy=DistanceStrategy.COSINE,
        )
        hits = vs.similarity_search("verify smoke test", k=1)
        if not hits or "verify smoke" not in hits[0].page_content.lower():
            raise RuntimeError(f"vector round-trip failed; got {hits!r}")

        # Best-effort cleanup so re-running verify stays idempotent.
        try:
            with conn.cursor() as cur:
                cur.execute("DROP TABLE CYP_VERIFY_SMOKE PURGE")
            conn.commit()
        except Exception:
            pass
    return "vector"


def check_inference() -> str:
    """One deterministic LLM call. Skill replaces {{llm_call}}."""
    text = {{llm_call}}
    if not text or not str(text).strip():
        raise RuntimeError(f"inference returned empty: {text!r}")
    return "inference"


def main() -> int:
    """Run each check, naming the failing step in the error label.

    Each check sets `step` BEFORE invocation so the except block prints the
    actual failing step name (not the last successful one — see friction
    finding P1-4).
    """
    checks = []
    step = "startup"
    try:
        step = "db"
        checks.append(check_db())
        step = "vector"
        checks.append(check_vector())
        if {{inference_enabled}}:
            step = "inference"
            checks.append(check_inference())
    except Exception as e:  # noqa: BLE001 — verify must surface anything
        print(f"verify: FAIL ({step}): {type(e).__name__}: {e}", file=sys.stderr)
        return 1
    print(f"verify: OK ({', '.join(checks)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
