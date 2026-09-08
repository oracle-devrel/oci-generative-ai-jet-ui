import { useCallback, useEffect, useRef, useState } from "react";
import type {
  AgentName,
  AgentTrace,
  ArchitectureGraph,
  ChatTurn,
  HealthInfo,
  ServerEvent,
  TableInfo,
  TableRowsResponse,
} from "./types";

const AGENTS: AgentName[] = ["supervisor", "demand_analyst", "policy_agent"];

/** Maps an agent's tool call to a node-id we should "pulse" in the architecture view. */
function targetNodeFor(agent: string | null, tool: string | null): string | null {
  if (!agent || !tool) return null;
  if (agent === "demand_analyst" && tool === "search_demand_reports") return "oracle_vs";
  if (agent === "policy_agent" && tool === "get_planner_policy") return "oracle_vs";
  if (agent === "policy_agent" && tool === "get_user_memory") return "agent_store";
  return null;
}

/** Maps (agent, tool) → edge-id between agent and the store it's reading. */
function edgeIdFor(agent: string | null, tool: string | null): string | null {
  if (!agent || !tool) return null;
  if (agent === "demand_analyst" && tool === "search_demand_reports") return "da-vs";
  if (agent === "policy_agent" && tool === "get_planner_policy") return "pa-vs";
  if (agent === "policy_agent" && tool === "get_user_memory") return "pa-store";
  return null;
}

/** Maps an agent name → the handoff edge from the supervisor. */
function handoffEdge(agent: string): string | null {
  if (agent === "demand_analyst") return "sup-da";
  if (agent === "policy_agent") return "sup-pa";
  return null;
}

/** Maps an agent's tool call to the data-explorer table it touched (for the pulse animation). */
export function tableTouchedBy(agent: string | null, tool: string | null): string | null {
  if (!agent || !tool) return null;
  if (tool === "search_demand_reports") return "SUPPLYCHAIN_DEMAND";
  if (tool === "get_planner_policy") return "SUPPLYCHAIN_DEMAND";
  if (tool === "get_user_memory") return "STORE_VECTORS_AGENT_MEMORY";
  return null;
}

interface UseAgentSocket {
  threadId: string | null;
  connected: boolean;
  isThinking: boolean;
  chat: ChatTurn[];
  agents: Record<AgentName, AgentTrace>;
  edgeActivity: Record<string, number>;
  nodeActivity: Record<string, number>;
  tableActivity: Record<string, number>;
  send: (text: string) => void;
}

const emptyAgents = (): Record<AgentName, AgentTrace> => ({
  supervisor: { agent: "supervisor", tokens: "", toolCalls: [] },
  demand_analyst: { agent: "demand_analyst", tokens: "", toolCalls: [] },
  policy_agent: { agent: "policy_agent", tokens: "", toolCalls: [] },
});

