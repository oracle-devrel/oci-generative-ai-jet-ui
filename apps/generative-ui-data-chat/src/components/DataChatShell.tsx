"use client";

import { useMemo, useState } from "react";
import { Button, Card, Callout, FollowUpBlock, FollowUpItem, TextArea } from "@openuidev/react-ui";
import { AlertCircle, ArrowRight, Bot, Database, Loader2, Route, Search, Send } from "lucide-react";

import { GenerativeRenderer } from "./GenerativeRenderer";
import { QueryTracePanel } from "./QueryTracePanel";
import type { DataChatApiResponse } from "@/lib/schemas";

const starterPromptGroups = [
  {
    strategy: "SQL",
    label: "Structured metrics",
    icon: Database,
    prompts: [
      "Revenue trend over the last 12 months",
      "Top 5 accounts by region in Q1",
      "Active users this month",
      "Can you analyse the data into a dashboard?"
    ]
  },
  {
    strategy: "Vector",
    label: "Contract evidence",
    icon: Search,
    prompts: [
      "Which contracts mention auto-renewal?",
      "Show renewal evidence from contracts",
      "Find contract snippets about renewal timing"
    ]
  },
  {
    strategy: "Hybrid",
    label: "Metrics + evidence",
    icon: Route,
    prompts: [
      "What's driving the dip in March?",
      "Explain the March revenue dip with evidence",
      "Why did March revenue fall if pipeline stayed healthy?"
    ]
  }
];

const STREAM_IDLE_TIMEOUT_MS = 90000;

type StreamStatus = {
  phase: "model" | "oracle" | "render";
  message: string;
  detail?: string;
};

type ChatTurn =
  | {
      id: string;
      role: "user";
      content: string;
    }
  | {
      id: string;
      role: "assistant";
      content: string;
      response?: DataChatApiResponse;
      error?: string;
      status?: StreamStatus;
    };

const phaseLabel = {
  model: "Thinking",
  oracle: "Querying Oracle",
  render: "Rendering"
} as const;

