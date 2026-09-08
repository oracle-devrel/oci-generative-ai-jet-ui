"use client";

import { Card, Tag } from "@openuidev/react-ui";
import { CheckCircle2, Code2, Database, Rows3, Route, Search, Timer } from "lucide-react";

import type { QueryTrace } from "@/lib/schemas";

const strategyVariant = {
  sql: "info",
  vector: "warning",
  hybrid: "success"
} as const;

function strategyTitle(strategy: QueryTrace["strategy"]) {
  if (strategy === "sql") {
    return "Oracle SQL";
  }
  if (strategy === "vector") {
    return "Oracle Vector Search";
  }
  return "Oracle Hybrid Search";
}

function strategyDescription(strategy: QueryTrace["strategy"]) {
  if (strategy === "sql") {
    return "Structured rows from seeded tables";
  }
  if (strategy === "vector") {
    return "Semantic contract evidence";
  }
  return "SQL, Oracle Text, and vector evidence";
}

function StrategyIcon({ strategy }: { strategy: QueryTrace["strategy"] }) {
  if (strategy === "vector") {
    return <Search className="h-4 w-4" aria-hidden />;
  }
  if (strategy === "hybrid") {
    return <Route className="h-4 w-4" aria-hidden />;
  }
  return <Database className="h-4 w-4" aria-hidden />;
}

export function QueryTracePanel({ traces }: { traces: QueryTrace[] }) {
  if (traces.length === 0) {
    return null;
  }

  const totalElapsed = traces.reduce((sum, trace) => sum + (trace.elapsedMs ?? 0), 0);
  const totalRows = traces.reduce((sum, trace) => sum + (trace.rowCount ?? 0), 0);
  const strategies = Array.from(new Set(traces.map((trace) => trace.strategy.toUpperCase()))).join(" + ");

  return (
    <Card variant="card" width="full" className="query-trace-card border border-ink/10 bg-white p-6 text-ink shadow-sm">
      <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
        <div className="flex gap-3">
          <div className="flex h-10 w-10 flex-none items-center justify-center rounded-md bg-signal/10 text-signal">
            <Database className="h-5 w-5" aria-hidden />
          </div>
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <h3 className="text-xl font-semibold text-ink">Oracle execution trace</h3>
              <Tag text="server-owned tools" variant="warning" size="sm" />
            </div>
            <p className="mt-1 max-w-3xl text-sm leading-6 text-ink/60">
              These are the database calls made after model planning. The model chooses the route; Oracle Database returns the rows and evidence.
            </p>
          </div>
        </div>

        <div className="grid min-w-72 grid-cols-3 gap-2">
          <div className="rounded-md border border-ink/10 bg-paper px-3 py-2">
            <p className="text-xs font-medium uppercase text-ink/45">Calls</p>
            <p className="mt-1 text-lg font-semibold text-ink">{traces.length}</p>
          </div>
          <div className="rounded-md border border-ink/10 bg-paper px-3 py-2">
            <p className="text-xs font-medium uppercase text-ink/45">Rows</p>
            <p className="mt-1 text-lg font-semibold text-ink">{totalRows}</p>
          </div>
          <div className="rounded-md border border-ink/10 bg-paper px-3 py-2">
            <p className="text-xs font-medium uppercase text-ink/45">Time</p>
            <p className="mt-1 text-lg font-semibold text-ink">{totalElapsed}ms</p>
          </div>
        </div>
      </div>

      <div className="mt-5 flex flex-wrap items-center gap-2 border-y border-ink/10 py-3 text-sm text-ink/65">
        <Route className="h-4 w-4 text-signal" aria-hidden />
        <span className="font-medium text-ink">Strategy path:</span>
        <span>{strategies}</span>
      </div>

      <div className="mt-5 space-y-3">
        {traces.map((trace, index) => (
          <article key={`${trace.label}-${index}`} className="trace-step">
            <div className="trace-step-number">{index + 1}</div>
            <div className="min-w-0 flex-1">
              <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <Tag text={trace.strategy.toUpperCase()} variant={strategyVariant[trace.strategy]} size="sm" />
                    <span className="inline-flex items-center gap-1.5 text-sm font-semibold text-signal">
                      <StrategyIcon strategy={trace.strategy} />
                      {strategyTitle(trace.strategy)}
                    </span>
                  </div>
                  <h4 className="mt-2 text-base font-semibold text-ink">{trace.label}</h4>
                  <p className="mt-1 text-sm leading-6 text-ink/58">{strategyDescription(trace.strategy)}</p>
                </div>

                <div className="flex flex-wrap gap-2 text-sm text-ink/65">
                  <span className="inline-flex items-center gap-1 rounded-md border border-ink/10 bg-white px-2.5 py-1">
                    <Rows3 className="h-3.5 w-3.5 text-signal" aria-hidden />
                    {trace.rowCount ?? 0} rows
                  </span>
                  <span className="inline-flex items-center gap-1 rounded-md border border-ink/10 bg-white px-2.5 py-1">
                    <Timer className="h-3.5 w-3.5 text-signal" aria-hidden />
                    {trace.elapsedMs ?? 0}ms
                  </span>
                  <span className="inline-flex items-center gap-1 rounded-md border border-ink/10 bg-white px-2.5 py-1">
                    <CheckCircle2 className="h-3.5 w-3.5 text-signal" aria-hidden />
                    completed
                  </span>
                </div>
              </div>

              <details className="trace-statement" open={index === 0}>
                <summary>
                  <Code2 className="h-4 w-4" aria-hidden />
                  Statement
                </summary>
                <pre>
                  <code>{trace.statement}</code>
                </pre>
              </details>
            </div>
          </article>
        ))}
      </div>
    </Card>
  );
}
