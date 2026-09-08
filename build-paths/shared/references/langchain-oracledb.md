# `langchain-oracledb` — the load-bearing library for beginner + intermediate paths

This is the package the beginner path is built on top of. Beginners never write raw `oracledb` cursor code; they write LangChain calls that happen to be backed by Oracle. Intermediate users learn the multi-collection / retriever / chat-history features.

Install: `pip install langchain-oracledb langchain-ollama` (intermediate adds `langchain-openai` for OCI's OpenAI-compatible endpoint).

## The 5-line beginner sermon

Every beginner project collapses to this shape. The skill teaches it before anything else.

```python
import oracledb
from langchain_oracledb import OracleVS
from langchain_oracledb.utils.distance_strategy import DistanceStrategy
from langchain_ollama import OllamaEmbeddings

conn = oracledb.connect(user="SYSTEM", password=PWD, dsn="localhost:1521/FREEPDB1")
vs = OracleVS.from_texts(
    texts=["bookmark 1 description", "bookmark 2 description"],
    embedding=OllamaEmbeddings(model="nomic-embed-text"),
    client=conn,
    table_name="BOOKMARKS",
    distance_strategy=DistanceStrategy.COSINE,
)
hits = vs.similarity_search("what was that thing about langchain?", k=3)
```

What this hides (and why that's the point):
- Table creation (DDL) — `from_texts` issues `CREATE TABLE ... VECTOR(...)` itself.
- Embedding-dim discovery — picked from the embedder, not declared by the user.
- `array.array("f", qv)` bind-variable wrangling for vectors — internal.
- `VECTOR_DISTANCE(... COSINE)` SQL — wrapped by `similarity_search`.

## Beginner methods (teach in this order)

| Method | Use when | Notes |
| --- | --- | --- |
| `OracleVS.from_texts(texts, embedding, client, table_name, distance_strategy)` | First time — seed the store. | Creates the table if missing. |
| `vs.add_texts(texts, metadatas=None)` | After the store exists, append. | Pass `metadatas=[{"source": "..."}]` to attach searchable tags. |
| `vs.similarity_search(query, k=3)` | Default search. | Returns `Document` objects with `.page_content` and `.metadata`. |
| `vs.similarity_search_with_score(query, k=3)` | When you want to show confidence. | Returns `(doc, score)` tuples. Lower = closer for COSINE. |
| `vs.as_retriever(search_kwargs={"k": 5})` | Hooking into LangChain chains. | Optional for beginners — bridge to intermediate. |

## Intermediate features (teach when the user is ready for RAG)

### Multi-collection pattern

One DB, many tables, all wrapped behind one class. Source: `apps/agentic_rag/src/OraDBVectorStore.py:1-100`. The skill copies the pattern down to a smaller wrapper:

```python
class ProjectStore:
    COLLECTIONS = {"PDF": "PROJECT_PDF_DOCS", "WEB": "PROJECT_WEB_DOCS"}
    def __init__(self, conn, embedding):
        self.stores = {
            kind: OracleVS(client=conn, embedding_function=embedding,
                           table_name=table, distance_strategy=DistanceStrategy.COSINE)
            for kind, table in self.COLLECTIONS.items()
        }
    def add(self, kind, texts, metadatas=None):
        self.stores[kind].add_texts(texts, metadatas=metadatas)
    def search(self, kind, query, k=5, filter=None):
        return self.stores[kind].similarity_search(query, k=k, filter=filter)
```

Naming convention the skill enforces: `<PROJECT>_<KIND>` so two projects on the same DB don't collide. E.g. `WIKI_RAW_NOTES`, `WIKI_SUMMARIES`, `BOOKMARKS_TITLES`.

### Metadata filtering

```python
vs.similarity_search("authentication flow", k=5,
                     filter={"source": "auth-handbook.pdf"})
```

**The non-negotiable monkeypatch.** Oracle returns metadata as `VARCHAR2`, so without this, `.metadata` is a string-of-JSON instead of a dict. Filtered retrievals silently miss. The patch target is the **module-level function** `langchain_oracledb.vectorstores.oraclevs._read_similarity_output`, not a class method — patching the class will silently no-op. Verbatim from `apps/agentic_rag/src/OraDBVectorStore.py:10-48`:

```python
# --- MONKEYPATCH BEGIN ---
# Fix for AttributeError: 'str' object has no attribute 'pop'.
# OracleVS expects metadata as dict, but VARCHAR2/JSON storage returns a
# string via oracledb. Pre-parse it to a dict before the library sees it.
try:
    import json
    import langchain_oracledb.vectorstores.oraclevs as vs_module

    _orig = vs_module._read_similarity_output

    def _fixed_read_similarity_output(results, has_similarity_score=False, has_embeddings=False):
        fixed = []
        for row in results:
            if len(row) >= 2:
                row_list = list(row)
                metadata = row_list[1]
                if isinstance(metadata, str):
                    try:
                        row_list[1] = json.loads(metadata)
                    except Exception:
                        pass
                fixed.append(tuple(row_list))
            else:
                fixed.append(row)
        return _orig(fixed, has_similarity_score, has_embeddings)

    vs_module._read_similarity_output = _fixed_read_similarity_output
except Exception as e:
    print(f"[OraDB] failed to apply metadata monkeypatch: {e}")
# --- MONKEYPATCH END ---
```

The intermediate skill always inserts this snippet near the top of the user's main module (or `store.py`). Non-negotiable. Note the real signature accepts `(results, has_similarity_score, has_embeddings)` — earlier prose versions of this file showed an instance-method shape that does **not** apply to the module-level function and silently no-ops.

### Hybrid retrieval via `EnsembleRetriever`

Layer LangChain's BM25 retriever on top of `OracleVS.as_retriever()` so the user gets reciprocal-rank-fusion behavior without writing SQL.

```python
from langchain.retrievers import EnsembleRetriever, BM25Retriever

vector_r = vs.as_retriever(search_kwargs={"k": 10})
bm25_r = BM25Retriever.from_documents(all_docs); bm25_r.k = 10
hybrid = EnsembleRetriever(retrievers=[vector_r, bm25_r], weights=[0.6, 0.4])
docs = hybrid.invoke("what does the security policy say about MFA?")
```

For users who want raw-SQL hybrid search (more control, less LangChain), the skill points at `apps/finance-ai-agent-demo/backend/retrieval/hybrid_search.py:1-80`.

### Persistent chat history

`langchain-oracledb` does **not** ship a chat-message-history class as of this writing — its top-level submodules are only `document_loaders`, `embeddings`, `retrievers`, `utilities`, `vectorstores`. So we roll a tiny one ourselves on top of `oracledb` + LangChain's `BaseChatMessageHistory`. This is intentional: the class is small, the storage shape is project-specific, and it keeps the dep surface honest.

```python
import json
import oracledb
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import BaseMessage, messages_from_dict, messages_to_dict


class OracleChatHistory(BaseChatMessageHistory):
    """Persistent chat history backed by an Oracle table.

    DDL (run once, e.g. in store.py bootstrap):
        CREATE TABLE chat_history (
            session_id VARCHAR2(120) NOT NULL,
            seq        NUMBER GENERATED ALWAYS AS IDENTITY,
            payload    CLOB CHECK (payload IS JSON),
            created_at TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
            PRIMARY KEY (session_id, seq)
        );
    """

    def __init__(self, conn: oracledb.Connection, session_id: str,
                 table_name: str = "chat_history"):
        self.conn = conn
        self.session_id = session_id
        self.table = table_name

    @property
    def messages(self) -> list[BaseMessage]:
        with self.conn.cursor() as cur:
            cur.execute(
                f"SELECT payload FROM {self.table} "
                f"WHERE session_id = :sid ORDER BY seq",
                sid=self.session_id,
            )
            rows = [json.loads(r[0].read() if hasattr(r[0], "read") else r[0])
                    for r in cur.fetchall()]
        return messages_from_dict(rows)

    def add_message(self, message: BaseMessage) -> None:
        payload = json.dumps(messages_to_dict([message])[0])
        with self.conn.cursor() as cur:
            cur.execute(
                f"INSERT INTO {self.table} (session_id, payload) VALUES (:sid, :p)",
                sid=self.session_id, p=payload,
            )
        self.conn.commit()

    def clear(self) -> None:
        with self.conn.cursor() as cur:
            cur.execute(f"DELETE FROM {self.table} WHERE session_id = :sid",
                        sid=self.session_id)
        self.conn.commit()
```

Wire into a chain via LangChain's `RunnableWithMessageHistory`:

```python
from langchain_core.runnables.history import RunnableWithMessageHistory

chain_with_history = RunnableWithMessageHistory(
    chain,
    lambda sid: OracleChatHistory(conn, session_id=sid),
    input_messages_key="question",
    history_messages_key="history",
)
chain_with_history.invoke({"question": "..."},
                          config={"configurable": {"session_id": "user-42"}})
```

The intermediate skill scaffolds this class verbatim into the project's `history.py`. Don't try to import from `langchain_oracledb.chat_message_histories` — it isn't there.

### `add_documents` vs `from_texts`

| Use | When |
| --- | --- |
| `from_texts(texts=..., embedding=..., client=..., table_name=...)` | Bootstrap. Creates the table. |
| `OracleVS(client=..., embedding_function=..., table_name=...)` + `vs.add_documents(docs)` | After bootstrap, when you have `Document` objects already. |
| `vs.add_texts(texts, metadatas=...)` | After bootstrap, simple text append. |

### `delete()` and async (`aget_relevant_documents`)

Mention only; don't make the user implement either unless they ask. They exist; here's where to read up.

## Distance strategies

`DistanceStrategy.COSINE` is the default the skill picks. Alternatives: `EUCLIDEAN`, `DOT_PRODUCT`, `MANHATTAN`. Don't switch unless the user has a reason.

**Score interpretation gotcha:** for COSINE, `similarity_search_with_score` returns *distance*, not similarity. Closer to 0 = better. If the user wants a 0-1 confidence number, the skill applies `1 - distance` after clipping to [0, 1].

## Embedding-dim must match

If the user later swaps embedders (e.g. nomic-embed-text → Cohere v3) the table dim won't match and inserts will fail with `ORA-51805` or similar. Either:
- Drop the table and re-bootstrap with `from_texts`, or
- Use a different `table_name` per embedder.

The skill enforces one embedder per table_name and refuses to run if it sees a mismatch (it queries `USER_TAB_COLUMNS` to check).

## Don't drop below LangChain unless the user asks

When something feels limited (e.g. "I want a custom hybrid score"), the *first* answer is "let's stay in LangChain and use `EnsembleRetriever` / a custom `BaseRetriever` subclass." Only drop to raw `oracledb` + SQL when the user explicitly wants control or the LangChain API can't express it.

## Exemplars

| Pattern | File |
| --- | --- |
| Minimal `add_texts` + `similarity_search` | `~/git/work/ai-solutions/apps/langflow-agentic-ai-oracle-mcp-vector-nl2sql/components/vectorstores/oracledb_vectorstore.py` |
| Multi-collection wrapper | `apps/agentic_rag/src/OraDBVectorStore.py:1-100` |
| Metadata-as-string monkeypatch | `apps/agentic_rag/src/OraDBVectorStore.py` (same file) |
| Hybrid retrieval blending | `apps/limitless-workflow/src/limitless/research/vector_store.py` |