function createId() {
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function followUpsFor(response: DataChatApiResponse) {
  const title = response.answer.title.toLowerCase();

  if (title.includes("account")) {
    return [
      "Can you analyse the data into a dashboard?",
      "What's driving the dip in March?",
      "Which contracts mention auto-renewal?"
    ];
  }

  if (title.includes("active user")) {
    return [
      "Revenue trend over the last 12 months",
      "Can you analyse the data into a dashboard?",
      "What's driving the dip in March?"
    ];
  }

  if (title.includes("contract") || title.includes("renewal")) {
    return [
      "What's driving the dip in March?",
      "Top 5 accounts by region in Q1",
      "Can you analyse the data into a dashboard?"
    ];
  }

  if (title.includes("march") || title.includes("dip")) {
    return [
      "Revenue trend over the last 12 months",
      "Which contracts mention auto-renewal?",
      "Can you analyse the data into a dashboard?"
    ];
  }

  return [
    "Top 5 accounts by region in Q1",
    "Active users this month",
    "What's driving the dip in March?"
  ];
}

export function DataChatShell() {
  const [message, setMessage] = useState("");
  const [turns, setTurns] = useState<ChatTurn[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const runIndicator = useMemo(() => {
    const latestStreamingTurn = [...turns].reverse().find((turn) => turn.role === "assistant" && turn.status);
    if (isLoading && latestStreamingTurn?.role === "assistant" && latestStreamingTurn.status) {
      return {
        label: `${phaseLabel[latestStreamingTurn.status.phase]} phase`,
        detail: latestStreamingTurn.status.message,
        active: true
      };
    }

    const latestResponse = [...turns].reverse().find((turn) => turn.role === "assistant" && turn.response);
    if (!latestResponse || latestResponse.role !== "assistant" || !latestResponse.response?.queryTrace.length) {
      return {
        label: "Ready",
        detail: "No Oracle calls yet",
        active: false
      };
    }

    const strategies = latestResponse.response.queryTrace.map((trace) => trace.strategy.toUpperCase()).join(" -> ");
    return {
      label: "Last execution",
      detail: `${latestResponse.response.queryTrace.length} Oracle calls · ${strategies}`,
      active: false
    };
  }, [isLoading, turns]);

  async function askDataChat(nextMessage = message) {
    const trimmed = nextMessage.trim();
    if (!trimmed || isLoading) {
      return;
    }

    setMessage("");
    setIsLoading(true);
    const assistantId = createId();
    setTurns((current) => [
      ...current,
      { id: createId(), role: "user", content: trimmed },
      {
        id: assistantId,
        role: "assistant",
        content: "Starting streamed request...",
        status: {
          phase: "model",
          message: "Starting streamed request",
          detail: "Opening a stream so progress can update before the final UI response is ready."
        }
      }
    ]);

    const updateAssistantTurn = (patch: Partial<Extract<ChatTurn, { role: "assistant" }>>) => {
      setTurns((current) =>
        current.map((turn) => (turn.id === assistantId && turn.role === "assistant" ? { ...turn, ...patch } : turn))
      );
    };

    let clearStreamTimeout = () => {};

    try {
      const controller = new AbortController();
      let idleTimeout = window.setTimeout(() => controller.abort(), STREAM_IDLE_TIMEOUT_MS);
      clearStreamTimeout = () => window.clearTimeout(idleTimeout);
      const resetIdleTimeout = () => {
        window.clearTimeout(idleTimeout);
        idleTimeout = window.setTimeout(() => controller.abort(), STREAM_IDLE_TIMEOUT_MS);
      };
      const result = await fetch("/api/chat", {
        method: "POST",
        signal: controller.signal,
        headers: { Accept: "text/event-stream", "Content-Type": "application/json" },
        body: JSON.stringify({ message: trimmed })
      });

      if (!result.ok) {
        window.clearTimeout(idleTimeout);
        const payload = await result.json();
        throw new Error(payload.error ?? "Data chat request failed");
      }

      if (!result.body) {
        window.clearTimeout(idleTimeout);
        throw new Error("Streaming response did not include a body.");
      }

      const reader = result.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let completed = false;

      const handleEventBlock = (block: string) => {
        let event = "message";
        const data: string[] = [];

        for (const line of block.split("\n")) {
          if (line.startsWith("event:")) {
            event = line.slice("event:".length).trim();
          }
          if (line.startsWith("data:")) {
            data.push(line.slice("data:".length).trimStart());
          }
        }

        if (data.length === 0) {
          return;
        }

        const payload = JSON.parse(data.join("\n")) as DataChatApiResponse | StreamStatus | { message?: string; error?: string };

        if (event === "status" && "message" in payload && typeof payload.message === "string") {
          const status = {
            phase: "phase" in payload ? payload.phase : "model",
            message: payload.message,
            detail: "detail" in payload ? payload.detail : undefined
          } as StreamStatus;
          updateAssistantTurn({ content: status.message, status });
          resetIdleTimeout();
          return;
        }

        if (event === "complete" && "answer" in payload) {
          completed = true;
          updateAssistantTurn({
            content: payload.answer.summary,
            response: payload,
            status: undefined
          });
          resetIdleTimeout();
          return;
        }

        if (event === "error" && "error" in payload) {
          throw new Error(typeof payload.error === "string" ? payload.error : "Data chat request failed");
        }
      };

      while (true) {
        const { done, value } = await reader.read();
        if (done) {
          break;
        }

        buffer += decoder.decode(value, { stream: true });
        resetIdleTimeout();
        const blocks = buffer.split("\n\n");
        buffer = blocks.pop() ?? "";
        for (const block of blocks) {
          handleEventBlock(block);
        }
      }

      window.clearTimeout(idleTimeout);

      if (buffer.trim()) {
        handleEventBlock(buffer);
      }

      if (!completed) {
        throw new Error("Streaming response ended before the final answer arrived.");
      }
    } catch (caught) {
      const message =
        caught instanceof DOMException && caught.name === "AbortError"
          ? "The stream stopped sending progress for 90 seconds. Check the LLM endpoint, proxy, or Oracle connection and try again."
          : caught instanceof Error
            ? caught.message
            : "Data chat request failed";
      clearStreamTimeout();
      updateAssistantTurn({
        content: "I could not complete that request.",
        error: message,
        status: undefined
      });
    } finally {
      clearStreamTimeout();
      setIsLoading(false);
    }
  }

  return (
    <main className="chat-page">
      <header className="chat-header">
        <div className="flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-md bg-signal text-white">
            <Bot className="h-5 w-5" aria-hidden />
          </div>
          <div>
            <p className="text-xs font-semibold uppercase text-signal">Oracle AI Database 26ai</p>
            <h1 className="text-2xl font-semibold text-ink">Generative UI Data Chat</h1>
            <p className={`header-run-status ${runIndicator.active ? "header-run-status-active" : ""}`}>
              <span>{runIndicator.label}</span>
              <span aria-hidden>·</span>
              <span>{runIndicator.detail}</span>
            </p>
          </div>
        </div>
      </header>

      <section className="chat-transcript" aria-live="polite">
        {turns.length === 0 ? (
          <section className="welcome-panel">
            <div className="welcome-copy">
              {/* <span className="generated-label sample-prompt-label">Sample prompts</span> */}
              <h2>Ask a business question. Get the interface back.</h2>
              <p>Examples are grouped by the Oracle retrieval path they demonstrate.</p>
            </div>
            <div className="starter-groups">
              {starterPromptGroups.map((group) => (
                <section key={group.strategy} className="starter-group">
                  <div className="starter-group-header">
                    <div className="starter-group-icon">
                      <group.icon className="h-4 w-4" aria-hidden />
                    </div>
                    <div>
                      <h3>{group.strategy}</h3>
                      <p>{group.label}</p>
                    </div>
                  </div>
                  <div className="starter-prompt-list">
                    {group.prompts.map((prompt) => (
                      <button key={prompt} type="button" onClick={() => void askDataChat(prompt)} className="starter-prompt">
                        <span>{prompt}</span>
                        <ArrowRight className="h-4 w-4" aria-hidden />
                      </button>
                    ))}
                  </div>
                </section>
              ))}
            </div>
          </section>
        ) : (
          <div className="space-y-6">
            {turns.map((turn) =>
              turn.role === "user" ? (
                <div key={turn.id} className="flex justify-end">
                  <div className="max-w-3xl rounded-md bg-ink px-4 py-3 text-base leading-7 text-white shadow-sm">
                    {turn.content}
                  </div>
                </div>
              ) : (
                <div key={turn.id} className="assistant-turn">
                  {turn.error ? (
                    <Callout
                      variant="danger"
                      title={
                        <span className="inline-flex items-center gap-2">
                          <AlertCircle className="h-4 w-4" aria-hidden />
                          Data chat request failed
                        </span>
                      }
                      description={turn.error}
                    />
                  ) : turn.response ? (
                    <div className="space-y-5">
                      <GenerativeRenderer response={turn.response.answer} />
                      <Card variant="card" width="full" className="response-followups border border-ink/10 bg-white px-5 py-3 shadow-sm">
                        <FollowUpBlock>
                          {followUpsFor(turn.response).map((followUp) => (
                            <FollowUpItem
                              key={followUp}
                              type="button"
                              text={followUp}
                              icon={<ArrowRight className="h-4 w-4" aria-hidden />}
                              disabled={isLoading}
                              onClick={() => void askDataChat(followUp)}
                            />
                          ))}
                        </FollowUpBlock>
                      </Card>
                      <QueryTracePanel traces={turn.response.queryTrace} />
                    </div>
                  ) : (
                    <Card variant="card" width="full" className="border border-ink/10 bg-white p-5 shadow-sm">
                      <div className="flex items-start gap-3 text-ink/70">
                        <Loader2 className="mt-1 h-5 w-5 animate-spin text-signal" aria-hidden />
                        <div>
                          {turn.status ? <span className={`stream-phase-label stream-phase-${turn.status.phase}`}>{phaseLabel[turn.status.phase]}</span> : null}
                          <p className="mt-2 text-base font-medium text-ink">{turn.status?.message ?? turn.content}</p>
                          {turn.status?.detail ? <p className="mt-1 text-sm leading-6 text-ink/60">{turn.status.detail}</p> : null}
                        </div>
                      </div>
                    </Card>
                  )}
                </div>
              )
            )}
          </div>
        )}
      </section>

      <Card variant="card" width="full" className="chat-composer border border-ink/10 bg-white/95 p-4 shadow-sm">
        <form
          className="flex flex-col gap-3 lg:flex-row lg:items-end"
          onSubmit={(event) => {
            event.preventDefault();
            void askDataChat();
          }}
        >
          <label htmlFor="message" className="sr-only">
            Ask a data question
          </label>
          <TextArea
            id="message"
            value={message}
            onChange={(event) => setMessage(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                void askDataChat();
              }
            }}
            rows={2}
            placeholder="Ask about revenue, accounts, users, contracts, or the March dip..."
            className="min-h-16 flex-1 resize-none text-base"
          />
          <Button
            type="submit"
            disabled={isLoading || !message.trim()}
            variant="primary"
            size="large"
            iconLeft={isLoading ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : <Send className="h-4 w-4" aria-hidden />}
            className="justify-center lg:w-44"
          >
            Send
          </Button>
        </form>
      </Card>
    </main>
  );
}
