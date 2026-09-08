# The chat app

A live deployment of the workshop's multi-agent supervisor against the
same Oracle the notebook seeded. Three panes:

- **Chat (left)** — type a planner request, watch the supervisor's
  answer stream in token-by-token.
- **Agent context (right)** — one tab per agent (`supervisor`,
  `policy_agent`, `demand_analyst`). Each tab shows the agent's live
  status, every tool call it made (`get_user_memory`, `get_planner_policy`,
  `search_demand_reports`), the tool inputs and outputs, the agent's own
  streaming output, and its final summary.
- **Architecture explorer (bottom)** — animated React-Flow graph of the
  multi-agent system + the three Oracle persistence layers. Edges light
  up as tool calls fire and as the supervisor hands off to specialists.

## How it's wired

```
Browser   ◀── WebSocket /ws/chat ─▶   FastAPI (uvicorn :8000)
                                          │
                                          ▼
                              supervisor.astream_events("v2")
                                          │
                                          ▼
                              translated to typed events:
                              { type: "agent_started", agent: "policy_agent" }
                              { type: "tool_started",  agent: "policy_agent",
                                                       tool: "get_user_memory",
                                                       args: { user_id: "priya" }}
                              { type: "tool_finished", agent: "policy_agent", ... }
                              { type: "token",         agent: "supervisor",
                                                       token: "Recommendation:" }
                              { type: "final_answer",  content: "…" }
```

The same code paths the notebook builds in Parts 7–10 power this app —
the `OracleVS`, `AsyncOracleStore`, and `AsyncOracleSaver` are shared
process-level singletons in `app/backend/agent/tools.py` and
`app/backend/agent/supervisor.py`.

## Run it

The Codespace's `postStartCommand` runs `.devcontainer/start_app.sh`
which boots both the backend and the frontend. Locally:

```bash
# backend on :8000
python -m uvicorn app.backend.main:app --host 0.0.0.0 --port 8000

# frontend on :3000 (Vite dev server with /api + /ws proxy to :8000)
cd app/frontend && npm install && npm run dev -- --host 0.0.0.0 --port 3000
```

Open <http://localhost:3000>. The chat input has two starter prompts.

## Layout

```
app/
  backend/
    main.py                  # FastAPI entry point — /api/health, /api/agents, /ws/chat
    config.py                # LLM_PROVIDER + Oracle env + chat_model_kwargs() helper
    db/connections.py        # 1 sync + 2 async oracledb singletons
    agent/
      tools.py               # search_demand_reports, get_planner_policy, get_user_memory
      supervisor.py          # compiles demand_analyst + policy_agent + supervisor
      streaming.py           # LangGraph astream_events → frontend event surface
    api/websocket.py         # /ws/chat — translates events, pushes JSON frames
    requirements.txt
  frontend/
    package.json
    vite.config.ts           # /api and /ws proxied to localhost:8000
    src/
      App.tsx                # three-pane layout
      useAgentSocket.ts      # WebSocket client + state machine
      types.ts               # shared wire types
      components/
        ChatPane.tsx
        AgentContextPane.tsx
        ArchitectureExplorer.tsx   # React Flow node graph
      styles.css
  scripts/
    bootstrap.py             # AGENT user + vector pool (run during postCreate)
    onnx_setup.py            # downloads + loads ALL_MINILM_L12_V2
    seed_supplychain.py      # HF download → OracleVS + AsyncOracleStore
```

## Try these prompts

| Prompt                                                                                                                                                                                                                                                                         | What lights up                                                                                                                           |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------- |
| _"I'm planner with user_id=priya. We're debating how aggressively to stock soccer / football merchandise for the upcoming season. Pull demand intel from comparable SKUs in our history and draft a buy recommendation that respects my preferences and the standing policy."_ | All four data edges + both specialist nodes + the final supervisor synthesis. Watch Priya's preference appear in the `policy_agent` tab. |
| _"I'm user_id=michael. Push hard on kids' football cleats — I want a depth buy. Verify it against policy."_                                                                                                                                                                    | Same flow with the aggressive preference instead.                                                                                        |
| _"How are our soccer merchandise comps performing? Just give me the data, no recommendation."_                                                                                                                                                                                 | Supervisor delegates only to `demand_analyst`. `policy_agent` stays idle.                                                                |
