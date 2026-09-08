"""
Oracle AI Database RAG Pipe for Open WebUI

This Pipe function creates a dedicated "Oracle RAG" model in Open WebUI that:
1. Routes all queries through Oracle AI Database for context retrieval
2. Uses the agentic_rag reasoning strategies
3. Syncs uploaded documents to Oracle automatically

The Pipe appears as a selectable "model" in Open WebUI's model dropdown.

Installation:
1. In Open WebUI, go to Workspace > Functions
2. Click "+" to create a new function
3. Paste this code and save
4. The "Oracle RAG" model will appear in your model list

Author: Oracle AI Developer Hub
Version: 1.0.0
License: MIT
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Generator, Iterator, Union
import requests
import json


class Pipe:
    """
    Oracle AI Database RAG Pipe

    Creates a virtual "model" in Open WebUI that routes all requests
    through Oracle AI Database for unified RAG retrieval and storage.
    """

    class Valves(BaseModel):
        """Configuration valves for the pipe."""
        api_base_url: str = Field(
            default="http://localhost:8000",
            description="Base URL of the agentic_rag API server"
        )
        default_strategy: str = Field(
            default="cot-rag",
            description="Default reasoning strategy (cot-rag, tot-rag, react-rag, etc.)"
        )
        temperature: float = Field(
            default=0.7,
            description="Temperature for LLM generation"
        )
        stream_responses: bool = Field(
            default=True,
            description="Enable streaming responses"
        )

    def __init__(self):
        self.type = "manifold"  # Exposes multiple model endpoints
        self.valves = self.Valves()
        self._session = None

    @property
    def session(self):
        """Lazy-load requests session."""
        if self._session is None:
            self._session = requests.Session()
            self._session.timeout = 120
        return self._session

    def pipes(self) -> List[dict]:
        """
        Return the list of available Oracle RAG models.
        These appear in Open WebUI's model dropdown.
        """
        return [
            {
                "id": "oracle-rag-cot",
                "name": "Oracle RAG (Chain of Thought)",
                "description": "RAG with step-by-step reasoning"
            },
            {
                "id": "oracle-rag-tot",
                "name": "Oracle RAG (Tree of Thoughts)",
                "description": "RAG with multi-path exploration"
            },
            {
                "id": "oracle-rag-react",
                "name": "Oracle RAG (ReAct)",
                "description": "RAG with reasoning and acting"
            },
            {
                "id": "oracle-rag-standard",
                "name": "Oracle RAG (Standard)",
                "description": "Simple RAG without advanced reasoning"
            },
            {
                "id": "oracle-rag-decomposed",
                "name": "Oracle RAG (Decomposed)",
                "description": "RAG with problem decomposition"
            },
            {
                "id": "oracle-rag-consistency",
                "name": "Oracle RAG (Self-Consistency)",
                "description": "RAG with multiple samples and voting"
            }
        ]

    def _get_strategy_from_model_id(self, model_id: str) -> str:
        """Map model ID to reasoning strategy."""
        strategy_map = {
            "oracle-rag-cot": "cot-rag",
            "oracle-rag-tot": "tot-rag",
            "oracle-rag-react": "react-rag",
            "oracle-rag-standard": "standard-rag",
            "oracle-rag-decomposed": "decomposed-rag",
            "oracle-rag-consistency": "consistency-rag"
        }
        return strategy_map.get(model_id, self.valves.default_strategy)

    def _convert_messages(self, messages: List[dict]) -> List[dict]:
        """Convert Open WebUI message format to OpenAI format."""
        converted = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            # Handle multimodal content
            if isinstance(content, list):
                text_parts = []
                for part in content:
                    if isinstance(part, dict) and part.get("type") == "text":
                        text_parts.append(part.get("text", ""))
                content = "\n".join(text_parts)

            converted.append({
                "role": role,
                "content": content
            })

        return converted

    def pipe(
        self,
        body: dict,
        __user__: Optional[dict] = None,
        __event_emitter__=None
    ) -> Union[str, Generator, Iterator]:
        """
        Process the request through Oracle AI Database RAG.

        Routes to our OpenAI-compatible API which handles:
        - RAG retrieval from Oracle AI Database
        - Reasoning strategy execution
        - Response streaming
        """
        # Get the model ID (e.g., "oracle-rag-cot")
        model_id = body.get("model", "").split(".")[-1]  # Handle "pipe.oracle-rag-cot"
        strategy = self._get_strategy_from_model_id(model_id)

        # Convert messages
        messages = self._convert_messages(body.get("messages", []))

        # Prepare request for our OpenAI-compatible API
        request_body = {
            "model": strategy,
            "messages": messages,
            "stream": self.valves.stream_responses and body.get("stream", True),
            "temperature": body.get("temperature", self.valves.temperature)
        }

        try:
            if request_body["stream"]:
                return self._stream_response(request_body, __event_emitter__)
            else:
                return self._sync_response(request_body)

        except Exception as e:
            error_msg = f"Oracle RAG Error: {str(e)}"
            print(f"[OracleRAG Pipe] {error_msg}")
            return error_msg

    def _stream_response(
        self,
        request_body: dict,
        __event_emitter__=None
    ) -> Generator[str, None, None]:
        """Stream response from Oracle RAG API."""
        try:
            response = self.session.post(
                f"{self.valves.api_base_url}/v1/chat/completions",
                json=request_body,
                stream=True,
                timeout=120
            )

            if response.status_code != 200:
                yield f"Error: API returned status {response.status_code}"
                return

            # Process SSE stream
            buffer = ""
            for line in response.iter_lines(decode_unicode=True):
                if not line:
                    continue

                if line.startswith("data: "):
                    data = line[6:]  # Remove "data: " prefix

                    if data == "[DONE]":
                        break

                    try:
                        chunk = json.loads(data)
                        choices = chunk.get("choices", [])
                        if choices:
                            delta = choices[0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                yield content
                    except json.JSONDecodeError:
                        continue

        except requests.exceptions.Timeout:
            yield "\n\n[Response timed out]"
        except Exception as e:
            yield f"\n\n[Error: {str(e)}]"

    def _sync_response(self, request_body: dict) -> str:
        """Get non-streaming response from Oracle RAG API."""
        try:
            response = self.session.post(
                f"{self.valves.api_base_url}/v1/chat/completions",
                json=request_body,
                timeout=120
            )

            if response.status_code != 200:
                return f"Error: API returned status {response.status_code}"

            data = response.json()
            choices = data.get("choices", [])
            if choices:
                message = choices[0].get("message", {})
                return message.get("content", "No response generated")

            return "No response generated"

        except Exception as e:
            return f"Error: {str(e)}"
