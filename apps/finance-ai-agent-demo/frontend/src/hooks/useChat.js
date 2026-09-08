import { useReducer, useCallback, useRef, useEffect } from "react";

const initialState = {
  threadId: `thread-${Date.now().toString(36)}`,
  messages: [],
  toolCalls: [],
  queries: [],
  appLogs: [],
  archEvents: [],
  isLoading: false,
  isCompacting: false,
  tokenUsage: null,
  querySummary: null,
  contextWindow: null,
  contextLoading: false,
  comparisonData: null,
  healthStatus: null,
};

function chatReducer(state, action) {
  switch (action.type) {
    case "SET_THREAD":
      return {
        ...state,
        threadId: action.payload,
        messages: [],
        toolCalls: [],
        queries: [],
        archEvents: [],
        contextWindow: null,
        tokenUsage: null,
      };

    case "LOAD_MESSAGES":
      return {
        ...state,
        messages: action.payload.map((m) => ({
          id: m.id,
          role: m.role,
          content: m.content,
          timestamp: m.timestamp,
          toolCalls: m.toolCalls || [],
        })),
      };

    case "ADD_USER_MESSAGE":
      return {
        ...state,
        messages: [
          ...state.messages,
          {
            id: `user-${Date.now()}`,
            role: "user",
            content: action.payload,
            timestamp: new Date().toISOString(),
          },
        ],
        isLoading: true,
        toolCalls: [],
        archEvents: [
          ...state.archEvents,
          {
            id: `arch-${Date.now()}`,
            type: "user_message",
            label: "User query → Backend",
            timestamp: Date.now(),
          },
        ].slice(-100),
      };

    case "ADD_TOOL_CALL_START":
      return {
        ...state,
        toolCalls: [
          ...state.toolCalls,
          {
            id: action.payload.tool_call_id,
            name: action.payload.tool_name,
            args: action.payload.tool_args,
            status: "running",
            output: null,
            elapsed_ms: null,
          },
        ],
        archEvents: [
          ...state.archEvents,
          {
            id: `arch-tc-${Date.now()}`,
            type: "tool_call",
            label: `${action.payload.tool_name}`,
            timestamp: Date.now(),
          },
        ].slice(-100),
      };

    case "UPDATE_TOOL_CALL":
      return {
        ...state,
        toolCalls: state.toolCalls.map((tc) =>
          tc.id === action.payload.tool_call_id
            ? {
                ...tc,
                status: action.payload.status,
                output: action.payload.output,
                elapsed_ms: action.payload.elapsed_ms,
              }
            : tc
        ),
      };

    case "ADD_QUERY":
      return {
        ...state,
        queries: [action.payload, ...state.queries].slice(0, 200),
        archEvents: [
          ...state.archEvents,
          {
            id: `arch-qr-${Date.now()}-${Math.random()}`,
            type: "query_result",
            label: `${action.payload.query_type || "query"} result`,
            timestamp: Date.now(),
          },
        ].slice(-100),
      };

    case "RESPONSE_CHUNK": {
      const existingMsg = state.messages.find((m) => m.id === action.payload.message_id);
      if (existingMsg) {
        return {
          ...state,
          messages: state.messages.map((m) =>
            m.id === action.payload.message_id
              ? { ...m, content: (m.content || "") + action.payload.chunk }
              : m
          ),
        };
      }
      // First chunk for this message — fire architecture response event
      return {
        ...state,
        messages: [
          ...state.messages,
          {
            id: action.payload.message_id,
            role: "assistant",
            content: action.payload.chunk,
            timestamp: new Date().toISOString(),
            isStreaming: true,
            toolCalls: [],
          },
        ],
        archEvents: [
          ...state.archEvents,
          {
            id: `arch-res-${Date.now()}`,
            type: "response",
            label: "LLM response → Frontend",
            timestamp: Date.now(),
          },
        ].slice(-100),
      };
    }

    case "AGENT_COMPLETE": {
      const streamingExists = state.messages.find((m) => m.id === action.payload.message_id);
      if (streamingExists) {
        return {
          ...state,
          messages: state.messages.map((m) =>
            m.id === action.payload.message_id
              ? {
                  ...m,
                  content: action.payload.response || m.content,
                  isStreaming: false,
                  toolCalls: [...state.toolCalls],
                }
              : m
          ),
          isLoading: false,
          querySummary: action.payload.query_summary,
          toolCalls: [],
        };
      }
      return {
        ...state,
        messages: [
          ...state.messages,
          {
            id: action.payload.message_id,
            role: "assistant",
            content: action.payload.response,
            timestamp: new Date().toISOString(),
            toolCalls: [...state.toolCalls],
          },
        ],
        isLoading: false,
        querySummary: action.payload.query_summary,
        toolCalls: [],
      };
    }

    case "UPDATE_TOKEN_USAGE":
      return { ...state, tokenUsage: action.payload };

    case "ADD_SYSTEM_MESSAGE":
      return {
        ...state,
        messages: [
          ...state.messages,
          {
            id: `sys-${Date.now()}`,
            role: "system",
            content: action.payload,
            timestamp: new Date().toISOString(),
          },
        ],
      };

    case "ADD_APP_LOG":
      return {
        ...state,
        appLogs: [...state.appLogs, action.payload].slice(-200),
      };

    case "CLEAR_APP_LOGS":
      return { ...state, appLogs: [] };

    case "CLEAR_QUERIES":
      return { ...state, queries: [], querySummary: null };

    case "SET_LOADING":
      return { ...state, isLoading: action.payload };

    case "SET_COMPACTING":
      return { ...state, isCompacting: action.payload };

    case "SET_CONTEXT_LOADING":
      return { ...state, contextLoading: action.payload };

    case "UPDATE_CONTEXT_WINDOW":
      return { ...state, contextWindow: action.payload, contextLoading: false };

    case "SET_COMPARISON_DATA":
      return { ...state, comparisonData: action.payload, isLoading: false };

    case "ADD_COMPARISON_LATENCY_POINT":
      return {
        ...state,
        comparisonData: {
          ...(state.comparisonData || {}),
          latency_points: [...((state.comparisonData || {}).latency_points || []), action.payload],
        },
      };

    case "SET_HEALTH_STATUS":
      return { ...state, healthStatus: action.payload };

    default:
      return state;
  }
}

