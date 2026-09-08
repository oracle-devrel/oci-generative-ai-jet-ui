"""Orchestrates the full file -> knowledge base pipeline."""

import os
import time
import uuid
from datetime import datetime


class FileIngestor:
    """Extract -> chunk -> embed -> store pipeline."""

    def __init__(
        self, file_processor, chunker, knowledge_base_vs, socketio=None, query_logger=None
    ):
        self.processor = file_processor
        self.chunker = chunker
        self.knowledge_base_vs = knowledge_base_vs
        self.socketio = socketio
        self.query_logger = query_logger

    def ingest(self, filepath, thread_id, upload_id=None):
        """Full pipeline: extract -> chunk -> embed -> store in OracleVS."""
        upload_id = upload_id or str(uuid.uuid4())[:8]
        filename = os.path.basename(filepath)
        file_type = os.path.splitext(filename)[1].lower().lstrip(".")

        # 1. Extract text
        self._emit_progress(filename, "extracting", 0, 0)
        raw_text = self.processor.extract(filepath)
        text_len = len(raw_text)

        # 2. Chunk
        self._emit_progress(filename, "chunking", 0, 0)
        chunks = self.chunker.chunk(raw_text)
        total_chunks = len(chunks)

        # 3. Build metadata for each chunk
        texts = []
        metadatas = []
        for i, chunk_text in enumerate(chunks):
            texts.append(chunk_text)
            metadatas.append(
                {
                    "source_file": filename,
                    "file_type": file_type,
                    "chunk_index": i,
                    "total_chunks": total_chunks,
                    "thread_id": thread_id,
                    "upload_id": upload_id,
                    "upload_timestamp": datetime.now().isoformat(),
                    "source_type": "user_upload",
                }
            )

            if (i + 1) % 5 == 0 or i == total_chunks - 1:
                self._emit_progress(filename, "embedding", i + 1, total_chunks)

        # 4. Store in OracleVS
        self._emit_progress(filename, "storing", total_chunks, total_chunks)
        insert_start = time.time()
        self.knowledge_base_vs.add_texts(texts=texts, metadatas=metadatas)
        insert_elapsed = round((time.time() - insert_start) * 1000, 1)

        # 5. Log the ingestion as a database query event
        self._log_ingestion_query(filename, total_chunks, text_len, insert_elapsed, upload_id)

        # 6. Emit completion
        if self.socketio:
            self.socketio.emit(
                "file_processing_complete",
                {
                    "filename": filename,
                    "chunks_created": total_chunks,
                    "status": "indexed",
                },
            )

        return {
            "filename": filename,
            "file_type": file_type,
            "chunks_created": total_chunks,
            "upload_id": upload_id,
            "status": "indexed",
        }

    def _log_ingestion_query(self, filename, chunk_count, text_len, elapsed_ms, upload_id):
        """Emit a synthetic query_executed event for the Database pane."""
        if not self.socketio:
            return

        import eventlet

        # Synthetic SQL showing what the OracleVS INSERT did
        synthetic_sql = f"""\
-- OracleVS Bulk Insert: {filename}
-- Extracted {text_len:,} chars -> {chunk_count} chunks (1000 char/chunk, 200 overlap)
-- Each chunk embedded with sentence-transformers/paraphrase-mpnet-base-v2 (768 dim)

INSERT INTO KNOWLEDGE_BASE (id, text, metadata, embedding)
VALUES (:id, :chunk_text, :metadata_json, :embedding_vector)
-- x{chunk_count} rows with HNSW vector index update"""

        query_record = {
            "id": upload_id,
            "type": "vector",
            "sql": synthetic_sql,
            "params": None,
            "elapsed_ms": elapsed_ms,
            "result_count": chunk_count,
            "top_result_preview": [
                {
                    "operation": "INSERT",
                    "table": "KNOWLEDGE_BASE",
                    "chunks": str(chunk_count),
                    "source": filename,
                }
            ],
            "timestamp": time.time(),
            "description": f"Document ingestion: {filename} ({chunk_count} chunks)",
        }

        # Also add to query_logger if available
        if self.query_logger:
            self.query_logger.queries.append(query_record)

        self.socketio.emit("query_executed", query_record)
        eventlet.sleep(0)

    def _emit_progress(self, filename, stage, processed, total):
        if self.socketio:
            self.socketio.emit(
                "file_processing_progress",
                {
                    "filename": filename,
                    "stage": stage,
                    "chunks_processed": processed,
                    "total_chunks": total,
                },
            )
