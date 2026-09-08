"""LangGraph agent with Oracle AI Agent Memory (OAMP) as its memory core.

The repo's research agent uses a transparent hand-rolled loop so you can see every
step. If you build with a framework instead, OAMP drops in the same way — it is
framework-agnostic. This example wires it into LangGraph:

  - BEFORE the model runs: relevant durable memories are recalled from the database
    and prepended as context (the "memory in" edge)
  - AFTER each exchange: the messages are added to an OAMP thread, and OAMP's LLM
    extractor distills durable memories from them automatically (the "memory out" edge)

Run it (needs the local database from the quickstart + an Anthropic key):

    ./.venv/bin/pip install langgraph
    cd examples && ../.venv/bin/python langgraph_oamp.py

Ask it something, tell it a fact about yourself, restart it, and ask again — the
second process remembers, because the memory lives in the database, not the process.
The same pattern works for the OpenAI Agents SDK or the Claude Agent SDK: recall
before the run, add_messages after.
"""
import os
import pathlib
import sys

import anthropic
import oracledb
from dotenv import load_dotenv
from langgraph.graph import StateGraph, MessagesState, START, END

from oracleagentmemory.core import (
    OracleAgentMemory, SchemaPolicy, SearchStrategy)
from oracleagentmemory.core.embedders import OracleDBEmbedder
from oracleagentmemory.core.llms import Llm

load_dotenv(pathlib.Path(__file__).resolve().parent.parent / "oracle" / ".env")

MODEL = os.environ.get("LLM_MODEL", "claude-opus-4-8")
USER_ID = os.environ.get("BRAIN_USER", "me")

# --- the memory core: same database, official package ---
conn = oracledb.connect(
    user=os.environ.get("DB_USER", "CCC"),
    password=os.environ["APP_PWD"],
    dsn=os.environ.get("DB_DSN", "localhost:1521/FREEPDB1"),
)
memory = OracleAgentMemory(
    connection=conn,
    embedder=OracleDBEmbedder(connection=conn, model="MINILM",
                              embedding_dimension=384, max_input_tokens=128),
    llm=Llm(model=os.environ.get("OAMP_LLM_MODEL", "anthropic/claude-sonnet-5")),
    schema_policy=SchemaPolicy.CREATE_IF_NECESSARY,
    memory_store_id="brain",
    search_strategy=SearchStrategy.HYBRID,
)
thread = memory.create_thread(user_id=USER_ID, agent_id="langgraph-demo")
claude = anthropic.Anthropic()


def recall_node(state: MessagesState):
    """Memory in: fetch durable memories relevant to the latest user message."""
    question = state["messages"][-1].content
    hits = memory.search(query=question, user_id=USER_ID, max_results=5,
                         record_types=["memory", "fact", "preference"])
    if not hits:
        return {}
    context = "\n".join(f"- {getattr(h, 'content', h)}" for h in hits)
    return {"messages": [("system", f"Durable memories about this user:\n{context}")]}


def model_node(state: MessagesState):
    """The model turn — plain Anthropic SDK; swap in any provider or tool loop here."""
    msgs = [{"role": "user" if m.type in ("human", "system") else "assistant",
             "content": m.content} for m in state["messages"]]
    r = claude.messages.create(model=MODEL, max_tokens=1024, messages=msgs)
    return {"messages": [("assistant", r.content[0].text)]}


def remember_node(state: MessagesState):
    """Memory out: persist the exchange; OAMP extracts durable memories from it."""
    user_msg = next(m.content for m in reversed(state["messages"]) if m.type == "human")
    thread.add_messages([
        {"role": "user", "content": user_msg},
        {"role": "assistant", "content": state["messages"][-1].content},
    ])
    return {}


graph = StateGraph(MessagesState)
graph.add_node("recall", recall_node)
graph.add_node("model", model_node)
graph.add_node("remember", remember_node)
graph.add_edge(START, "recall")
graph.add_edge("recall", "model")
graph.add_edge("model", "remember")
graph.add_edge("remember", END)
app = graph.compile()


if __name__ == "__main__":
    print("LangGraph + OAMP demo — ctrl-c to quit. Tell it something; it remembers "
          "across restarts (the memory is in the database).")
    try:
        while True:
            q = input("\nyou> ").strip()
            if not q:
                continue
            out = app.invoke({"messages": [("user", q)]})
            print("agent>", out["messages"][-1].content)
    except (KeyboardInterrupt, EOFError):
        thread.wait_for_memory_extraction()   # let the extractor finish before exit
        conn.close()
        sys.exit(0)
