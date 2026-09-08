import { useRef, useEffect, useState, useCallback } from "react";
import ChatMessage from "./ChatMessage";
import ToolCallBubble from "./ToolCallBubble";
import ChatInput from "./ChatInput";
import TokenUsageBar from "./TokenUsageBar";
import FileDropZone from "./FileDropZone";
import { uploadFile } from "../utils/uploadFile";

const STARTER_QUERIES = [
  {
    icon: "\u{1F4CA}",
    label: "Portfolio Risk Analysis",
    query: "Analyze the portfolio risk for ACC-001 and identify any concentration issues",
  },
  {
    icon: "\u{1F50D}",
    label: "Convergent Search",
    query:
      "Run a convergent search for ACC-003 to find connected accounts, nearby clients, and relevant risk research",
  },
  {
    icon: "\u{1F4C4}",
    label: "Compliance & Knowledge",
    query:
      "What compliance rules apply to accounts in the same network as ACC-003, and what do our research documents say about concentration risk?",
  },
  {
    icon: "\u{1F30D}",
    label: "Spatial Proximity",
    query: "Which clients are within 500km of ACC-001 and do they share similar risk profiles?",
  },
];

export default function ChatPane({ chat, socket, archMode }) {
  const handleSend = useCallback(
    (msg) => {
      if (archMode === "comparison" && chat.sendComparison) {
        chat.sendComparison(msg);
      } else {
        chat.sendMessage(msg);
      }
    },
    [archMode, chat]
  );
  const messagesEndRef = useRef(null);
  const containerRef = useRef(null);
  const [autoScroll, setAutoScroll] = useState(true);
  const [isDragOver, setIsDragOver] = useState(false);

  // Auto-scroll
  useEffect(() => {
    if (autoScroll && messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [chat.messages, chat.toolCalls, autoScroll]);

  const handleScroll = useCallback(() => {
    const el = containerRef.current;
    if (!el) return;
    const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 100;
    setAutoScroll(atBottom);
  }, []);

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = () => setIsDragOver(false);

  const handleDrop = async (e) => {
    e.preventDefault();
    setIsDragOver(false);
    const files = Array.from(e.dataTransfer.files);
    for (const file of files) {
      await uploadFile(file, chat.threadId, chat.dispatch);
    }
  };

  return (
    <div
      className="flex-1 flex flex-col min-w-0 relative"
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      {/* Drag overlay */}
      {isDragOver && <FileDropZone />}

      {/* Messages area */}
      <div
        ref={containerRef}
        onScroll={handleScroll}
        className="flex-1 overflow-y-auto px-4 py-6 space-y-4"
      >
        {chat.messages.length === 0 && !chat.isLoading && (
          <div className="flex flex-col items-center justify-center h-full text-text-secondary">
            <div className="text-4xl mb-4">
              <svg
                width="48"
                height="48"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1"
                className="text-text-accent/30"
              >
                <path d="M12 2L2 7l10 5 10-5-10-5z" />
                <path d="M2 17l10 5 10-5" />
                <path d="M2 12l10 5 10-5" />
              </svg>
            </div>
            <p className="text-sm font-medium text-text-accent/60">AFSA</p>
            <p className="text-[11px] mt-0.5 text-text-secondary/50 tracking-wide">
              <span className="font-bold">A</span>gentic <span className="font-bold">F</span>
              inancial <span className="font-bold">S</span>ervice{" "}
              <span className="font-bold">A</span>ssistant
            </p>
            <p className="text-xs mt-2 text-text-secondary/60 max-w-md text-center">
              Ask about portfolio risk, compliance, accounts, or market research. All queries run
              against a single Oracle AI Database instance.
            </p>

            {/* Starter query buttons */}
            <div className="flex flex-col gap-2 mt-6 w-full max-w-lg">
              {STARTER_QUERIES.map((sq, i) => (
                <button
                  key={i}
                  onClick={() => handleSend(sq.query)}
                  className="group flex items-center gap-3 px-4 py-3 rounded-lg glow-border bg-secondary hover:bg-tertiary text-left transition"
                >
                  <span className="text-base shrink-0">{sq.icon}</span>
                  <div className="min-w-0">
                    <p className="text-xs font-medium text-text-accent group-hover:text-text-primary transition truncate">
                      {sq.label}
                    </p>
                    <p className="text-[10px] text-text-secondary/50 truncate">{sq.query}</p>
                  </div>
                  <svg
                    width="14"
                    height="14"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    className="text-text-secondary/30 group-hover:text-text-accent shrink-0 ml-auto transition"
                  >
                    <polyline points="9 18 15 12 9 6" />
                  </svg>
                </button>
              ))}
            </div>
          </div>
        )}

        {chat.messages.map((msg) => (
          <div key={msg.id}>
            {/* Tool calls for this assistant message */}
            {msg.role === "assistant" && msg.toolCalls && msg.toolCalls.length > 0 && (
              <ToolCallChain toolCalls={msg.toolCalls} />
            )}
            <ChatMessage message={msg} />
          </div>
        ))}

        {/* Live tool calls (during loading) */}
        {chat.isLoading && chat.toolCalls.length > 0 && (
          <ToolCallChain toolCalls={chat.toolCalls} />
        )}

        {/* Loading indicator */}
        {chat.isLoading && chat.toolCalls.length === 0 && (
          <div className="flex items-center gap-2 text-text-secondary text-sm pl-10">
            <div className="flex gap-1">
              <span
                className="w-1.5 h-1.5 bg-text-accent/40 rounded-full animate-bounce"
                style={{ animationDelay: "0ms" }}
              />
              <span
                className="w-1.5 h-1.5 bg-text-accent/40 rounded-full animate-bounce"
                style={{ animationDelay: "150ms" }}
              />
              <span
                className="w-1.5 h-1.5 bg-text-accent/40 rounded-full animate-bounce"
                style={{ animationDelay: "300ms" }}
              />
            </div>
            Thinking...
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* "New messages" pill when scrolled up */}
      {!autoScroll && chat.messages.length > 0 && (
        <button
          onClick={() => {
            messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
            setAutoScroll(true);
          }}
          className="absolute bottom-32 left-1/2 -translate-x-1/2 bg-tertiary text-text-accent text-xs px-3 py-1.5 rounded-full glow-border hover:bg-white/10 transition z-10 shadow-lg"
        >
          New messages
        </button>
      )}

      {/* Token bar + Input */}
      <div className="border-t border-white/5 bg-secondary">
        <TokenUsageBar
          tokenUsage={chat.tokenUsage}
          onCompact={chat.triggerCompaction}
          isCompacting={chat.isCompacting}
        />
        <ChatInput
          onSend={handleSend}
          isLoading={chat.isLoading}
          threadId={chat.threadId}
          dispatch={chat.dispatch}
        />
      </div>
    </div>
  );
}

function ToolCallChain({ toolCalls }) {
  const [collapsed, setCollapsed] = useState(false);

  if (collapsed) {
    const totalMs = toolCalls.reduce((s, tc) => s + (tc.elapsed_ms || 0), 0);
    return (
      <button
        onClick={() => setCollapsed(false)}
        className="text-xs text-text-secondary hover:text-text-primary transition pl-10 py-1"
      >
        {toolCalls.length} tool call{toolCalls.length > 1 ? "s" : ""} ({Math.round(totalMs)}ms
        total) - Expand
      </button>
    );
  }

  return (
    <div className="pl-10 space-y-0">
      {toolCalls.length > 1 && (
        <button
          onClick={() => setCollapsed(true)}
          className="text-[10px] text-text-secondary/60 hover:text-text-secondary transition mb-1"
        >
          Collapse tools
        </button>
      )}
      {toolCalls.map((tc, i) => (
        <div key={tc.id}>
          <ToolCallBubble toolCall={tc} />
          {i < toolCalls.length - 1 && <div className="ml-4 h-3 connector-line" />}
        </div>
      ))}
      <div className="ml-4 h-3 connector-line" />
    </div>
  );
}
