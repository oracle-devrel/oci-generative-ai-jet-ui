"""SprawlMemoryManager: 6+1 memory types backed by PostgreSQL, Neo4j, MongoDB, and Qdrant.

Provides the same interface as the Oracle MemoryManager but distributes data
across the four sprawl databases:
- Conversational memory: MongoDB (document store)
- Tool log: PostgreSQL (relational)
- Knowledge base, entity, workflow, toolbox, summary: Qdrant (vector)
- Thread metadata (get_threads): MongoDB
"""

import json as json_lib
import logging
import uuid
from datetime import datetime

from qdrant_client.models import FieldCondition, Filter, MatchValue, PointStruct

logger = logging.getLogger(__name__)


class SprawlMemoryManager:
    """Manages 6 types of memory + tool log using the sprawl database stack.

    Memory types:
    - Conversational: Chat history per thread (MongoDB: conversations collection)
    - Knowledge Base: Searchable documents (Qdrant: knowledge_base)
    - Workflow: Execution patterns (Qdrant: workflow_memory)
    - Toolbox: Available tools (Qdrant: toolbox_memory)
    - Entity: People, places, instruments (Qdrant: entity_memory)
    - Summary: Compressed context snapshots (Qdrant: summary_memory)
    - Tool Log: Tool output offloading (PostgreSQL)
    """

    def __init__(
        self,
        pg_conn,
        qdrant_client,
        embedding_model=None,
        mongo_db=None,
        tool_log_table="tool_log",
    ):
        self.pg_conn = pg_conn
        self.qdrant = qdrant_client
        self.embedding_model = embedding_model
        self.mongo_db = mongo_db
        self.tool_log_table = tool_log_table
        # MongoDB collections
        self._conversations = mongo_db["conversations"] if mongo_db is not None else None
        self._tool_logs_mongo = mongo_db["tool_logs"] if mongo_db is not None else None

    # -----------------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------------

    def _embed(self, texts):
        """Embed a list of texts using the configured embedding model."""
        if self.embedding_model is None:
            raise RuntimeError("No embedding model configured on SprawlMemoryManager")
        if isinstance(texts, str):
            texts = [texts]
        return self.embedding_model.embed_documents(texts)

    def _embed_query(self, text):
        """Embed a single query text."""
        if self.embedding_model is None:
            raise RuntimeError("No embedding model configured on SprawlMemoryManager")
        return self.embedding_model.embed_query(text)

    # -----------------------------------------------------------------------
    # Conversational Memory (MongoDB)
    # -----------------------------------------------------------------------

    def write_conversational_memory(self, content, role, thread_id, metadata=None):
        """Store a message in conversation history (MongoDB).

        Signature matches Oracle MemoryManager: (content, role, thread_id).
        """
        thread_id = str(thread_id)
        record_id = str(uuid.uuid4())
        doc = {
            "_id": record_id,
            "thread_id": thread_id,
            "role": role,
            "content": content,
            "metadata": metadata or {},
            "timestamp": datetime.utcnow(),
            "summary_id": None,
        }
        try:
            self._conversations.insert_one(doc)
            return record_id
        except Exception as e:
            logger.warning("Failed to write conversational memory (MongoDB): %s", e)
            return None

    def read_conversational_memory(self, thread_id, limit=10):
        """Read unsummarized conversation history formatted for context."""
        messages = self.get_unsummarized_messages(thread_id, limit=limit)
        lines = [
            f"[{m['timestamp'].strftime('%H:%M:%S') if m['timestamp'] else ''}] [{m['role']}] {m['content']}"
            for m in messages
        ]
        messages_formatted = "\n".join(lines)
        return f"""## Conversation Memory (Thread: {thread_id})
### Purpose: Recent dialogue turns that have NOT yet been summarized.

{messages_formatted}"""

    def read_conversational_memory_raw(self, thread_id, limit=200):
        """Read all messages for a thread (for loading into UI)."""
        thread_id = str(thread_id)
        try:
            cursor = (
                self._conversations.find(
                    {"thread_id": thread_id},
                    {"_id": 1, "role": 1, "content": 1, "timestamp": 1, "summary_id": 1},
                )
                .sort("timestamp", 1)
                .limit(limit)
            )
            return [
                {
                    "id": doc["_id"],
                    "role": doc["role"],
                    "content": doc["content"],
                    "timestamp": doc["timestamp"].isoformat() if doc.get("timestamp") else None,
                    "summary_id": doc.get("summary_id"),
                }
                for doc in cursor
            ]
        except Exception as e:
            logger.warning("Failed to read conversational memory (MongoDB): %s", e)
            return []

    def get_threads(self, limit=50):
        """Get list of threads ordered by last activity (MongoDB aggregation)."""
        try:
            pipeline = [
                {"$match": {"role": "user"}},
                {
                    "$group": {
                        "_id": "$thread_id",
                        "last_updated": {"$max": "$timestamp"},
                        "message_count": {"$sum": 1},
                        "first_ts": {"$min": "$timestamp"},
                        "first_content": {"$first": "$content"},
                    }
                },
                {"$sort": {"last_updated": -1}},
                {"$limit": limit},
            ]
            results = list(self._conversations.aggregate(pipeline))
            return [
                {
                    "thread_id": r["_id"],
                    "title": (r["first_content"][:50] + "...")
                    if r.get("first_content") and len(r["first_content"]) > 50
                    else r.get("first_content"),
                    "updated_at": r["last_updated"].isoformat() if r.get("last_updated") else None,
                    "message_count": r["message_count"],
                }
                for r in results
            ]
        except Exception as e:
            logger.warning("Failed to get threads (MongoDB): %s", e)
            return []

    def get_unsummarized_messages(self, thread_id, limit=100):
        """Return unsummarized conversation messages for a thread."""
        thread_id = str(thread_id)
        try:
            cursor = (
                self._conversations.find(
                    {"thread_id": thread_id, "summary_id": None},
                    {"_id": 1, "role": 1, "content": 1, "timestamp": 1},
                )
                .sort("timestamp", 1)
                .limit(limit)
            )
            return [
                {
                    "id": doc["_id"],
                    "role": doc["role"],
                    "content": doc["content"],
                    "timestamp": doc.get("timestamp"),
                }
                for doc in cursor
            ]
        except Exception as e:
            logger.warning("Failed to get unsummarized messages (MongoDB): %s", e)
            return []

    def mark_as_summarized(self, thread_id, summary_id, message_ids=None):
        """Mark conversation messages as summarized.

        Signature matches Oracle MemoryManager: (thread_id, summary_id, message_ids).
        """
        if not message_ids:
            return
        try:
            self._conversations.update_many(
                {"_id": {"$in": message_ids}, "summary_id": None},
                {"$set": {"summary_id": summary_id}},
            )
        except Exception as e:
            logger.warning("Failed to mark messages as summarized (MongoDB): %s", e)

    def delete_thread_messages(self, thread_id):
        """Delete all messages for a thread. Returns count of deleted rows."""
        thread_id = str(thread_id)
        try:
            result = self._conversations.delete_many({"thread_id": thread_id})
            return result.deleted_count
        except Exception as e:
            logger.warning("Failed to delete thread messages (MongoDB): %s", e)
            return 0

    # -----------------------------------------------------------------------
    # Tool Log (PostgreSQL)
    # -----------------------------------------------------------------------

    def write_tool_log(self, thread_id, tool_call_id, tool_name, tool_args, tool_output):
        """Offload tool output to the tool log and return a compact reference."""
        preview = str(tool_output)[:1500]
        try:
            cur = self.pg_conn.cursor()
            cur.execute(
                f"""INSERT INTO {self.tool_log_table}
                    (thread_id, tool_call_id, tool_name, tool_args, tool_output)
                    VALUES (%s, %s, %s, %s, %s)""",
                (str(thread_id), tool_call_id, tool_name, tool_args, str(tool_output)),
            )
            self.pg_conn.commit()
            cur.close()
        except Exception as e:
            self.pg_conn.rollback()
            logger.warning("Failed to write tool log: %s", e)
        return f"[Tool Log: {tool_name} | id={tool_call_id}] Preview: {preview}"

    def read_tool_log(self, thread_id, tool_call_id):
        """Read a specific tool log entry. Returns dict or None."""
        try:
            cur = self.pg_conn.cursor()
            cur.execute(
                f"""SELECT tool_call_id, tool_name, tool_args, tool_output, timestamp
                    FROM {self.tool_log_table}
                    WHERE thread_id = %s AND tool_call_id = %s
                    ORDER BY timestamp DESC
                    LIMIT 1""",
                (str(thread_id), tool_call_id),
            )
            row = cur.fetchone()
            cur.close()
            if row:
                return {
                    "tool_call_id": row[0],
                    "tool_name": row[1],
                    "tool_args": row[2],
                    "tool_output": row[3],
                    "timestamp": row[4].isoformat() if row[4] else None,
                }
            return None
        except Exception as e:
            logger.warning("Failed to read tool log: %s", e)
            return None

    # -----------------------------------------------------------------------
    # Knowledge Base (Qdrant: knowledge_base collection)
    # -----------------------------------------------------------------------

    def search_knowledge_base(self, query_embedding, top_k=5):
        """Search knowledge base by embedding vector. Returns list of dicts."""
        try:
            results = self.qdrant.search(
                collection_name="knowledge_base",
                query_vector=query_embedding,
                limit=top_k,
            )
            return [
                {
                    "id": str(r.id),
                    "text": r.payload.get("text", ""),
                    "score": r.score,
                    **{k: v for k, v in r.payload.items() if k != "text"},
                }
                for r in results
            ]
        except Exception as e:
            logger.warning("Failed to search knowledge base: %s", e)
            return []

    def write_knowledge_base(self, texts, metadatas):
        """Write documents to the knowledge base Qdrant collection."""
        try:
            embeddings = self._embed(texts)
            points = []
            for text, meta, emb in zip(texts, metadatas, embeddings, strict=False):
                point_id = str(uuid.uuid4())
                payload = {"text": text, **meta}
                points.append(PointStruct(id=point_id, vector=emb, payload=payload))
            self.qdrant.upsert(collection_name="knowledge_base", points=points)
        except Exception as e:
            logger.warning("Failed to write knowledge base: %s", e)

    # -----------------------------------------------------------------------
    # Toolbox Memory (Qdrant: toolbox_memory collection)
    # -----------------------------------------------------------------------

    def search_toolbox_memory(self, query_embedding, top_k=5):
        """Search toolbox memory by embedding vector. Returns list of tool schemas."""
        try:
            results = self.qdrant.search(
                collection_name="toolbox_memory",
                query_vector=query_embedding,
                limit=top_k,
            )
            tools = []
            for r in results:
                meta = r.payload
                if meta and "name" in meta and "description" in meta:
                    tool_schema = {
                        "type": "function",
                        "function": {
                            "name": meta["name"],
                            "description": meta.get("description", ""),
                            "parameters": meta.get(
                                "parameters", {"type": "object", "properties": {}}
                            ),
                        },
                    }
                    tools.append(tool_schema)
            return tools
        except Exception as e:
            logger.warning("Failed to search toolbox memory: %s", e)
            return []

    def write_toolbox_memory(self, texts, metadatas):
        """Write tool definitions to the toolbox Qdrant collection."""
        try:
            embeddings = self._embed(texts)
            points = []
            for text, meta, emb in zip(texts, metadatas, embeddings, strict=False):
                point_id = str(uuid.uuid4())
                payload = {"text": text, **meta}
                points.append(PointStruct(id=point_id, vector=emb, payload=payload))
            self.qdrant.upsert(collection_name="toolbox_memory", points=points)
        except Exception as e:
            logger.warning("Failed to write toolbox memory: %s", e)

    # -----------------------------------------------------------------------
    # Entity Memory (Qdrant: entity_memory collection)
    # -----------------------------------------------------------------------

    def search_entity_memory(self, query_embedding, thread_id=None, top_k=5):
        """Search entity memory by embedding vector, optionally scoped to thread."""
        try:
            query_filter = None
            search_limit = top_k
            if thread_id:
                query_filter = Filter(
                    must=[FieldCondition(key="thread_id", match=MatchValue(value=str(thread_id)))]
                )
                search_limit = top_k * 4  # over-fetch to account for filtering

            results = self.qdrant.search(
                collection_name="entity_memory",
                query_vector=query_embedding,
                query_filter=query_filter,
                limit=search_limit,
            )
            return [
                {
                    "id": str(r.id),
                    "text": r.payload.get("text", ""),
                    "name": r.payload.get("name", ""),
                    "type": r.payload.get("type", ""),
                    "description": r.payload.get("description", ""),
                    "score": r.score,
                }
                for r in results[:top_k]
            ]
        except Exception as e:
            logger.warning("Failed to search entity memory: %s", e)
            return []

    def write_entity_memory(self, texts, metadatas):
        """Write entity records to the entity Qdrant collection."""
        try:
            embeddings = self._embed(texts)
            points = []
            for text, meta, emb in zip(texts, metadatas, embeddings, strict=False):
                point_id = str(uuid.uuid4())
                payload = {"text": text, **meta}
                points.append(PointStruct(id=point_id, vector=emb, payload=payload))
            self.qdrant.upsert(collection_name="entity_memory", points=points)
        except Exception as e:
            logger.warning("Failed to write entity memory: %s", e)

    # -----------------------------------------------------------------------
    # Workflow Memory (Qdrant: workflow_memory collection)
    # -----------------------------------------------------------------------

    def search_workflow_memory(self, query_embedding, thread_id=None, top_k=5):
        """Search workflow memory by embedding vector, optionally scoped to thread."""
        try:
            query_filter = None
            search_limit = top_k
            if thread_id:
                query_filter = Filter(
                    must=[FieldCondition(key="thread_id", match=MatchValue(value=str(thread_id)))]
                )
                search_limit = top_k * 4

            results = self.qdrant.search(
                collection_name="workflow_memory",
                query_vector=query_embedding,
                query_filter=query_filter,
                limit=search_limit,
            )
            return [
                {
                    "id": str(r.id),
                    "text": r.payload.get("text", ""),
                    "score": r.score,
                    **{k: v for k, v in r.payload.items() if k != "text"},
                }
                for r in results[:top_k]
            ]
        except Exception as e:
            logger.warning("Failed to search workflow memory: %s", e)
            return []

    def write_workflow_memory(self, texts, metadatas):
        """Write workflow records to the workflow Qdrant collection."""
        try:
            embeddings = self._embed(texts)
            points = []
            for text, meta, emb in zip(texts, metadatas, embeddings, strict=False):
                point_id = str(uuid.uuid4())
                payload = {"text": text, **meta}
                points.append(PointStruct(id=point_id, vector=emb, payload=payload))
            self.qdrant.upsert(collection_name="workflow_memory", points=points)
        except Exception as e:
            logger.warning("Failed to write workflow memory: %s", e)

    # -----------------------------------------------------------------------
    # Summary Memory (Qdrant: summary_memory collection)
    # -----------------------------------------------------------------------

    def write_summary_memory(self, texts, metadatas):
        """Write summary records to the summary Qdrant collection."""
        try:
            embeddings = self._embed(texts)
            points = []
            for text, meta, emb in zip(texts, metadatas, embeddings, strict=False):
                point_id = str(uuid.uuid4())
                payload = {"text": text, **meta}
                points.append(PointStruct(id=point_id, vector=emb, payload=payload))
            self.qdrant.upsert(collection_name="summary_memory", points=points)
        except Exception as e:
            logger.warning("Failed to write summary memory: %s", e)

    def read_summary_memory(self, summary_id):
        """Read the full summary text for a given summary_id.

        Returns a dict with 'text' and metadata, or None if not found.
        """
        try:
            # Use scroll with filter to find the summary by its stored id
            results, _ = self.qdrant.scroll(
                collection_name="summary_memory",
                scroll_filter=Filter(
                    must=[FieldCondition(key="id", match=MatchValue(value=summary_id))]
                ),
                limit=1,
            )
            if results:
                point = results[0]
                return {
                    "id": summary_id,
                    "text": point.payload.get("text", ""),
                    **{k: v for k, v in point.payload.items() if k not in ("text", "id")},
                }
            return None
        except Exception as e:
            logger.warning("Failed to read summary memory for %s: %s", summary_id, e)
            return None

    # -----------------------------------------------------------------------
    # High-level API — matches Oracle MemoryManager interface used by harness
    # -----------------------------------------------------------------------

    def read_knowledge_base(self, query, k=3):
        """Search knowledge base and return formatted string for context."""
        try:
            qv = self._embed_query(query)
            results = self.qdrant.search(
                collection_name="knowledge_base",
                query_vector=qv,
                limit=k,
            )
            content = "\n".join([r.payload.get("text", "") for r in results])
        except Exception as e:
            logger.warning("Failed to read knowledge base: %s", e)
            content = "No relevant documents found."
        return f"""## Knowledge Base Memory
### Purpose: Factual documents, research papers, and regulatory documents.

{content}"""

    def write_workflow(self, query, steps, final_answer, success=True, thread_id=None):
        """Store a completed workflow pattern."""
        steps_text = "\n".join([f"Step {i + 1}: {s}" for i, s in enumerate(steps)])
        text = f"Query: {query}\nSteps:\n{steps_text}\nAnswer: {final_answer[:200]}"
        metadata = {
            "query": query,
            "success": str(success),
            "num_steps": len(steps),
            "timestamp": datetime.now().isoformat(),
        }
        if thread_id:
            metadata["thread_id"] = str(thread_id)
        self.write_workflow_memory([text], [metadata])

    def read_workflow(self, query, k=3, thread_id=None):
        """Search for similar past workflows, scoped to thread_id."""
        try:
            qv = self._embed_query(query)
            query_filter = None
            if thread_id:
                query_filter = Filter(
                    must=[FieldCondition(key="thread_id", match=MatchValue(value=str(thread_id)))]
                )
            results = self.qdrant.search(
                collection_name="workflow_memory",
                query_vector=qv,
                query_filter=query_filter,
                limit=k,
            )
            if not results:
                return "## Workflow Memory\nNo relevant workflows found."
            content = "\n---\n".join([r.payload.get("text", "") for r in results])
        except Exception:
            return "## Workflow Memory\nNo relevant workflows found."
        return f"""## Workflow Memory
### Purpose: Step-by-step records of how similar past queries were resolved.

{content}"""

    def write_toolbox(self, text, metadata):
        """Store a tool definition for semantic retrieval."""
        self.write_toolbox_memory([text], [metadata])

    def read_toolbox(self, query, k=5):
        """Retrieve relevant tools via Qdrant vector search."""
        try:
            qv = self._embed_query(query or "tool")
            results = self.qdrant.search(
                collection_name="toolbox_memory",
                query_vector=qv,
                limit=k,
            )
            tools = []
            for r in results:
                meta = r.payload
                if meta and "name" in meta and "description" in meta:
                    tool_schema = {
                        "type": "function",
                        "function": {
                            "name": meta["name"],
                            "description": meta.get("description", ""),
                            "parameters": meta.get(
                                "parameters", {"type": "object", "properties": {}}
                            ),
                        },
                    }
                    tools.append(tool_schema)
            return tools
        except Exception:
            return []

    def write_entity(
        self, name, entity_type, description, llm_client=None, text=None, thread_id=None
    ):
        """Store or extract entities, scoped to thread_id."""
        tid = str(thread_id) if thread_id else None
        if text and llm_client:
            entities = self._extract_entities(text, llm_client)
            for e in entities:
                entity_text = f"{e['name']}: {e['description']}"
                metadata = {
                    "name": e["name"],
                    "type": e.get("type", "UNKNOWN"),
                    "description": e.get("description", ""),
                    "timestamp": datetime.now().isoformat(),
                }
                if tid:
                    metadata["thread_id"] = tid
                self.write_entity_memory([entity_text], [metadata])
        elif name:
            entity_text = f"{name}: {description}"
            metadata = {
                "name": name,
                "type": entity_type,
                "description": description,
                "timestamp": datetime.now().isoformat(),
            }
            if tid:
                metadata["thread_id"] = tid
            self.write_entity_memory([entity_text], [metadata])

    def _extract_entities(self, text, llm_client):
        """Use LLM to extract entities from text."""
        if not text or len(text.strip()) < 5:
            return []
        prompt = f"""Extract entities from: "{text[:500]}"
Return JSON: [{{"name": "X", "type": "PERSON|PLACE|SYSTEM|INSTRUMENT|ACCOUNT", "description": "brief"}}]
If none: []"""
        try:
            from config import OPENAI_MODEL

            response = llm_client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_completion_tokens=300,
            )
            result = response.choices[0].message.content.strip()
            start, end = result.find("["), result.rfind("]")
            if start == -1 or end == -1:
                return []
            parsed = json_lib.loads(result[start : end + 1])
            return [
                {
                    "name": e["name"],
                    "type": e.get("type", "UNKNOWN"),
                    "description": e.get("description", ""),
                }
                for e in parsed
                if isinstance(e, dict) and e.get("name")
            ]
        except Exception:
            return []

    def read_entity(self, query, k=5, thread_id=None):
        """Search for relevant entities, scoped to thread_id."""
        try:
            qv = self._embed_query(query)
            query_filter = None
            if thread_id:
                query_filter = Filter(
                    must=[FieldCondition(key="thread_id", match=MatchValue(value=str(thread_id)))]
                )
            results = self.qdrant.search(
                collection_name="entity_memory",
                query_vector=qv,
                query_filter=query_filter,
                limit=k,
            )
            if not results:
                return "## Entity Memory\nNo entities found."
            entities = [
                f"- {r.payload.get('name', '?')}: {r.payload.get('description', '')}"
                for r in results
            ]
        except Exception:
            return "## Entity Memory\nNo entities found."
        return f"""## Entity Memory
### Purpose: Named entities extracted from conversations.

{chr(10).join(entities)}"""

    def write_summary(self, summary_id, full_content, summary_text, description, thread_id=None):
        """Store a summary in Qdrant, scoped to thread_id."""
        metadata = {
            "id": summary_id,
            "description": description,
            "timestamp": datetime.now().isoformat(),
            "full_content_length": len(full_content),
        }
        if thread_id:
            metadata["thread_id"] = str(thread_id)
        self.write_summary_memory([summary_text], [metadata])

    def read_summary_context(self, query="", k=10, thread_id=None):
        """Get available summaries (IDs + descriptions for JIT expansion)."""
        try:
            qv = self._embed_query(query or "summary")
            query_filter = None
            if thread_id:
                query_filter = Filter(
                    must=[FieldCondition(key="thread_id", match=MatchValue(value=str(thread_id)))]
                )
            results = self.qdrant.search(
                collection_name="summary_memory",
                query_vector=qv,
                query_filter=query_filter,
                limit=k,
            )
            if not results:
                return "## Summary Memory\nNo summaries available."
            lines = [
                "## Summary Memory",
                "### Purpose: Compressed snapshots of older conversations and context windows.",
                "### Call expand_summary(summary_id) to retrieve full content just-in-time.",
                "",
            ]
            for r in results:
                sid = r.payload.get("id", "?")
                desc = r.payload.get("description", "No description")
                lines.append(f"  - [ID: {sid}] {desc}")
            return "\n".join(lines)
        except Exception:
            return "## Summary Memory\nNo summaries available."

    def get_messages_by_summary_id(self, summary_id):
        """Get original messages that were compacted into a summary (MongoDB)."""
        try:
            cursor = self._conversations.find(
                {"summary_id": summary_id},
                {"_id": 1, "role": 1, "content": 1, "timestamp": 1},
            ).sort("timestamp", 1)
            return [
                {
                    "id": doc["_id"],
                    "role": doc["role"],
                    "content": doc["content"],
                    "timestamp": doc.get("timestamp"),
                }
                for doc in cursor
            ]
        except Exception as e:
            logger.warning("Failed to get messages by summary_id (MongoDB): %s", e)
            return []

    def get_tool_logs_for_thread(self, thread_id):
        """Retrieve all tool logs for a thread, ordered by timestamp."""
        thread_id = str(thread_id)
        try:
            cur = self.pg_conn.cursor()
            cur.execute(
                f"""SELECT tool_call_id, tool_name, tool_args, tool_output, timestamp
                    FROM {self.tool_log_table}
                    WHERE thread_id = %s
                    ORDER BY timestamp ASC""",
                (thread_id,),
            )
            rows = cur.fetchall()
            cur.close()
            return [
                {
                    "tool_call_id": tcid,
                    "tool_name": tname,
                    "tool_args": targs,
                    "tool_output": tout,
                    "timestamp": ts.isoformat() if ts else None,
                }
                for tcid, tname, targs, tout, ts in rows
            ]
        except Exception as e:
            logger.warning("Failed to get tool logs: %s", e)
            return []
