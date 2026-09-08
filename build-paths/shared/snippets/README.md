# `shared/snippets/`

Verbatim, copy-pasteable patterns the skills cite. Lives here so projects don't depend on `~/git/personal/...` paths being present on the user's machine.

When a `SKILL.md` says "copy the pattern from X", and X is a `~/`-rooted file, the skill copies the relevant snippet from this directory instead. Each file:

- Has a header comment naming the original source.
- Is small enough to drop into a generated project as-is, with placeholder names the skill substitutes.
- Carries an MIT license note (matches the rest of the project).

## Index

| File | Purpose | Used by | Source |
| --- | --- | --- | --- |
| [`metadata_monkeypatch.py`](./metadata_monkeypatch.py) | Module-level patch that pre-parses Oracle's VARCHAR2 metadata into dicts so OracleVS filtered retrieval works. | intermediate, advanced | `apps/agentic_rag/src/OraDBVectorStore.py:10-48` |
| [`oracle_chat_history.py`](./oracle_chat_history.py) | `BaseChatMessageHistory` subclass storing messages in an Oracle table. Replaces the missing `langchain_oracledb.chat_message_histories`. | intermediate, advanced | `shared/references/langchain-oracledb.md` |
| [`oci_chat_factory.py`](./oci_chat_factory.py) | Dual-auth client factory for OCI's OpenAI-compatible endpoint (`oci-openai` SDK + signer; falls back to bearer token). | intermediate, advanced | `~/git/personal/oci-genai-service/src/oci_genai_service/inference/chat.py:1-95` |
| [`oci_cohere_embeddings.py`](./oci_cohere_embeddings.py) | LangChain `Embeddings` subclass wrapping `GenerativeAiInferenceClient.embed_text` with batching + empty-text filter. | intermediate, advanced | `~/git/personal/oci-genai-service/src/oci_genai_service/inference/embeddings.py:1-60` |
| [`memory_manager.py`](./memory_manager.py) | Six-memory-types pattern (conversational, KB, workflow, toolbox, entity, summary), all Oracle-backed. | advanced | `apps/finance-ai-agent-demo/backend/memory/manager.py:1-100` |
| [`oamp_helpers.py`](./oamp_helpers.py) | OAMP (`oracleagentmemory`) wired to in-DB ONNX (`MY_MINILM_V1`) + Grok-4 over OCI bearer-token. `make_oamp_client(conn)` + `make_oamp_thread(client, user_id, agent_id)`. | advanced (ideas 1 + 2) | `notebooks/agent_memory/oracle_agent_memory_developer_guide_oci.ipynb` |
| [`onnx_loader.py`](./onnx_loader.py) | `DBMS_VECTOR.LOAD_ONNX_MODEL` registration + idempotency check. | advanced (when ONNX in-DB selected) | `~/git/personal/onnx2oracle/src/onnx2oracle/loader.py:15-70` |
| [`forbidden_imports.txt`](./forbidden_imports.txt) | Newline-separated list the advanced verify step greps for. Single source of truth — keep in sync with `shared/verify.md`. | advanced (verify gate) | — |

## Convention

When the skill copies a snippet into the user's project:

1. Open the snippet, replace `__PROJECT__` placeholders with the user's slug, replace `__TABLE__` placeholders with the user's table-name convention.
2. Keep the `# Source:` header comment intact — gives the user a paper trail back to the canonical pattern.
3. Don't reformat. The snippets are tested in their current shape; reformatting risks introducing a subtle bug.

## When to update

- A snippet's upstream source changes meaningfully (bug fix, API change). Re-copy and bump the source line range in the header.
- A skill needs a pattern not in this directory. Add a new file + a row in the index above.
- A snippet stops working against a current `langchain-oracledb` / `oci` / `oracledb` release. Pin the version in the header comment and update.

## License

MIT, same as the rest of `oracle-ai-developer-hub`.
