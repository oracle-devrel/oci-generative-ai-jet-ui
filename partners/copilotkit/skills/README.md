# CopilotKit skills for this recipe

This recipe pairs with the **CopilotKit Agent Skills** — `SKILL.md` files that teach a
coding agent (Claude Code, Codex, Cursor, OpenCode) how to build with CopilotKit. They're
built on the open [Agent Skills](https://agentskills.io) standard, so one set works across
agents.

## Install

```bash
npx skills add CopilotKit/CopilotKit/skills
```

Fresh clone every time — run it again to update. Source of truth:
[`CopilotKit/CopilotKit/skills`](https://github.com/CopilotKit/CopilotKit/tree/main/skills).

## Most relevant to this recipe

| Skill | Use it for |
| --- | --- |
| `copilotkit-setup` | Scaffolding a CopilotKit app and its runtime endpoint. |
| `copilotkit-integrations` | Wiring an external agent into CopilotKit over AG-UI. |
| `copilotkit-agui` | The AG-UI protocol itself — events, client SDK, agent wiring. |
| `react-core` | Frontend hooks: chat, generative UI, human-in-the-loop, threads. |
| `runtime` | The CopilotKit runtime — agent runners, server-side tools, setup. |

## For this recipe specifically

The agent here is an Oracle **Agent Spec** agent served over AG-UI, so on the CopilotKit
side you wire it like any AG-UI agent — an `HttpAgent` pointing at the agent's `/run`
endpoint. The Oracle-specific glue — defining the agent in Agent Spec (`pyagentspec`), the
`ag_ui_agentspec` adapter on the LangGraph runtime, and long-term memory on Oracle AI
Database (`oracleagentmemory`) — is walked through in [`../cookbook.md`](../cookbook.md) and
runnable in [`../demo/`](../demo/).
