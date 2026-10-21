import { useCallback, useEffect, useReducer, useRef } from "react";

const NEW_THREAD_ID = () =>
  Math.random().toString(36).slice(2, 14);

const EMPTY_USAGE = {
  lastTurn: null,
  cumulative: { prompt: 0, completion: 0, total: 0 },
  modelMax: 200_000,
  model: null,
};

const initialState = {
  threadId: NEW_THREAD_ID(),
  messages: [],
  trace: [],
  contextWindow: null,
  // Thread the in-flight agent turn belongs to (null when idle). Tool events
  // carry no thread id, so exactly one turn runs at a time; the user can still
  // switch threads while it runs and the turn's events must not leak into the
  // thread they switched to.
  pendingThreadId: null,
  threads: [],
  // touched: { "SCHEMA.TABLE": { action, ts } } — kept fresh by TABLES_TOUCHED
  // events from the backend. DataExplorer reads it and pulses the matching tabs.
  touched: {},
  // tokenUsage: { lastTurn: {...}, cumulative: {...}, modelMax: N } for the
  // *visible* thread, fed by the backend's TOKEN_USAGE event after every chat
  // completion. tokenUsageByThread keeps each thread's own numbers so a turn
  // that finishes in a thread the user has left can't leak into the one they
  // are looking at, yet is still there when they navigate back.
  tokenUsage: { ...EMPTY_USAGE },
  tokenUsageByThread: {},
};

function threadTokenUsage(state, threadId) {
  const own = state.tokenUsageByThread[threadId];
  return {
    ...EMPTY_USAGE,
    modelMax: state.tokenUsage.modelMax,
    model: state.tokenUsage.model,
    ...(own || {}),
  };
}

function reducer(state, action) {
  switch (action.type) {
    case "USER_SUBMITTED":
      return {
        ...state,
        pendingThreadId: state.threadId,
        trace: [],
        messages: [
          ...state.messages,
          { role: "user", content: action.payload, ts: Date.now() },
        ],
      };
    case "TOOL_STARTED":
      if (!state.pendingThreadId) return state;
      return {
        ...state,
        trace: [
          ...state.trace,
          { type: "tool_started", ...action.payload, ts: Date.now() },
        ],
      };
    case "TOOL_FINISHED":
      if (!state.pendingThreadId) return state;
      return {
        ...state,
        trace: [
          ...state.trace,
          { type: "tool_finished", ...action.payload, ts: Date.now() },
        ],
      };
    case "TURN_FINISHED": {
      // The user switched threads mid-turn: the answer is persisted server-side
      // and shows up when they reopen that thread — don't paste it into this one.
      const here = !action.payload.thread_id || action.payload.thread_id === state.threadId;
      return {
        ...state,
        pendingThreadId: null,
        messages: here
          ? [
              ...state.messages,
              {
                role: "assistant",
                content: action.payload.answer,
                trace: state.trace,
                elapsed: action.payload.elapsed_seconds,
                ts: Date.now(),
              },
            ]
          : state.messages,
        trace: [],
      };
    }
    case "TURN_ABORTED":
      // Socket dropped mid-turn: the reply (sent to the old connection) is lost.
      if (!state.pendingThreadId) return state;
      return {
        ...state,
        pendingThreadId: null,
        trace: [],
        messages:
          state.pendingThreadId === state.threadId
            ? [
                ...state.messages,
                {
                  role: "assistant",
                  content:
                    "⚠️ Connection lost before the answer arrived. The agent may still have finished — reopen this thread from History to check.",
                  ts: Date.now(),
                },
              ]
            : state.messages,
      };
    case "CONTEXT_WINDOW":
      // A refresh for a thread the user already left must not repopulate the pane.
      if (action.payload?.thread_id && action.payload.thread_id !== state.threadId) return state;
      return { ...state, contextWindow: action.payload };
    case "TABLES_TOUCHED": {
      const ts = Date.now();
      const next = { ...state.touched };
      for (const t of action.payload.tables || []) {
        next[t] = { action: action.payload.action || "read", ts };
      }
      return { ...state, touched: next };
    }
    case "TABLES_TOUCHED_GC":
      return { ...state, touched: action.payload };
    case "TOKEN_USAGE": {
      // token_usage carries no thread id; it belongs to the in-flight turn's
      // thread. File it under that thread, and only show it when that thread
      // is the visible one (the user may have switched away mid-turn).
      const u = action.payload;
      const owner = state.pendingThreadId || state.threadId;
      const prev = state.tokenUsageByThread[owner] || EMPTY_USAGE;
      const cum = prev.cumulative;
      const next = {
        lastTurn: { prompt: u.prompt, completion: u.completion, total: u.total, step: u.step },
        cumulative: {
          prompt: cum.prompt + (u.prompt || 0),
          completion: cum.completion + (u.completion || 0),
          total: cum.total + (u.total || 0),
        },
        modelMax: u.model_max || state.tokenUsage.modelMax,
        model: u.model || state.tokenUsage.model,
      };
      return {
        ...state,
        tokenUsageByThread: { ...state.tokenUsageByThread, [owner]: next },
        tokenUsage: owner === state.threadId ? next : state.tokenUsage,
      };
    }
    case "NEW_THREAD": {
      const threadId = NEW_THREAD_ID();
      return {
        ...state,
        threadId,
        messages: [], contextWindow: null, touched: {},
        tokenUsage: threadTokenUsage(state, threadId),
      };
    }
    case "LOAD_THREAD":
      // Keep the thread's own usage if this session already ran turns in it
      // (e.g. a turn that finished while the user was elsewhere).
      return {
        ...state,
        threadId: action.payload,
        messages: [], contextWindow: null, touched: {},
        tokenUsage: threadTokenUsage(state, action.payload),
      };
    case "LOAD_MESSAGES":
      // Ignore a slow response for a thread the user has since left.
      if (action.threadId !== state.threadId) return state;
      return { ...state, messages: action.payload };
    case "THREADS":
      return { ...state, threads: action.payload };
    default:
      return state;
  }
}

