# oracle/ — the database and the agents

Everything that runs against Oracle AI Database 26ai lives here.

```
oracle/
├── docker-compose.yml     Oracle AI Database 26ai Free — local container
├── schema/                auto-applied on first boot: content tables + Duality views,
│                          the four agent-memory tables, and the wiki graph
├── setup/                 one-time SQL: load the in-DB ONNX embedding model,
│                          plus retrieval examples you can run by hand
├── bootstrap.sh           first-time setup in one command (schema + model)
├── download-model.sh      fetch the MiniLM ONNX model for in-DB embeddings
├── .env.example           copy to .env; CHANGE_ME_* placeholders work locally
└── agent/                 the Python side: db/content modules, the memory layer
                           (oamp_memory — the package default — plus the hand-built
                           learning track), the research and idea agents, the MCP
                           server (stdio + hosted HTTP), and runnable demo_*.py scripts
```

Start with the step-by-step workshop in [../docs/TUTORIAL.md](../docs/TUTORIAL.md) —
Lab 1 stands this folder up from zero. The architecture overview is in
[../docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md).
