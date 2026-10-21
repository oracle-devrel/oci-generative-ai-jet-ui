"""Part 5 plumbing: OAMP thread store, turn setup and teardown, tool dispatch and tool-output offload."""
import concurrent.futures
import json
import threading
import time
import warnings
from types import SimpleNamespace

from oracleagentmemory.apis.thread import Message
from oracleagentmemory.core import MemoryExtractionConfig

OFFLOAD_TTL_DAYS = 7

# The SDK warns once per thread; the searches then run serially, which is what this harness needs.
warnings.filterwarnings("ignore", message="context_card_type_search_concurrency", category=RuntimeWarning)

MEMORY_CFG = MemoryExtractionConfig(
    extract_memories=True,
    memory_extraction_frequency=2,
    memory_extraction_window=4,
    enable_context_summary=True,
    context_summary_update_frequency=4,
)


class ThreadStore:
    """OAMP threads for one user/agent pair. OAMP is not thread-safe, so every call takes one lock."""

    def __init__(self, memory_client, user_id, agent_id):
        self.client, self.user_id, self.agent_id = memory_client, user_id, agent_id
        self.lock = threading.RLock()
        self.threads = {}
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=4, thread_name_prefix="oamp-log")
        self._pending = []

    def get_thread(self, thread_id):
        with self.lock:
            if thread_id in self.threads:
                return self.threads[thread_id]
            try:
                thread = self.client.get_thread(thread_id)
            except Exception:
                try:
                    thread = self.client.create_thread(
                        thread_id=thread_id, user_id=self.user_id, agent_id=self.agent_id,
                        memory_extraction_config=MEMORY_CFG)
                except ValueError:
                    thread = self.client.get_thread(thread_id)
            self.threads[thread_id] = thread
            return thread

    def context_card(self, thread_id):
        """The thread's rolling summary as text, or "" if OAMP cannot build it right now."""
        try:
            return str(self.get_thread(thread_id).get_context_card() or "")
        except Exception as e:
            print(f"  ! OAMP context card unavailable ({type(e).__name__}), continuing without it")
            return ""

    def log_message(self, thread_id, role, content):
        """Persist one message in the background so the loop never waits for the database."""
        def write():
            with self.lock:
                self.get_thread(thread_id).add_messages([Message(role=role, content=content)])
        self._pending[:] = [f for f in self._pending if not f.done()]
        self._pending.append(self._executor.submit(write))

    def finish_turn(self, thread_id, user_query, final):
        """Log the answer and store the whole exchange as one episodic memory."""
        self.log_message(thread_id, "assistant", final)
        try:
            with self.lock:
                self.client.add_memory(
                    f"User: {user_query}\n\nAssistant: {final}",
                    user_id=self.user_id, agent_id=self.agent_id, thread_id=thread_id,
                    metadata={"kind": "episodic", "thread_id": thread_id,
                              "user_query": user_query[:240]})
        except Exception:
            pass

    def raw_vs_card(self, thread_id, texts):
        """Add user messages to a thread; return the raw transcript and the context card built from it."""
        thread = self.get_thread(thread_id)
        with self.lock:
            thread.add_messages([Message(role="user", content=t) for t in texts])
            raw = "\n".join(m.content for m in thread.get_messages())
        return raw, self.context_card(thread_id)

    def log_tool_output(self, thread_id, tool_call_id, tool_name, tool_args, output):
        """Store the full output of a tool call as an expiring OAMP memory."""
        self.get_thread(thread_id)
        with self.lock:
            self.client.add_memory(
                output, user_id=self.user_id, agent_id=self.agent_id, thread_id=thread_id,
                metadata={"kind": "tool_output", "tool_call_id": tool_call_id,
                          "tool_name": tool_name, "tool_args": json.dumps(tool_args)},
                ttl_days=OFFLOAD_TTL_DAYS)

    def offloader(self, thread_id, limit):
        """Hook for `call_tool`: keep outputs up to `limit` characters, else a preview plus a pointer."""
        def offload(tool_call_id, name, args, output):
            if len(output) <= limit:
                return output
            self.log_tool_output(thread_id, tool_call_id, name, args, output)
            return (output[:limit] + f"...[+{len(output) - limit} chars. "
                    f"full output: fetch_tool_output(tool_call_id='{tool_call_id}')]")
        return offload

    def fetch_tool_output(self, tool_call_id):
        """JSON string with the stored output of an earlier tool call."""
        with self.lock:
            rows = self.client._store.list(
                "memory", user_id=self.user_id, agent_id=self.agent_id,
                metadata_filter={"kind": "tool_output", "tool_call_id": tool_call_id}, limit=1)
        if not rows:
            return json.dumps({"error": f"no offloaded output for {tool_call_id}"})
        meta = rows[0].metadata or {}
        return json.dumps({"tool_name": meta.get("tool_name"), "tool_output": str(rows[0].content)})


