[![Jupyter](https://img.shields.io/badge/Jupyter-Notebook-F37626?logo=jupyter&logoColor=white)](#) [![Python 3.10+](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)](#) [![oracle-vecdb](https://img.shields.io/badge/oracle-vecdb-F80000?logo=oracle&logoColor=white)](#) [![Gemini](https://img.shields.io/badge/Gemini-GenAI-4285F4?logo=google&logoColor=white)](#)

# Gemini + VecDB RAG Notebook

`gemini-vecdb-rag.ipynb` demonstrates how to pair Google Gemini for summarization/Q&A with Oracle VecDB for vector storage and retrieval. The walkthrough mirrors enterprise VecDB patterns: ingest documents with Gemini embeddings, run semantic search inside VecDB, and feed the retrieved context back into Gemini for grounded responses.

## Highlights
- Configure the Gemini SDK alongside the standard VecDB `.env` connection cell, logging resolved host/user/model selections at runtime.
- Chunk and embed sample documents with Gemini (default `gemini-embedding-001`), then upsert vectors and rich metadata into VecDB with automatic indexing.
- Run semantic search inside VecDB to retrieve supporting passages, including document IDs and titles for audit-ready responses.
- Prompt Gemini with VecDB search results to produce grounded answers that reference the retrieved evidence.
- Clean up demo artifacts so repeated runs stay deterministic and VecDB remains tidy.

## Prerequisites
- `.env` with VecDB credentials (`VECDB_REST_URL`, `VECDB_USERNAME`, `VECDB_PASSWORD`).
- Gemini API key via `GOOGLE_API_KEY`. Optional overrides: `GEMINI_EMBED_MODEL` (default `gemini-embedding-001`) and `GEMINI_CHAT_MODEL` (default `gemini-2.5-flash`).
- Python 3.10+ with `oracle-vecdb`, `python-dotenv`, `pandas`, `google-generativeai`.

Run the notebook top to bottom. The final cleanup cell drops the demo table so reruns start clean, and the optional Q&A helper lets you iterate on questions without rerunning setup.
