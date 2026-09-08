# Manual UI test checklist

Run:

    uv run uvicorn soccer_agent.api.main:app --reload

Open http://localhost:8000/ and check:

- [ ] Page loads, shows ⚽ header and input box.
- [ ] Send "hello" — assistant bubble appears with reply.
- [ ] Send "What is Spain vs Brazil?" — tool_trace details element shows
      one or more calls (lookup_prediction, sql_query).
- [ ] Expanding the trace shows pretty-printed JSON.
- [ ] Click "Reset session" — transcript clears.
- [ ] Refresh page — sessionId resets, no errors in browser console.

Per project rules: open the browser before declaring this task done.