export function useChat(socket) {
  const [state, dispatch] = useReducer(chatReducer, initialState);
  const stateRef = useRef(state);
  stateRef.current = state;

  // Register socket listeners
  useEffect(() => {
    if (!socket) return;

    const handlers = {
      tool_call_start: (data) => dispatch({ type: "ADD_TOOL_CALL_START", payload: data }),
      tool_call_complete: (data) => dispatch({ type: "UPDATE_TOOL_CALL", payload: data }),
      query_executed: (data) => dispatch({ type: "ADD_QUERY", payload: data }),
      response_chunk: (data) => dispatch({ type: "RESPONSE_CHUNK", payload: data }),
      agent_complete: (data) => dispatch({ type: "AGENT_COMPLETE", payload: data }),
      token_usage_update: (data) => dispatch({ type: "UPDATE_TOKEN_USAGE", payload: data }),
      thread_loaded: (data) => {
        if (data.error) {
          dispatch({ type: "ADD_SYSTEM_MESSAGE", payload: `Thread not found: ${data.thread_id}` });
        } else {
          dispatch({ type: "LOAD_MESSAGES", payload: data.messages });
          // Auto-refresh context window for the loaded thread
          const lastUserMsg = data.messages?.filter((m) => m.role === "user").pop();
          socket.emit("request_context_window", {
            thread_id: stateRef.current.threadId,
            query: lastUserMsg?.content || "",
          });
        }
        dispatch({ type: "SET_LOADING", payload: false });
      },
      thread_created: (data) => {
        dispatch({ type: "SET_THREAD", payload: data.thread_id });
      },
      compaction_complete: (data) => {
        dispatch({ type: "SET_COMPACTING", payload: false });
        const desc = data.description ? ` — "${data.description}"` : "";
        const msg = `Context compacted: ${data.tokens_before} -> ${data.tokens_after} tokens (${data.messages_compacted} messages summarized as Summary ID: ${data.summary_id}${desc})`;
        dispatch({ type: "ADD_SYSTEM_MESSAGE", payload: msg });
      },
      file_processing_complete: (data) => {
        dispatch({
          type: "ADD_SYSTEM_MESSAGE",
          payload: `Uploaded ${data.filename} - ${data.chunks_created} chunks processed and added to knowledge base.`,
        });
      },
      context_window_update: (data) => {
        dispatch({ type: "UPDATE_CONTEXT_WINDOW", payload: data });
      },
      app_log: (data) => {
        dispatch({ type: "ADD_APP_LOG", payload: data });
      },
      comparison_complete: (data) => {
        dispatch({ type: "SET_COMPARISON_DATA", payload: data });
        if (data.response) {
          dispatch({
            type: "RESPONSE_CHUNK",
            payload: { message_id: `cmp-${Date.now()}`, chunk: data.response },
          });
        }
      },
      comparison_latency_point: (data) => {
        dispatch({ type: "ADD_COMPARISON_LATENCY_POINT", payload: data });
      },
      health_check_result: (data) => {
        dispatch({ type: "SET_HEALTH_STATUS", payload: data });
      },
    };

    Object.entries(handlers).forEach(([event, handler]) => {
      socket.on(event, handler);
    });

    return () => {
      Object.entries(handlers).forEach(([event, handler]) => {
        socket.off(event, handler);
      });
    };
  }, [socket]);

  const sendMessage = useCallback(
    (message) => {
      if (!socket || !message.trim()) return;
      dispatch({ type: "ADD_USER_MESSAGE", payload: message });
      dispatch({ type: "CLEAR_QUERIES" });
      dispatch({ type: "CLEAR_APP_LOGS" });
      socket.emit("send_message", {
        message,
        thread_id: stateRef.current.threadId,
      });
    },
    [socket]
  );

  const newThread = useCallback(() => {
    if (!socket) return;
    socket.emit("new_thread", {});
  }, [socket]);

  const loadThread = useCallback(
    (threadId) => {
      if (!socket) return;
      dispatch({ type: "SET_THREAD", payload: threadId });
      dispatch({ type: "SET_LOADING", payload: true });
      socket.emit("load_thread", { thread_id: threadId });
    },
    [socket]
  );

  const triggerCompaction = useCallback(() => {
    if (!socket || stateRef.current.isCompacting) return;
    dispatch({ type: "SET_COMPACTING", payload: true });
    socket.emit("trigger_compaction", {
      thread_id: stateRef.current.threadId,
    });
  }, [socket]);

  const requestContextWindow = useCallback(() => {
    if (!socket) return;
    dispatch({ type: "SET_CONTEXT_LOADING", payload: true });
    const lastUserMsg = stateRef.current.messages.filter((m) => m.role === "user").pop();
    socket.emit("request_context_window", {
      thread_id: stateRef.current.threadId,
      query: lastUserMsg?.content || "",
    });
  }, [socket]);

  const sendComparison = useCallback(
    (message) => {
      if (!socket || !message.trim()) return;
      dispatch({ type: "ADD_USER_MESSAGE", payload: message });
      dispatch({ type: "CLEAR_QUERIES" });
      dispatch({ type: "CLEAR_APP_LOGS" });
      dispatch({ type: "SET_COMPARISON_DATA", payload: { latency_points: [] } });
      socket.emit("send_comparison", {
        message,
        thread_id: stateRef.current.threadId,
      });
    },
    [socket]
  );

  const checkHealth = useCallback(() => {
    if (!socket) return;
    socket.emit("health_check", {});
  }, [socket]);

  return {
    ...state,
    sendMessage,
    sendComparison,
    newThread,
    loadThread,
    triggerCompaction,
    requestContextWindow,
    checkHealth,
    dispatch,
  };
}
