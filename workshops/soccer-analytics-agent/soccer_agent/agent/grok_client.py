"""Grok 4 chat client over OCI Generative AI Inference (bearer-token auth).

OCI GenAI's GENERIC api-format does not surface a `tools` parameter at this
endpoint, so tool calling is implemented as a prompt-protocol: the available
tool schemas are appended to the system prompt, and Grok is instructed to
reply with a single JSON object on its own line whenever it wants to call a
tool. The caller (agent loop) parses that JSON out of the text response.

The public signature `chat(messages, tool_schemas)` is unchanged, so callers
do not need to know whether real function-calling is available.
"""

from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass, field
from typing import Any

import httpx


@dataclass
class GrokReply:
    text: str
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    raw: Any = None


_TOOL_PROTOCOL = """
You have access to the following tools. When you need to call one, reply with
EXACTLY a single JSON object on its own line and nothing else:

    {"tool": "<tool_name>", "args": {<args>}}

When the user's question is fully answered, reply with plain prose (no JSON).
Available tools:
"""


def _url() -> str:
    return os.environ["OCI_GENAI_ENDPOINT"].rstrip("/") + "/20231130/actions/chat"


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {os.environ['OCI_GENAI_API_KEY']}",
        "Content-Type": "application/json",
    }


def _to_oci_message(m: dict[str, Any]) -> dict[str, Any]:
    return {
        "role": m["role"].upper(),
        "content": [{"type": "TEXT", "text": m["content"]}],
    }


def _inject_tool_protocol(messages: list[dict[str, Any]],
                          tool_schemas: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not tool_schemas:
        return messages
    schema_lines = "\n".join(
        f"- {t['name']}: {t['description']} | params: {json.dumps(t['parameters'])}"
        for t in tool_schemas
    )
    addendum = _TOOL_PROTOCOL + schema_lines
    out = list(messages)
    # Find the first system message and append; if none, prepend a new one.
    for i, m in enumerate(out):
        if m["role"] == "system":
            out[i] = {"role": "system", "content": m["content"] + "\n\n" + addendum}
            return out
    return [{"role": "system", "content": addendum.strip()}] + out


_JSON_LINE = re.compile(r"\{[^\n]*\"tool\"[^\n]*\}")
# Matches a JSON object that may span multiple lines, used as a fallback when
# the single-line regex finds nothing.  We scan for balanced-brace substrings
# that contain the literal string "tool" and attempt json.loads on each.
_JSON_BLOCK = re.compile(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*(\"tool\")[^{}]*\}",
                         re.DOTALL)


def _parse_tool_calls(text: str) -> list[dict[str, Any]]:
    """Pick up to one tool call out of the response text.

    Looks for a single JSON object that contains a "tool" key. Tries two
    strategies in order:
    1. Single-line match (fast, handles the common case).
    2. Multi-line / indented JSON block scan (handles pretty-printed output).

    Returns a list-of-one in our standard tool-call shape, or an empty list
    if no valid tool call is found.
    """
    # Strategy 1: single-line match.
    for match in _JSON_LINE.findall(text):
        try:
            obj = json.loads(match)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict) and "tool" in obj:
            return [{
                "id": "",
                "name": obj["tool"],
                "arguments": json.dumps(obj.get("args", {})),
            }]

    # Strategy 2: multi-line JSON block scan.  Walk the text looking for
    # opening braces; for each candidate extract the balanced substring and
    # attempt to parse it.
    for start in range(len(text)):
        if text[start] != "{":
            continue
        depth = 0
        for end in range(start, len(text)):
            if text[end] == "{":
                depth += 1
            elif text[end] == "}":
                depth -= 1
                if depth == 0:
                    candidate = text[start:end + 1]
                    if '"tool"' not in candidate:
                        break
                    try:
                        obj = json.loads(candidate)
                    except json.JSONDecodeError:
                        break
                    if isinstance(obj, dict) and "tool" in obj:
                        return [{
                            "id": "",
                            "name": obj["tool"],
                            "arguments": json.dumps(obj.get("args", {})),
                        }]
                    break
    return []


def chat(messages: list[dict[str, Any]],
         tool_schemas: list[dict[str, Any]] | None = None,
         max_tokens: int = 1024,
         temperature: float = 0.2,
         max_retries: int = 1) -> GrokReply:
    enriched = _inject_tool_protocol(messages, tool_schemas or [])
    body = {
        "compartmentId": os.environ["OCI_COMPARTMENT_ID"],
        "servingMode": {
            "servingType": "ON_DEMAND",
            "modelId": os.environ["OCI_GENAI_MODEL_ID"],
        },
        "chatRequest": {
            "messages": [_to_oci_message(m) for m in enriched],
            "apiFormat": "GENERIC",
            "maxTokens": max_tokens,
            "temperature": temperature,
        },
    }

    attempt = 0
    while True:
        with httpx.Client(timeout=180.0) as client:
            resp = client.post(_url(), headers=_headers(), json=body)
        if resp.status_code == 200:
            break
        if resp.status_code in (429,) or 500 <= resp.status_code < 600:
            if attempt >= max_retries:
                resp.raise_for_status()
            time.sleep(0.5 * (2 ** attempt))
            attempt += 1
            continue
        raise RuntimeError(f"OCI GenAI {resp.status_code}: {resp.text[:500]}")

    data = resp.json()
    message = data["chatResponse"]["choices"][0]["message"]

    text_parts = [
        c["text"] for c in message.get("content") or []
        if c.get("type") == "TEXT"
    ]
    text = "\n".join(text_parts)

    # Native toolCalls (if the API ever surfaces them) win; otherwise parse
    # JSON tool calls out of the prose.
    tool_calls = []
    for tc in message.get("toolCalls") or []:
        if "function" in tc:
            fn = tc["function"]
            tool_calls.append({
                "id": tc.get("id", ""),
                "name": fn.get("name"),
                "arguments": fn.get("arguments"),
            })
        elif "name" in tc:
            tool_calls.append({
                "id": tc.get("id", ""),
                "name": tc["name"],
                "arguments": tc.get("arguments"),
            })
    if not tool_calls and tool_schemas:
        tool_calls = _parse_tool_calls(text)

    return GrokReply(text=text, tool_calls=tool_calls, raw=data)
