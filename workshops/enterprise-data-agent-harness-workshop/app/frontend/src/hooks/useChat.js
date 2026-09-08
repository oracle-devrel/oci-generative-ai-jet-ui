import { useCallback, useEffect, useReducer, useRef } from "react";

const NEW_THREAD_ID = () =>
  Math.random().toString(36).slice(2, 14);

const initialState = {
  threadId: NEW_THREAD_ID(),
  messages: [],
  trace: [],
  contextWindow: null,
  isThinking: false,
  threads: [],
  // touched: { "SCHEMA.TABLE": { action, ts } } — kept fresh by TABLES_TOUCHED
  // events from the backend. DataExplorer reads it and pulses the matching tabs.
  touched: {},
  // tokenUsage: { lastTurn: {...}, cumulative: {...}, modelMax: N } populated
  // by the backend's TOKEN_USAGE event after every chat completion.
  tokenUsage: { lastTurn: null, cumulative: { prompt: 0, completion: 0, total: 0 }, modelMax: 200_000, model: null },
};

function reducer(state, action) {
  switch (action.type) {
    case "USER_SUBMITTED":
      return {
        ...state,
        isThinking: true,
        trace: [],
        messages: [
          ...state.messages,
          { role: "user", content: action.payload, ts: Date.now() },
        ],
      };
    case "TOOL_STARTED":
      return {
        ...state,
        trace: [
          ...state.trace,
          { type: "tool_started", ...action.payload, ts: Date.now() },
        ],
      };
    case "TOOL_FINISHED":
      return {
        ...state,
        trace: [
          ...state.trace,
          { type: "tool_finished", ...action.payload, ts: Date.now() },
        ],
      };
    case "TURN_FINISHED":
      return {
        ...state,
        isThinking: false,
        messages: [
          ...state.messages,
          {
            role: "assistant",
            content: action.payload.answer,
            trace: state.trace,
            elapsed: action.payload.elapsed_seconds,
            ts: Date.now(),
          },
        ],
        trace: [],
      };
    case "CONTEXT_WINDOW":
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
      const u = action.payload;
      const cum = state.tokenUsage.cumulative;
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
      return { ...state, tokenUsage: next };
    }
    case "RESET_TOKENS":
      return {
        ...state,
        tokenUsage: { ...state.tokenUsage, cumulative: { prompt: 0, completion: 0, total: 0 }, lastTurn: null },
      };
    case "NEW_THREAD":
      return {
        ...state,
        threadId: NEW_THREAD_ID(),
        messages: [], trace: [], contextWindow: null, touched: {},
        tokenUsage: { ...state.tokenUsage, cumulative: { prompt: 0, completion: 0, total: 0 }, lastTurn: null },
      };
    case "LOAD_THREAD":
      return {
        ...state,
        threadId: action.payload,
        messages: [], trace: [], contextWindow: null, touched: {},
        tokenUsage: { ...state.tokenUsage, cumulative: { prompt: 0, completion: 0, total: 0 }, lastTurn: null },
      };
    case "LOAD_MESSAGES":
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
    const onTurnFinished = (p) => dispatch({ type: "TURN_FINISHED", payload: p });
    const onContextWindow = (p) => dispatch({ type: "CONTEXT_WINDOW", payload: p });
    const onTablesTouched = (p) => dispatch({ type: "TABLES_TOUCHED", payload: p });
    const onTokenUsage = (p) => dispatch({ type: "TOKEN_USAGE", payload: p });

    socket.on("turn_started", onTurnStarted);
    socket.on("tool_started", onToolStarted);
    socket.on("tool_finished", onToolFinished);
    socket.on("turn_finished", onTurnFinished);
    socket.on("context_window", onContextWindow);
    socket.on("tables_touched", onTablesTouched);
    socket.on("token_usage", onTokenUsage);

    fetchThreads();

    return () => {
      socket.off("turn_started", onTurnStarted);
      socket.off("tool_started", onToolStarted);
      socket.off("tool_finished", onToolFinished);
      socket.off("turn_finished", onTurnFinished);
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
      if (!socket || !content.trim()) return;
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

  const loadThread = useCallback((tid) => {
    dispatch({ type: "LOAD_THREAD", payload: tid });
    fetch(`/api/threads/${tid}/messages?limit=100`)
      .then((r) => r.json())
      .then((d) => {
        if (d.error) return;
        const msgs = (d.messages || []).map((m) => ({
          role: m.role,
          content: m.content,
          ts: m.timestamp,
        }));
        dispatch({ type: "LOAD_MESSAGES", payload: msgs });
      })
      .catch(() => {});
  }, []);

  const deleteThread = useCallback(
    (tid) => {
      fetch(`/api/threads/${tid}`, { method: "DELETE" })
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
    sendMessage,
    newThread,
    loadThread,
    deleteThread,
    fetchThreads,
    refreshContext,
    dispatch,
  };
}
