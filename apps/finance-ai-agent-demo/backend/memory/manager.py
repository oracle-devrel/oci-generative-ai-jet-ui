"""MemoryManager: 6+1 memory types backed by Oracle AI Database."""

import array
import json as json_lib
from datetime import datetime

from retrieval.text_search import _sanitize_for_oracle_text


class MemoryManager:
    """Manages 6 types of memory + tool log for AI agents using Oracle AI Database.

    Memory types:
    - Conversational: Chat history per thread (SQL table)
    - Knowledge Base: Searchable documents (vector-enabled table)
    - Workflow: Execution patterns (vector-enabled table)
    - Toolbox: Available tools (vector-enabled table)
    - Entity: People, places, instruments (vector-enabled table)
    - Summary: Compressed context snapshots (vector-enabled table)
    - Tool Log: Tool output offloading (SQL table)
    """

    def __init__(
        self,
        conn,
        conversation_table,
        knowledge_base_vs,
        workflow_vs,
        toolbox_vs,
        entity_vs,
        summary_vs,
        embedding_model=None,
        tool_log_table="TOOL_LOG",
    ):
        self.conn = conn
        self.conversation_table = conversation_table
        self.knowledge_base_vs = knowledge_base_vs
        self.workflow_vs = workflow_vs
        self.toolbox_vs = toolbox_vs
        self.entity_vs = entity_vs
        self.summary_vs = summary_vs
        self.embedding_model = embedding_model
        self.tool_log_table = tool_log_table

    # ---- Conversational Memory ----

    def write_conversational_memory(self, content, role, thread_id):
        """Store a message in conversation history."""
        thread_id = str(thread_id)
        with self.conn.cursor() as cur:
            id_var = cur.var(str)
            cur.execute(
                f"""INSERT INTO {self.conversation_table}
                    (thread_id, role, content, metadata, timestamp)
                    VALUES (:thread_id, :role, :content, :metadata, CURRENT_TIMESTAMP)
                    RETURNING id INTO :id""",
                {
                    "thread_id": thread_id,
                    "role": role,
                    "content": content,
                    "metadata": "{}",
                    "id": id_var,
                },
            )
            record_id = id_var.getvalue()[0] if id_var.getvalue() else None
        self.conn.commit()
        return record_id

    def get_unsummarized_messages(self, thread_id, limit=100):
        """Return unsummarized conversation messages for a thread."""
        thread_id = str(thread_id)
        with self.conn.cursor() as cur:
            cur.execute(
                f"""SELECT id, role, content, timestamp
                    FROM {self.conversation_table}
                    WHERE thread_id = :thread_id AND summary_id IS NULL
                    ORDER BY timestamp ASC
                    FETCH FIRST :limit ROWS ONLY""",
                {"thread_id": thread_id, "limit": limit},
            )
            rows = cur.fetchall()
        return [
            {"id": rid, "role": role, "content": content, "timestamp": ts}
            for rid, role, content, ts in rows
        ]

    def read_conversational_memory(self, thread_id, limit=10):
        """Read unsummarized conversation history for a thread (formatted for context)."""
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
        with self.conn.cursor() as cur:
            cur.execute(
                f"""SELECT id, role, content, timestamp, summary_id
                    FROM {self.conversation_table}
                    WHERE thread_id = :thread_id
                    ORDER BY timestamp ASC
                    FETCH FIRST :limit ROWS ONLY""",
                {"thread_id": thread_id, "limit": limit},
            )
            rows = cur.fetchall()
        return [
            {
                "id": rid,
                "role": role,
                "content": content,
                "timestamp": ts.isoformat() if ts else None,
                "summary_id": sid,
            }
            for rid, role, content, ts, sid in rows
        ]

    def mark_as_summarized(self, thread_id, summary_id, message_ids=None):
        """Mark conversation messages as summarized."""
        thread_id = str(thread_id)
        with self.conn.cursor() as cur:
            if message_ids:
                cur.executemany(
                    f"""UPDATE {self.conversation_table}
                        SET summary_id = :summary_id
                        WHERE thread_id = :thread_id AND id = :id AND summary_id IS NULL""",
                    [
                        {"summary_id": summary_id, "thread_id": thread_id, "id": mid}
                        for mid in message_ids
                    ],
                )
            else:
                cur.execute(
                    f"""UPDATE {self.conversation_table}
                        SET summary_id = :summary_id
                        WHERE thread_id = :thread_id AND summary_id IS NULL""",
                    {"summary_id": summary_id, "thread_id": thread_id},
                )
        self.conn.commit()

    def get_messages_by_summary_id(self, summary_id):
        """Retrieve original messages that were compacted into a summary."""
        with self.conn.cursor() as cur:
            cur.execute(
                f"""SELECT id, role, content, timestamp
                    FROM {self.conversation_table}
                    WHERE summary_id = :summary_id
                    ORDER BY timestamp ASC""",
                {"summary_id": summary_id},
            )
            rows = cur.fetchall()
        return [
            {"id": rid, "role": role, "content": content, "timestamp": ts}
            for rid, role, content, ts in rows
        ]

    def delete_thread_messages(self, thread_id):
        """Delete all messages for a thread."""
        thread_id = str(thread_id)
        with self.conn.cursor() as cur:
            cur.execute(
                f"DELETE FROM {self.conversation_table} WHERE thread_id = :thread_id",
                {"thread_id": thread_id},
            )
            count = cur.rowcount
        self.conn.commit()
        return count

    def get_threads(self, limit=50):
        """Get list of threads ordered by last activity."""
        with self.conn.cursor() as cur:
            cur.execute(
                f"""SELECT t.thread_id,
                           DBMS_LOB.SUBSTR(f.content, 200, 1) AS first_msg,
                           t.last_updated,
                           t.message_count
                    FROM (
                        SELECT thread_id,
                               MAX(timestamp) AS last_updated,
                               COUNT(*) AS message_count,
                               MIN(timestamp) AS first_ts
                        FROM {self.conversation_table}
                        WHERE role = 'user'
                        GROUP BY thread_id
                    ) t
                    LEFT JOIN {self.conversation_table} f
                        ON f.thread_id = t.thread_id
                        AND f.timestamp = t.first_ts
                        AND f.role = 'user'
                    ORDER BY t.last_updated DESC
                    FETCH FIRST :limit ROWS ONLY""",
                {"limit": limit},
            )
            rows = cur.fetchall()
        return [
            {
                "thread_id": tid,
                "title": (first_msg[:50] + "...")
                if first_msg and len(first_msg) > 50
                else first_msg,
                "updated_at": ts.isoformat() if ts else None,
                "message_count": cnt,
            }
            for tid, first_msg, ts, cnt in rows
        ]

    # ---- Knowledge Base Memory ----

    def read_knowledge_base(self, query, k=3):
        """Search knowledge base for relevant content."""
        results = self.knowledge_base_vs.similarity_search(query, k=k)
        content = "\n".join([doc.page_content for doc in results])
        return f"""## Knowledge Base Memory
### Purpose: Factual documents, research papers, and regulatory documents.

{content}"""

    # ---- Workflow Memory ----

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
        self.workflow_vs.add_texts([text], [metadata])

    def read_workflow(self, query, k=3, thread_id=None):
        """Search for similar past workflows, scoped to thread_id."""
        try:
            # Fetch extra results so we can post-filter by thread_id
            fetch_k = k * 4 if thread_id else k
            results = self.workflow_vs.similarity_search(query, k=fetch_k)
        except Exception:
            return "## Workflow Memory\nNo relevant workflows found."
        if thread_id:
            results = [doc for doc in results if doc.metadata.get("thread_id") == str(thread_id)][
                :k
            ]
        if not results:
            return "## Workflow Memory\nNo relevant workflows found."
        content = "\n---\n".join([doc.page_content for doc in results])
        return f"""## Workflow Memory
### Purpose: Step-by-step records of how similar past queries were resolved.

{content}"""

    # ---- Toolbox Memory ----

    def write_toolbox(self, text, metadata):
        """Store a tool definition for semantic retrieval."""
        self.toolbox_vs.add_texts([text], [metadata])

    def read_toolbox(self, query, k=5):
        """Retrieve relevant tools via hybrid search (vector + Oracle Text RRF).

        Falls back to vector-only search if hybrid prerequisites are missing.
        """
        if self.conn and self.embedding_model and query:
            try:
                return self._read_toolbox_hybrid(query, k)
            except Exception:
                pass  # Fall back to vector-only

        # Fallback: vector-only search
        try:
            results = self.toolbox_vs.similarity_search(query or "tool", k=k)
        except Exception:
            return []

        return self._docs_to_tool_schemas(results)

    def _read_toolbox_hybrid(self, query, k=5, per_list=50, rrf_k=60):
        """Hybrid RRF search against TOOLBOX_MEMORY (vector + Oracle Text)."""
        qv = array.array("f", self.embedding_model.embed_query(query))
        safe_kw = _sanitize_for_oracle_text(query)

        sql = f"""
            WITH
            vec AS (
                SELECT id, metadata,
                    ROW_NUMBER() OVER (ORDER BY distance) AS r_vec
                FROM (
                    SELECT id, text, metadata,
                        vector_distance(embedding, :q, COSINE) as distance
                    FROM TOOLBOX_MEMORY
                    ORDER BY distance
                    FETCH APPROX FIRST {per_list} ROWS ONLY WITH TARGET ACCURACY 90
                )
            ),
            txt AS (
                SELECT
                    id, text, metadata,
                    SCORE(1) AS score_txt,
                    ROW_NUMBER() OVER (ORDER BY SCORE(1) DESC) AS r_txt
                FROM TOOLBOX_MEMORY
                WHERE CONTAINS(text, :kw, 1) > 0
                FETCH FIRST {per_list} ROWS ONLY
            ),
            fused AS (
                SELECT
                    COALESCE(v.id, t.id) AS id,
                    COALESCE(v.metadata, t.metadata) AS metadata,
                    NVL(v.r_vec, 999999) AS r_vec,
                    NVL(t.r_txt, 999999) AS r_txt
                FROM vec v
                FULL OUTER JOIN txt t ON t.id = v.id
            )
            SELECT
                id, metadata,
                ROUND((1.0/(:k + r_vec)) + (1.0/(:k + r_txt)), 6) AS rrf_score
            FROM fused
            ORDER BY rrf_score DESC
            FETCH FIRST :top_k ROWS ONLY
        """

        with self.conn.cursor() as cur:
            cur.execute(sql, {"q": qv, "kw": safe_kw, "k": rrf_k, "top_k": k})
            rows = cur.fetchall()

        tools = []
        for _row_id, metadata_raw, _rrf_score in rows:
            meta = self._parse_metadata(metadata_raw)
            if meta and "name" in meta and "description" in meta:
                tool_schema = {
                    "type": "function",
                    "function": {
                        "name": meta["name"],
                        "description": meta.get("description", ""),
                        "parameters": meta.get("parameters", {"type": "object", "properties": {}}),
                    },
                }
                tools.append(tool_schema)
        return tools

    @staticmethod
    def _parse_metadata(metadata_raw):
        """Parse metadata from Oracle CLOB or string."""
        if metadata_raw is None:
            return None
        try:
            text = metadata_raw.read() if hasattr(metadata_raw, "read") else str(metadata_raw)
            return json_lib.loads(text)
        except (json_lib.JSONDecodeError, ValueError):
            return None

    @staticmethod
    def _docs_to_tool_schemas(docs):
        """Convert LangChain Document list to OpenAI tool schemas."""
        tools = []
        for doc in docs:
            meta = doc.metadata
            if "name" in meta and "description" in meta:
                tool_schema = {
                    "type": "function",
                    "function": {
                        "name": meta["name"],
                        "description": meta.get("description", ""),
                        "parameters": meta.get("parameters", {"type": "object", "properties": {}}),
                    },
                }
                tools.append(tool_schema)
        return tools

    # ---- Entity Memory ----

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
                self.entity_vs.add_texts([entity_text], [metadata])
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
            self.entity_vs.add_texts([entity_text], [metadata])

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
            fetch_k = k * 4 if thread_id else k
            results = self.entity_vs.similarity_search(query, k=fetch_k)
        except Exception:
            return "## Entity Memory\nNo entities found."
        if thread_id:
            results = [doc for doc in results if doc.metadata.get("thread_id") == str(thread_id)][
                :k
            ]
        if not results:
            return "## Entity Memory\nNo entities found."
        entities = [
            f"- {doc.metadata.get('name', '?')}: {doc.metadata.get('description', '')}"
            for doc in results
            if hasattr(doc, "metadata")
        ]
        return f"""## Entity Memory
### Purpose: Named entities extracted from conversations.

{chr(10).join(entities)}"""

    # ---- Summary Memory ----

    def write_summary(self, summary_id, full_content, summary_text, description, thread_id=None):
        """Store a summary in vector memory, scoped to thread_id."""
        metadata = {
            "id": summary_id,
            "description": description,
            "timestamp": datetime.now().isoformat(),
            "full_content_length": len(full_content),
        }
        if thread_id:
            metadata["thread_id"] = str(thread_id)
        self.summary_vs.add_texts([summary_text], [metadata])

    def read_summary_context(self, query="", k=10, thread_id=None):
        """Get available summaries (IDs + descriptions only for JIT expansion), scoped to thread_id."""
        try:
            fetch_k = k * 4 if thread_id else k
            results = self.summary_vs.similarity_search(query or "summary", k=fetch_k)
        except Exception:
            return "## Summary Memory\nNo summaries available."
        if thread_id:
            results = [doc for doc in results if doc.metadata.get("thread_id") == str(thread_id)][
                :k
            ]
        if not results:
            return "## Summary Memory\nNo summaries available."
        lines = [
            "## Summary Memory",
            "### Purpose: Compressed snapshots of older conversations and context windows.",
            "### When to use: These are lightweight pointers. If a summary looks relevant,",
            "### call expand_summary(summary_id) to retrieve the full content just-in-time.",
            "### Do NOT expand all summaries — only expand when you need specific details.",
            "",
        ]
        for doc in results:
            sid = doc.metadata.get("id", "?")
            desc = doc.metadata.get("description", "No description")
            lines.append(f"  - [ID: {sid}] {desc}")
        return "\n".join(lines)

    def read_summary_memory(self, summary_id):
        """Read the full summary text for a given summary_id."""
        try:
            results = self.summary_vs.similarity_search(f"summary {summary_id}", k=10)
            for doc in results:
                if doc.metadata.get("id") == summary_id:
                    return doc.page_content
        except Exception:
            pass
        return f"Summary {summary_id} not found."

    # ---- Tool Log ----

    def write_tool_log(self, thread_id, tool_call_id, tool_name, tool_args, tool_output):
        """Offload tool output to the tool log and return a compact reference."""
        preview = str(tool_output)[:1500]
        with self.conn.cursor() as cur:
            cur.execute(
                f"""INSERT INTO {self.tool_log_table}
                    (thread_id, tool_call_id, tool_name, tool_args, tool_output)
                    VALUES (:thread_id, :tool_call_id, :tool_name, :tool_args, :tool_output)""",
                {
                    "thread_id": str(thread_id),
                    "tool_call_id": tool_call_id,
                    "tool_name": tool_name,
                    "tool_args": tool_args,
                    "tool_output": str(tool_output),
                },
            )
        self.conn.commit()
        return f"[Tool Log: {tool_name} | id={tool_call_id}] Preview: {preview}"

    def get_tool_logs_for_thread(self, thread_id):
        """Retrieve all tool logs for a thread, ordered by timestamp."""
        thread_id = str(thread_id)
        with self.conn.cursor() as cur:
            cur.execute(
                f"""SELECT tool_call_id, tool_name, tool_args, tool_output, timestamp
                    FROM {self.tool_log_table}
                    WHERE thread_id = :thread_id
                    ORDER BY timestamp ASC""",
                {"thread_id": thread_id},
            )
            rows = cur.fetchall()
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
