import uuid
from langchain.chat_models import init_chat_model
from langgraph.graph import StateGraph, MessagesState, START
from langgraph.store.base import BaseStore
from langgraph_oracledb.checkpoint.oracle import OracleSaver
from langgraph_oracledb.store.oracle import OracleStore
from dotenv import load_dotenv
load_dotenv()

DB_URI = "dyndan_agent/YourPassword123@localhost:1521/FREEPDB1"
model = init_chat_model("claude-sonnet-4-6")

with (
    OracleStore.from_conn_string(DB_URI) as store,
    OracleSaver.from_conn_string(DB_URI) as checkpointer,
):
    store.setup()
    checkpointer.setup()

    def call_model(state: MessagesState, config, *, store: BaseStore):
        user_id = config["configurable"]["user_id"]
        namespace = ("preferences", user_id)
        memories = store.search(namespace)
        context = "\n".join(m.value["text"] for m in memories)
        system_msg = f"Known customer preferences:\n{context}"
        response = model.invoke([{"role": "system", "content": system_msg}, *state["messages"]])
        last_user_msg = state["messages"][-1].content
        if "prefer" in last_user_msg.lower() or "caffeine" in last_user_msg.lower():
            store.put(namespace, str(uuid.uuid4()), {"text": last_user_msg})
        return {"messages": [response]}

    builder = StateGraph(MessagesState)
    builder.add_node("call_model", call_model)
    builder.add_edge(START, "call_model")
    graph = builder.compile(checkpointer=checkpointer, store=store)

    config = {"configurable": {"thread_id": "session-1", "user_id": "dyndan-customer-42"}}
    result = graph.invoke(
        {"messages": [{"role": "user", "content": "I only drink DYNDAN Citrus Punch, no caffeine after 6pm."}]},
        config,
    )
    print(result["messages"][-1].content)