"""Turn an async generator of dict events into a Server-Sent-Events response."""
from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

from sse_starlette.sse import EventSourceResponse


def sse_response(events: AsyncIterator[dict[str, Any]]) -> EventSourceResponse:
    async def stream():
        async for event in events:
            yield {"data": json.dumps(event, default=str)}
        yield {"event": "end", "data": "{}"}

    return EventSourceResponse(stream())
