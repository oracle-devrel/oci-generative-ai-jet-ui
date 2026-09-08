"""
Oracle AI Database Document Sync Action for Open WebUI

This Action function syncs documents uploaded to Open WebUI to Oracle AI Database.
It can be triggered manually or automatically via the filter.

Features:
- Syncs file uploads to Oracle AI Database
- Handles PDF, text, and web content
- Provides sync status feedback

Installation:
1. In Open WebUI, go to Workspace > Functions
2. Click "+" to create a new function
3. Paste this code and save
4. Use the action button to sync documents

Author: Oracle AI Developer Hub
Version: 1.0.0
License: MIT
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import requests
import json


class Action:
    """
    Oracle Document Sync Action

    Syncs Open WebUI documents and knowledge to Oracle AI Database
    for unified RAG retrieval.
    """

    class Valves(BaseModel):
        """Configuration valves."""
        api_base_url: str = Field(
            default="http://localhost:8000",
            description="Base URL of the agentic_rag API server"
        )
        auto_sync_uploads: bool = Field(
            default=True,
            description="Automatically sync new uploads"
        )
        chunk_size: int = Field(
            default=800,
            description="Chunk size for document splitting"
        )

    def __init__(self):
        self.valves = self.Valves()
        self._session = None

    @property
    def session(self):
        if self._session is None:
            self._session = requests.Session()
            self._session.timeout = 60
        return self._session

    async def action(
        self,
        body: dict,
        __user__: Optional[dict] = None,
        __event_emitter__=None
    ) -> Optional[dict]:
        """
        Sync documents to Oracle AI Database.

        This action can be triggered:
        1. Manually via the action button
        2. Automatically when documents are uploaded
        """
        if __event_emitter__:
            await __event_emitter__({
                "type": "status",
                "data": {
                    "description": "Syncing to Oracle AI Database...",
                    "done": False
                }
            })

        try:
            # Get sync status first
            status_response = self.session.get(
                f"{self.valves.api_base_url}/sync/status"
            )

            if status_response.status_code != 200:
                if __event_emitter__:
                    await __event_emitter__({
                        "type": "status",
                        "data": {
                            "description": "Oracle API not available",
                            "done": True
                        }
                    })
                return {"error": "Oracle API not available"}

            status = status_response.json()

            # Extract any document content from the current context
            messages = body.get("messages", [])
            documents_to_sync = []

            for msg in messages:
                content = msg.get("content", "")
                if isinstance(content, str) and len(content) > 500:
                    # This might be document content
                    documents_to_sync.append({
                        "text": content[:10000],  # Limit size
                        "metadata": {
                            "source": "openwebui_chat",
                            "role": msg.get("role", "unknown")
                        }
                    })

            if documents_to_sync:
                # Sync to Oracle
                sync_response = self.session.post(
                    f"{self.valves.api_base_url}/sync/embeddings",
                    json={
                        "collection_name": "openwebui-chat",
                        "documents": documents_to_sync,
                        "source": "openwebui_action"
                    }
                )

                if sync_response.status_code == 200:
                    result = sync_response.json()
                    message = f"Synced {result.get('documents_synced', 0)} documents to Oracle AI Database"
                else:
                    message = f"Sync failed: {sync_response.status_code}"
            else:
                message = "No documents to sync in current context"

            if __event_emitter__:
                await __event_emitter__({
                    "type": "status",
                    "data": {
                        "description": message,
                        "done": True
                    }
                })

            # Return updated status
            return {
                "status": "success",
                "message": message,
                "collections": status.get("collections", {})
            }

        except Exception as e:
            error_msg = f"Sync error: {str(e)}"
            if __event_emitter__:
                await __event_emitter__({
                    "type": "status",
                    "data": {
                        "description": error_msg,
                        "done": True
                    }
                })
            return {"error": error_msg}
