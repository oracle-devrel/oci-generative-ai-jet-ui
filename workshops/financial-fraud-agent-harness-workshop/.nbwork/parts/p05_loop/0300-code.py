import json
from types import SimpleNamespace

sql = f"SELECT * FROM {DEMO_USER}.transactions FETCH FIRST 40 ROWS ONLY"
call = SimpleNamespace(id="call_demo_01", function=SimpleNamespace(name="run_sql", arguments=json.dumps({"sql": sql})))
shown = call_tool(TOOLS, call, offload=store.offloader("offload-demo", OFFLOAD_CHARS))
print(f"the model sees {len(shown)} chars, ending: ...{shown[-110:]}")

full = json.loads(tool_fetch_tool_output("call_demo_01"))["tool_output"]
print(f"fetch_tool_output returns the stored {len(full)} chars: {full[:60]}...")