export function useChat(socket, identityId) {
  const [state, dispatch] = useReducer(reducer, initialState);
  const stateRef = useRef(state);
  stateRef.current = state;
  const identityRef = useRef(identityId);
  identityRef.current = identityId;

  useEffect(() => {
    if (!socket) return;
    const onTurnStarted = () => {};
    const onToolStarted = (p) => dispatch({ type: "TOOL_STARTED", payload: p });
    const onToolFinished = (p) => dispatch({ type: "TOOL_FINISHED", payload: p });
    const onTurnFinished = (p) => {
      dispatch({ type: "TURN_FINISHED", payload: p });
      // The first turn of a thread is what creates it server-side.
      fetchThreads();
    };
    const onDisconnect = () => dispatch({ type: "TURN_ABORTED" });
    const onContextWindow = (p) => dispatch({ type: "CONTEXT_WINDOW", payload: p });
    const onTablesTouched = (p) => dispatch({ type: "TABLES_TOUCHED", payload: p });
    const onTokenUsage = (p) => dispatch({ type: "TOKEN_USAGE", payload: p });

    socket.on("turn_started", onTurnStarted);
    socket.on("tool_started", onToolStarted);
    socket.on("tool_finished", onToolFinished);
    socket.on("turn_finished", onTurnFinished);
    socket.on("disconnect", onDisconnect);
    socket.on("context_window", onContextWindow);
    socket.on("tables_touched", onTablesTouched);
    socket.on("token_usage", onTokenUsage);

    fetchThreads();

    return () => {
      socket.off("turn_started", onTurnStarted);
      socket.off("tool_started", onToolStarted);
      socket.off("tool_finished", onToolFinished);
      socket.off("turn_finished", onTurnFinished);
      socket.off("disconnect", onDisconnect);
      socket.off("context_window", onContextWindow);
      socket.off("tables_touched", onTablesTouched);
      socket.off("token_usage", onTokenUsage);
    };
  }, [socket]);

  // Garbage-collect stale touched-table entries every second so the pulse
  // animation only stays visible for ~3.5s after the access happened.
  useEffect(() => {
    const id = window.setInterval(() => {
      const cutoff = Date.now() - 3500;
      const cur = stateRef.current.touched;
      let changed = false;
      const next = {};
      for (const [k, v] of Object.entries(cur)) {
        if (v.ts >= cutoff) {
          next[k] = v;
        } else {
          changed = true;
        }
      }
      if (changed) dispatch({ type: "TABLES_TOUCHED_GC", payload: next });
    }, 1000);
    return () => window.clearInterval(id);
  }, []);

  const sendMessage = useCallback(
    (content) => {
      if (!socket || !content.trim() || stateRef.current.pendingThreadId) return;
      dispatch({ type: "USER_SUBMITTED", payload: content });
      socket.emit("send_message", {
        thread_id: stateRef.current.threadId,
        content,
        as_user: identityRef.current || "agent",
      });
    },
    [socket],
  );

  const newThread = useCallback(() => dispatch({ type: "NEW_THREAD" }), []);

  const fetchThreads = useCallback(() => {
    fetch("/api/threads")
      .then((r) => r.json())
      .then((d) => dispatch({ type: "THREADS", payload: d.threads || [] }))
      .catch(() => {});
  }, []);

  const loadThread = useCallback(
    (tid) => {
      dispatch({ type: "LOAD_THREAD", payload: tid });
      // Fill the Context pane for the reopened thread (it was reset above).
      socket?.emit("request_context_window", { thread_id: tid, query: "" });
      fetch(`/api/threads/${encodeURIComponent(tid)}/messages?limit=100`)
        .then((r) => r.json())
        .then((d) => {
          if (d.error) return;
          const msgs = (d.messages || []).map((m) => ({
            role: m.role,
            content: m.content,
            ts: m.timestamp,
          }));
          dispatch({ type: "LOAD_MESSAGES", payload: msgs, threadId: tid });
        })
        .catch(() => {});
    },
    [socket],
  );

  const deleteThread = useCallback(
    (tid) => {
      fetch(`/api/threads/${encodeURIComponent(tid)}`, { method: "DELETE" })
        .then(() => {
          fetchThreads();
          // If the deleted thread was the active one, mint a fresh thread id.
          if (tid === stateRef.current.threadId) {
            dispatch({ type: "NEW_THREAD" });
          }
        })
        .catch(() => {});
    },
    [fetchThreads]
  );

  const refreshContext = useCallback(
    (query) => {
      if (!socket) return;
      socket.emit("request_context_window", {
        thread_id: stateRef.current.threadId,
        query: query || "",
      });
    },
    [socket],
  );

  return {
    ...state,
    // Per-thread view of the in-flight turn vs. "a turn is running somewhere".
    isThinking: state.pendingThreadId !== null && state.pendingThreadId === state.threadId,
    // In-flight tool calls belong to the pending thread only; hide them elsewhere.
    liveTrace: state.pendingThreadId === state.threadId ? state.trace : [],
    busy: state.pendingThreadId !== null,
    sendMessage,
    newThread,
    loadThread,
    deleteThread,
    fetchThreads,
    refreshContext,
    dispatch,
  };
}
