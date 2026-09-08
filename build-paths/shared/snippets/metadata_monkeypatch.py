"""Module-level monkeypatch for langchain-oracledb metadata handling.

Source: apps/agentic_rag/src/OraDBVectorStore.py:10-48 (oracle-ai-developer-hub)

WHY THIS EXISTS
---------------
Oracle stores OracleVS metadata as VARCHAR2/JSON. When read back, oracledb
returns it as a Python *string*, but the langchain-oracledb internals expect a
dict. Filtered retrievals then fail with `AttributeError: 'str' object has no
attribute 'pop'` — silent in some code paths, loud in others.

This patch sits in front of `_read_similarity_output` (the module-level
function — patching the class no-ops) and parses the metadata column to a dict
before the library sees it.

Apply ONCE, near the top of your project's main module or `store.py`. Importing
this file is enough — the patch runs at import time.
"""

from __future__ import annotations

import json

try:
    import langchain_oracledb.vectorstores.oraclevs as _vs_module

    _orig_read_similarity_output = _vs_module._read_similarity_output

    def _fixed_read_similarity_output(
        results,
        has_similarity_score: bool = False,
        has_embeddings: bool = False,
    ):
        fixed = []
        for row in results:
            if len(row) >= 2:
                row_list = list(row)
                metadata = row_list[1]
                if isinstance(metadata, str):
                    try:
                        row_list[1] = json.loads(metadata)
                    except Exception:
                        # Leave as-is; downstream may surface it.
                        pass
                fixed.append(tuple(row_list))
            else:
                fixed.append(row)
        return _orig_read_similarity_output(fixed, has_similarity_score, has_embeddings)

    _vs_module._read_similarity_output = _fixed_read_similarity_output
except Exception as e:  # noqa: BLE001 — this must never crash the host process
    print(f"[build-paths] failed to apply OracleVS metadata monkeypatch: {e}")
