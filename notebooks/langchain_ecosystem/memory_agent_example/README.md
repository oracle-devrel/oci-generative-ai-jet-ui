# Customer Memory Agent (LangGraph + Oracle AI Database)

A minimal LangGraph agent demonstrating long-term memory (OracleStore)
separated from thread-level checkpointing (OracleSaver) on Oracle AI Database.

## Setup
1. Run Oracle AI Database Free in Docker.
2. `pip install oracledb langgraph langgraph-oracledb langchain langchain-anthropic python-dotenv`
3. Set `ANTHROPIC_API_KEY` and `DB_PASSWORD` in a `.env` file.
4. Run `agent.py` (session 1), then `session2.py` (new thread, same user) to see memory recall.
