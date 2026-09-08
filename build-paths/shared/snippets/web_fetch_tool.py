"""LangChain BaseTool that fetches a URL and returns extracted main-body text.

WHY THIS EXISTS
---------------
Advanced idea 2 (self-improving research agent) needs an outbound HTTP tool
so the agent can read articles, save findings, and retrieve them later. The
SKILL referenced this tool but did not specify its shape — friction P0-6.
This is the canonical implementation.

The `(url, fallback_query)` shape lets the agent recover gracefully when a
URL 4xx/5xx or times out: it can pivot to a corpus search using the same
phrasing. This keeps the demo unblocked when the network is flaky.

USAGE
-----
    from langchain_core.tools import BaseTool
    from .web_fetch_tool import WebFetchTool, fetch_and_extract

    tool = WebFetchTool(corpus_search_fn=lambda q: vs.similarity_search(q, k=3))
    out = tool.invoke({"url": "https://...", "fallback_query": "arrow vs parquet"})

DEPS
----
httpx>=0.27
trafilatura>=1.10
"""

from __future__ import annotations

from typing import Any, Callable, Optional

import httpx
import trafilatura
from langchain_core.tools import BaseTool
from pydantic import Field


def fetch_and_extract(url: str, timeout: float = 8.0) -> str:
    """Fetch a URL with a short timeout and return cleaned main-body text.
    Raises `httpx.HTTPStatusError` on 4xx/5xx; returns empty string if the
    page has no extractable main content."""
    resp = httpx.get(url, timeout=timeout, follow_redirects=True)
    resp.raise_for_status()
    extracted = trafilatura.extract(resp.text, include_comments=False)
    return extracted or ""


class WebFetchTool(BaseTool):
    """Fetch a URL; on failure, fall back to a corpus search.

    Constructor takes `corpus_search_fn(query) -> str` so the SKILL can wire
    in any retriever (an `OracleVS.similarity_search` is the typical case).
    """

    name: str = "web_fetch"
    description: str = (
        "Fetch the main-body text of a URL. If the fetch fails, fall back "
        "to searching the project corpus for `fallback_query`. Returns "
        "extracted text. Args: url (str), fallback_query (str)."
    )

    corpus_search_fn: Optional[Callable[[str], str]] = Field(default=None, exclude=True)

    class Config:
        arbitrary_types_allowed = True

    def _run(self, url: str, fallback_query: str = "") -> str:  # type: ignore[override]
        try:
            text = fetch_and_extract(url)
            if text:
                return text
            raise ValueError("trafilatura returned empty extraction")
        except Exception as e:
            if self.corpus_search_fn and fallback_query:
                hits = self.corpus_search_fn(fallback_query)
                return (
                    f"[web_fetch failed: {type(e).__name__}: {e}; "
                    f"used corpus search for {fallback_query!r}]\n\n{hits}"
                )
            return f"[web_fetch failed: {type(e).__name__}: {e}]"