def assistant_message(msg):
    """Echo an assistant message with its tool calls, so every tool result has a matching call."""
    return {"role": "assistant", "content": msg.content or "",
            "tool_calls": [{"id": tc.id, "type": "function",
                            "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                           for tc in msg.tool_calls]}


def call_tool(tools, tc, step=0, verbose=True, offload=None):
    """Run one tool call. Bad JSON becomes {}, unknown tools and exceptions become a JSON error.

    `offload(tool_call_id, name, args, output)` may replace the output with a shorter reference.
    """
    name = tc.function.name
    try:
        args = json.loads(tc.function.arguments or "{}")
    except json.JSONDecodeError:
        args = {}
    if verbose:
        print(f"  step {step}: -> {name}({json.dumps(args)[:110]})")
    if name not in tools:
        output = json.dumps({"error": f"unknown tool: {name}"})
    else:
        try:
            output = tools[name][0](**args)
        except Exception as e:
            output = json.dumps({"error": f"{type(e).__name__}: {e}"})
    return offload(tc.id, name, args, output) if offload else output


def start_turn(store, thread_id, user_query, system_prompt, build_context, retrieve_tools, offload_chars):
    """Log the question and return (messages, tool schemas, offload hook, start time) for one turn."""
    started = time.time()
    store.log_message(thread_id, "user", user_query)
    messages = [{"role": "system", "content": system_prompt},
                {"role": "user", "content": build_context(thread_id, user_query)}]
    return messages, retrieve_tools(user_query, k=6), store.offloader(thread_id, offload_chars), started


def budgeted_steps(max_iterations, started, budget_seconds):
    """Yield step numbers 0..max_iterations-1, and stop early once the wall-clock budget is spent."""
    for step in range(max_iterations):
        if time.time() - started > budget_seconds:
            return
        yield step


def end_turn(store, chat, thread_id, user_query, final, messages, started, verbose):
    """Force an answer if the loop produced none, store the exchange and return the answer."""
    steps = sum(m["role"] == "assistant" for m in messages) + 1
    final = final or force_final_answer(chat, messages)
    store.finish_turn(thread_id, user_query, final)
    if verbose:
        print(f"  [{time.time() - started:.1f}s, {steps} steps]")
    return final


def force_final_answer(chat, messages):
    """Out of steps or time: ask once more, without tools, for the best answer so far."""
    messages.append({"role": "user",
                     "content": "Budget exhausted. Provide your best answer now, no more tools."})
    return chat(messages, tools=None).choices[0].message.content or "(no answer produced)"


def check_agent_turn(ns):
    """TODO 8 checkpoint: run `ns["agent_turn"]` against a scripted model and a probe tool.

    The model first asks for the probe tool, then answers. A correct loop runs the tool, appends its
    result, calls the model once more and stops. `ns` is the notebook namespace; the fakes replace
    chat, store, build_context, retrieve_tools and TOOLS only for the duration of the call.
    """
    chat_calls, ran = [], []

    def scripted_chat(messages, tools=None, **kwargs):
        chat_calls.append([dict(m) for m in messages])
        if len(chat_calls) == 1:
            call = SimpleNamespace(id="probe-1", function=SimpleNamespace(name="probe", arguments='{"x": 2}'))
            msg = SimpleNamespace(content=None, tool_calls=[call])
        else:
            msg = SimpleNamespace(content="final answer", tool_calls=[])
        return SimpleNamespace(choices=[SimpleNamespace(message=msg)])

    class QuietStore:
        def log_message(self, *args): pass
        def finish_turn(self, *args): pass
        def offloader(self, thread_id, limit): return None

    def probe(x):
        ran.append(x)
        return "probe result"

    fakes = {"chat": scripted_chat, "store": QuietStore(), "build_context": lambda thread_id, query: query,
             "retrieve_tools": lambda query, k=6: [], "TOOLS": {"probe": (probe, {})}}
    saved = {name: ns[name] for name in fakes}
    ns.update(fakes)
    try:
        answer = ns["agent_turn"]("probe?", thread_id="todo9-check", max_iterations=4, verbose=False)
    except Exception as e:
        raise AssertionError(f"❌ TODO 8: agent_turn raised {type(e).__name__}: {e}") from None
    finally:
        ns.update(saved)
    assert ran == [2], "❌ TODO 8: the tool call was not dispatched with its arguments through call_tool."
    tool_msgs = [m for m in (chat_calls[1] if len(chat_calls) > 1 else []) if m["role"] == "tool"]
    assert tool_msgs == [{"role": "tool", "tool_call_id": "probe-1", "content": "probe result"}], \
        "❌ TODO 8: the tool result must be appended as a role='tool' message before the next chat call."
    echoed = [m for m in (chat_calls[1] if len(chat_calls) > 1 else []) if m["role"] == "assistant"]
    assert echoed and [c["id"] for c in echoed[-1].get("tool_calls", [])] == ["probe-1"], \
        "❌ TODO 8: append assistant_message(msg) before the tool results, so every result has a matching call."
    assert len(chat_calls) == 2, \
        "❌ TODO 8: the loop must stop as soon as the model answers without tool calls; keep the given `break` and the tool branch intact."
    assert answer == "final answer", "❌ TODO 8: agent_turn must return the model's final answer."
    print("✅ TODO 8 passed: the loop ran the tool, appended its result, and stopped on the answer.")
