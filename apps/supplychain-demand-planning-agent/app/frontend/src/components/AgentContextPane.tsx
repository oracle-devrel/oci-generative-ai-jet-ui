import { useState } from "react";
import type { AgentName, AgentTrace } from "../types";

interface Props {
  agents: Record<AgentName, AgentTrace>;
}

const ORDER: AgentName[] = ["supervisor", "policy_agent", "demand_analyst"];

const LABEL: Record<AgentName, string> = {
  supervisor: "Supervisor",
  policy_agent: "policy_agent",
  demand_analyst: "demand_analyst",
};

export function AgentContextPane({ agents }: Props) {
  const [active, setActive] = useState<AgentName>("supervisor");
  const trace = agents[active];

  return (
    <div className="pane context-pane">
      <div className="pane-header">
        <div className="pane-title">Agent context</div>
        <div className="pane-sub">live trace per agent</div>
      </div>

      <div className="agent-tabs">
        {ORDER.map((a) => {
          const calls = agents[a].toolCalls.length;
          const status = agents[a].finished ? "done" : agents[a].started ? "running" : "idle";
          return (
            <button
              key={a}
              className={`agent-tab ${a === active ? "agent-tab-active" : ""} agent-${status}`}
              onClick={() => setActive(a)}
            >
              <div className="agent-tab-label">{LABEL[a]}</div>
              <div className="agent-tab-sub">
                {status} · {calls} tool{calls === 1 ? "" : "s"}
              </div>
            </button>
          );
        })}
      </div>

      <div className="agent-body">
        <Section title="Status">
          <div className="kv">
            <span>started</span>
            <span>{trace.started ? new Date(trace.started).toLocaleTimeString() : "—"}</span>
          </div>
          <div className="kv">
            <span>finished</span>
            <span>{trace.finished ? new Date(trace.finished).toLocaleTimeString() : "—"}</span>
          </div>
        </Section>

        <Section title={`Tool calls (${trace.toolCalls.length})`}>
          {trace.toolCalls.length === 0 && <div className="muted">no tools called yet</div>}
          {trace.toolCalls.map((tc) => (
            <details key={tc.id} className="tool-call">
              <summary>
                <span className={`badge ${tc.finishedAt ? "badge-done" : "badge-running"}`}>
                  {tc.finishedAt ? "done" : "running"}
                </span>
                <code>{tc.tool}</code>
                {Object.keys(tc.args).length > 0 && (
                  <span className="muted">
                    {" "}
                    (
                    {Object.entries(tc.args)
                      .map(([k, v]) => `${k}=${JSON.stringify(v).slice(0, 30)}`)
                      .join(", ")}
                    )
                  </span>
                )}
              </summary>
              {tc.result && <pre className="tool-result">{tc.result.slice(0, 2000)}</pre>}
            </details>
          ))}
        </Section>

        <Section title="Streaming output">
          {trace.tokens ? (
            <pre className="tokens">{trace.tokens}</pre>
          ) : (
            <div className="muted">no tokens streamed yet</div>
          )}
        </Section>

        {trace.summary && (
          <Section title="Final summary">
            <pre className="tokens">{trace.summary}</pre>
          </Section>
        )}
      </div>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="section">
      <div className="section-title">{title}</div>
      <div className="section-body">{children}</div>
    </div>
  );
}