export function useAgentSocket(wsUrl: string): UseAgentSocket {
  const [threadId, setThreadId] = useState<string | null>(null);
  const [connected, setConnected] = useState(false);
  const [isThinking, setIsThinking] = useState(false);
  const [chat, setChat] = useState<ChatTurn[]>([]);
  const [agents, setAgents] = useState<Record<AgentName, AgentTrace>>(emptyAgents());
  const [edgeActivity, setEdgeActivity] = useState<Record<string, number>>({});
  const [nodeActivity, setNodeActivity] = useState<Record<string, number>>({});
  const [tableActivity, setTableActivity] = useState<Record<string, number>>({});
  const wsRef = useRef<WebSocket | null>(null);
  const assistantIdRef = useRef<string | null>(null);

  useEffect(() => {
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;
    ws.onopen = () => setConnected(true);
    ws.onclose = () => {
      setConnected(false);
      setIsThinking(false);
    };
    ws.onerror = () => setConnected(false);
    ws.onmessage = (msg) => {
      let evt: ServerEvent;
      try {
        evt = JSON.parse(msg.data);
      } catch {
        return;
      }
      handleEvent(evt);
    };
    return () => {
      ws.close();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [wsUrl]);

  const touchNode = useCallback(
    (id: string) => setNodeActivity((p) => ({ ...p, [id]: Date.now() })),
    []
  );
  const touchEdge = useCallback(
    (id: string) => setEdgeActivity((p) => ({ ...p, [id]: Date.now() })),
    []
  );
  const touchTable = useCallback(
    (id: string) => setTableActivity((p) => ({ ...p, [id]: Date.now() })),
    []
  );

  const handleEvent = useCallback(
    (evt: ServerEvent) => {
      switch (evt.type) {
        case "session":
          setThreadId(evt.thread_id);
          return;
        case "user_message": {
          const uid = "u-" + Math.random().toString(36).slice(2, 8);
          setChat((p) => [...p, { id: uid, role: "user", content: evt.content }]);
          const aid = "a-" + Math.random().toString(36).slice(2, 8);
          assistantIdRef.current = aid;
          setChat((p) => [...p, { id: aid, role: "assistant", content: "", pending: true }]);
          setAgents(emptyAgents());
          setEdgeActivity({});
          setNodeActivity({});
          setIsThinking(true);
          touchNode("user");
          touchEdge("user-sup");
          return;
        }
        case "agent_started":
          setAgents((p) => ({ ...p, [evt.agent]: { ...p[evt.agent], started: Date.now() } }));
          touchNode(evt.agent);
          const eid = handoffEdge(evt.agent);
          if (eid) touchEdge(eid);
          return;
        case "agent_finished":
          setAgents((p) => ({
            ...p,
            [evt.agent]: { ...p[evt.agent], finished: Date.now(), summary: evt.summary },
          }));
          return;
        case "tool_started": {
          if (!evt.agent || !AGENTS.includes(evt.agent as AgentName)) return;
          const a = evt.agent as AgentName;
          setAgents((p) => ({
            ...p,
            [a]: {
              ...p[a],
              toolCalls: [
                ...p[a].toolCalls,
                {
                  id: `${evt.tool}-${Date.now()}`,
                  tool: evt.tool,
                  args: evt.args || {},
                  startedAt: Date.now(),
                },
              ],
            },
          }));
          const eId = edgeIdFor(evt.agent, evt.tool);
          if (eId) touchEdge(eId);
          const nId = targetNodeFor(evt.agent, evt.tool);
          if (nId) touchNode(nId);
          const tId = tableTouchedBy(evt.agent, evt.tool);
          if (tId) touchTable(tId);
          return;
        }
        case "tool_finished": {
          if (!evt.agent || !AGENTS.includes(evt.agent as AgentName)) return;
          const a = evt.agent as AgentName;
          setAgents((p) => {
            const calls = [...p[a].toolCalls];
            for (let i = calls.length - 1; i >= 0; i--) {
              if (calls[i].tool === evt.tool && !calls[i].finishedAt) {
                calls[i] = { ...calls[i], result: evt.result, finishedAt: Date.now() };
                break;
              }
            }
            return { ...p, [a]: { ...p[a], toolCalls: calls } };
          });
          return;
        }
        case "token": {
          const a = evt.agent;
          setAgents((p) => ({ ...p, [a]: { ...p[a], tokens: p[a].tokens + evt.token } }));
          if (a === "supervisor") {
            const aid = assistantIdRef.current;
            if (aid) {
              setChat((p) =>
                p.map((t) => (t.id === aid ? { ...t, content: t.content + evt.token } : t))
              );
            }
          }
          return;
        }
        case "final_answer": {
          const aid = assistantIdRef.current;
          if (aid) {
            setChat((p) =>
              p.map((t) =>
                t.id === aid ? { ...t, content: evt.content || t.content, pending: false } : t
              )
            );
          }
          assistantIdRef.current = null;
          setIsThinking(false);
          return;
        }
        case "stream_end":
        case "pong":
          return;
        case "error":
          setIsThinking(false);
          setChat((p) => [
            ...p,
            { id: "e-" + Date.now(), role: "assistant", content: `⚠ ${evt.message}` },
          ]);
          return;
      }
    },
    [touchEdge, touchNode, touchTable]
  );

  const send = useCallback(
    (text: string) => {
      const ws = wsRef.current;
      if (!ws || ws.readyState !== ws.OPEN) return;
      ws.send(JSON.stringify({ type: "user_message", content: text, thread_id: threadId }));
    },
    [threadId]
  );

  return {
    threadId,
    connected,
    isThinking,
    chat,
    agents,
    edgeActivity,
    nodeActivity,
    tableActivity,
    send,
  };
}

// ─── REST fetchers ────────────────────────────────────────────────────────
export async function fetchArchitecture(): Promise<ArchitectureGraph> {
  const r = await fetch("/api/agents");
  if (!r.ok) throw new Error(`/api/agents failed: ${r.status}`);
  return r.json();
}

export async function fetchHealth(): Promise<HealthInfo> {
  const r = await fetch("/api/health");
  if (!r.ok) throw new Error(`/api/health failed: ${r.status}`);
  return r.json();
}

export async function fetchTables(): Promise<TableInfo[]> {
  const r = await fetch("/api/tables");
  if (!r.ok) throw new Error(`/api/tables failed: ${r.status}`);
  const j = await r.json();
  return j.tables;
}

export async function fetchTableRows(
  name: string,
  opts: { limit?: number; search?: string } = {}
): Promise<TableRowsResponse> {
  const params = new URLSearchParams();
  if (opts.limit) params.set("limit", String(opts.limit));
  if (opts.search) params.set("search", opts.search);
  const qs = params.toString();
  const url = `/api/tables/${encodeURIComponent(name)}/rows${qs ? `?${qs}` : ""}`;
  const r = await fetch(url);
  if (!r.ok) throw new Error(`${url} failed: ${r.status}`);
  return r.json();
}
