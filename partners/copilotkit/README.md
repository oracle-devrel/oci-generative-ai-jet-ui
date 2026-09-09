<!-- DRAFT — destined for oracle-devrel/oracle-ai-developer-hub at partners/copilotkit/.
     Self-contained: the recipe (cookbook.md), a runnable starter (demo/), and a skills
     pointer all live in this directory. -->

# Partners · CopilotKit

[CopilotKit](https://www.copilotkit.ai/) is the frontend interaction layer for AI agents —
chat, generative UI, and human-in-the-loop — over the open [AG-UI](https://docs.ag-ui.com/)
protocol. This directory shows how to build agentic, memory-augmented experiences on
**Oracle AI Database** with CopilotKit, defining the agent once as portable JSON with
**Oracle Agent Spec**.

## Cookbook

| Recipe | Description | Stack |
| --- | --- | --- |
| [Portable agent with Agent Spec, memory & CopilotKit](./cookbook.md) | A travel concierge — an Oracle **Agent Spec** agent on LangGraph, served over AG-UI to a CopilotKit V2 chat, with long-term memory on Oracle AI Database and human-in-the-loop booking. | CopilotKit · Oracle Agent Spec · Oracle Agent Memory · LangGraph · AG-UI |

## What's here

| Path | What it is |
| --- | --- |
| [`cookbook.md`](./cookbook.md) | The written recipe — architecture, run steps, and the key code. |
| [`demo/`](./demo/) | The runnable starter: the Agent Spec agent, the CopilotKit V2 frontend, and a local Oracle AI Database. Start at [`demo/README.md`](./demo/README.md). |
| [`skills/`](./skills/) | CopilotKit **Agent Skills** for coding agents — `npx skills add CopilotKit/CopilotKit/skills`. |

## Quick start

```bash
cd demo
docker compose up -d && ./db/setup-db.sh                          # local Oracle AI Database
cd agent && cp .env.example .env && uv sync \
  && uv run uvicorn concierge.server:app --reload --port 8000     # add OPENAI_API_KEY to .env
cd ../frontend && cp .env.local.example .env.local \
  && npm install && npm run dev
```

Open <http://localhost:3000>. Full walkthrough → [`cookbook.md`](./cookbook.md).

The written guide is also published on the CopilotKit docs at
[docs.copilotkit.ai/cookbook](https://docs.copilotkit.ai/cookbook).
