"""
Oracle AI Database RAG Filter for Open WebUI

This filter integrates Open WebUI with Oracle AI Database via langchain-oracledb:
1. INLET: Retrieves relevant context from Oracle AI Database before sending to LLM
2. OUTLET: Syncs document embeddings to Oracle AI Database after processing

The filter works in symbiosis with the agentic_rag API backend to provide
unified vector storage and retrieval across Open WebUI and Oracle.

Installation:
1. In Open WebUI, go to Workspace > Functions
2. Click "+" to create a new function
3. Paste this code and save
4. Enable the filter for your models

Author: Oracle AI Developer Hub
Version: 1.0.0
License: MIT
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import requests
import json
import re
import hashlib


class Filter:
    """
    Oracle AI Database RAG Filter

    Integrates Open WebUI with Oracle AI Database for unified vector storage
    and retrieval using langchain-oracledb.
    """

    class Valves(BaseModel):
        """Configuration valves for the filter."""
        api_base_url: str = Field(
            default="http://localhost:8000",
            description="Base URL of the agentic_rag API server"
        )
        enable_rag_retrieval: bool = Field(
            default=True,
            description="Enable RAG context retrieval from Oracle AI Database"
        )
        enable_document_sync: bool = Field(
            default=True,
            description="Enable automatic document sync to Oracle AI Database"
        )
        top_k_results: int = Field(
            default=5,
            description="Number of RAG results to retrieve"
        )
        min_query_length: int = Field(
            default=10,
            description="Minimum query length to trigger RAG retrieval"
        )
        collections_to_search: str = Field(
            default="all",
            description="Collections to search: 'all', 'pdf', 'web', 'repo', or comma-separated list"
        )
        inject_sources_in_response: bool = Field(
            default=True,
            description="Show retrieved sources in the response"
        )
        sync_threshold_chars: int = Field(
            default=500,
            description="Minimum content length to trigger document sync"
        )

    def __init__(self):
        self.valves = self.Valves()
        self.toggle = True  # Enable toggle UI
        self.icon = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z"/>
        </svg>"""
        self._session = None
        self._processed_hashes = set()  # Track already synced content

    @property
    def session(self):
        """Lazy-load requests session."""
        if self._session is None:
            self._session = requests.Session()
            self._session.timeout = 30
        return self._session

    def _get_content_hash(self, content: str) -> str:
        """Generate hash for deduplication."""
        return hashlib.md5(content[:1000].encode()).hexdigest()[:12]

    def _extract_user_query(self, body: dict) -> str:
        """Extract the user's query from the request body."""
        messages = body.get("messages", [])
        for msg in reversed(messages):
            if msg.get("role") == "user":
                content = msg.get("content", "")
                if isinstance(content, str):
                    return content
                elif isinstance(content, list):
                    # Handle multimodal content
                    for part in content:
                        if isinstance(part, dict) and part.get("type") == "text":
                            return part.get("text", "")
        return ""

    def _query_oracle_rag(self, query: str) -> List[Dict[str, Any]]:
        """Query Oracle AI Database for relevant context."""
        try:
            # Use unified RAG search endpoint
            response = self.session.post(
                f"{self.valves.api_base_url}/query",
                json={
                    "query": query,
                    "use_cot": False
                },
                timeout=15
            )

            if response.status_code == 200:
                data = response.json()
                return data.get("context", [])
            else:
                print(f"[OracleRAG] Query failed: {response.status_code}")
                return []

        except Exception as e:
            print(f"[OracleRAG] Error querying Oracle: {e}")
            return []

    def _format_rag_context(self, results: List[Dict[str, Any]], query: str) -> str:
        """Format RAG results as context for the LLM."""
        if not results:
            return ""

        context_parts = [
            "\n---",
            "**Retrieved from Oracle AI Database:**\n"
        ]

        for i, result in enumerate(results[:self.valves.top_k_results], 1):
            content = result.get("content", result.get("text", ""))
            metadata = result.get("metadata", {})
            source = metadata.get("source", metadata.get("url", "Unknown"))
            score = result.get("score", result.get("similarity"))

            # Truncate long content
            if len(content) > 500:
                content = content[:500] + "..."

            context_parts.append(f"**[{i}]** {source}")
            if score:
                context_parts.append(f"   Relevance: {score:.2%}")
            context_parts.append(f"   {content}\n")

        context_parts.append("---\n")
        context_parts.append(f"Use the above context to help answer: {query}\n")

        return "\n".join(context_parts)

    def _sync_to_oracle(self, content: str, metadata: Dict[str, Any]) -> bool:
        """Sync document content to Oracle AI Database."""
        try:
            # Check if already synced
            content_hash = self._get_content_hash(content)
            if content_hash in self._processed_hashes:
                return False

            # Prepare documents for sync
            documents = [{
                "text": content,
                "metadata": {
                    **metadata,
                    "synced_by": "openwebui_filter",
                    "content_hash": content_hash
                }
            }]

            response = self.session.post(
                f"{self.valves.api_base_url}/sync/embeddings",
                json={
                    "collection_name": metadata.get("collection", "openwebui-general"),
                    "documents": documents,
                    "source": "openwebui"
                },
                timeout=30
            )

            if response.status_code == 200:
                self._processed_hashes.add(content_hash)
                result = response.json()
                print(f"[OracleRAG] Synced {result.get('documents_synced', 0)} documents")
                return True
            else:
                print(f"[OracleRAG] Sync failed: {response.status_code}")
                return False

        except Exception as e:
            print(f"[OracleRAG] Error syncing to Oracle: {e}")
            return False

    def _extract_source_content(self, text: str) -> List[Dict[str, Any]]:
        """Extract source content from Open WebUI preprocessed messages."""
        sources = []

        # Pattern for Open WebUI source tags
        pattern = re.compile(
            r'<source\s+([^>]*)>(.*?)</source>',
            re.DOTALL | re.IGNORECASE
        )

        for match in pattern.finditer(text):
            attrs_str = match.group(1)
            content = match.group(2).strip()

            if len(content) < self.valves.sync_threshold_chars:
                continue

            # Parse attributes
            id_match = re.search(r'id="([^"]*)"', attrs_str)
            title_match = re.search(r'title="([^"]*)"', attrs_str)
            url_match = re.search(r'url="([^"]*)"', attrs_str)

            sources.append({
                "id": id_match.group(1) if id_match else f"source_{len(sources)}",
                "title": title_match.group(1) if title_match else "",
                "url": url_match.group(1) if url_match else "",
                "content": content
            })

        return sources

    async def inlet(
        self,
        body: dict,
        __event_emitter__=None,
        __user__: Optional[dict] = None
    ) -> dict:
        """
        Process incoming request before sending to LLM.

        - Retrieves relevant context from Oracle AI Database
        - Injects context into the user's message
        - Syncs any embedded document content to Oracle
        """
        if not self.valves.enable_rag_retrieval:
            return body

        # Extract user query
        user_query = self._extract_user_query(body)

        if not user_query or len(user_query) < self.valves.min_query_length:
            return body

        # Emit status
        if __event_emitter__:
            await __event_emitter__({
                "type": "status",
                "data": {
                    "description": "Searching Oracle AI Database...",
                    "done": False
                }
            })

        # Check for embedded source content and sync to Oracle
        if self.valves.enable_document_sync:
            sources = self._extract_source_content(user_query)
            for source in sources:
                self._sync_to_oracle(
                    source["content"],
                    {
                        "source": source.get("url", "openwebui"),
                        "title": source.get("title", ""),
                        "source_id": source.get("id", ""),
                        "collection": "openwebui-attachments"
                    }
                )

        # Query Oracle AI Database for context
        rag_results = self._query_oracle_rag(user_query)

        if rag_results and self.valves.inject_sources_in_response:
            # Format and inject context
            context = self._format_rag_context(rag_results, user_query)

            # Modify the last user message to include context
            messages = body.get("messages", [])
            for i in range(len(messages) - 1, -1, -1):
                if messages[i].get("role") == "user":
                    original_content = messages[i].get("content", "")
                    if isinstance(original_content, str):
                        messages[i]["content"] = f"{context}\n\n{original_content}"
                    break

            body["messages"] = messages

        # Emit completion status
        if __event_emitter__:
            await __event_emitter__({
                "type": "status",
                "data": {
                    "description": f"Found {len(rag_results)} relevant documents",
                    "done": True
                }
            })

        return body

    def stream(self, event: dict) -> dict:
        """Process streaming events (pass-through)."""
        return event

    async def outlet(
        self,
        body: dict,
        __event_emitter__=None,
        __user__: Optional[dict] = None
    ) -> None:
        """
        Process response after LLM completes.

        - Can be used for post-processing or additional logging
        """
        if not self.valves.enable_document_sync:
            return

        # Get the assistant's response
        messages = body.get("messages", [])
        if not messages:
            return

        last_message = messages[-1]
        if last_message.get("role") != "assistant":
            return

        # Log completion (optional: could sync response for future retrieval)
        content = last_message.get("content", "")
        if len(content) > 100:
            print(f"[OracleRAG] Response length: {len(content)} chars")
