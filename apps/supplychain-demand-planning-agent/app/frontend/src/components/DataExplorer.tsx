import { useCallback, useEffect, useMemo, useState } from "react";
import { Database, RefreshCcw, Search, Table } from "lucide-react";
import { fetchTableRows, fetchTables } from "../useAgentSocket";
import type { TableInfo, TableRowsResponse } from "../types";

interface Props {
  tableActivity: Record<string, number>;
}

const KIND_BADGE: Record<TableInfo["kind"], string> = {
  vector: "bg-accent-memory/15 text-accent-memory",
  store: "bg-accent-skill/15  text-accent-skill",
  cache: "bg-accent-tool/15   text-accent-tool",
  chat: "bg-accent-sql/15    text-accent-sql",
  checkpoint: "bg-overlay-medium   text-text-secondary",
};

const TYPE_COLOR: Record<string, string> = {
  NUMBER: "text-accent-tool",
  CLOB: "text-text-accent",
  BLOB: "text-text-muted",
  VARCHAR2: "text-text-accent",
  CHAR: "text-text-accent",
  DATE: "text-accent-memory",
  TIMESTAMP: "text-accent-memory",
  JSON: "text-accent-skill",
  VECTOR: "text-accent-oracle",
  RAW: "text-text-muted",
};

const ACTIVE_MS = 3500;

export function DataExplorer({ tableActivity }: Props) {
  const [tables, setTables] = useState<TableInfo[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [rows, setRows] = useState<TableRowsResponse | null>(null);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(false);
  const [now, setNow] = useState<number>(Date.now());

  // Tick only while there is recent activity (avoids ReactFlow-style churn).
  useEffect(() => {
    const stamps = Object.values(tableActivity);
    if (stamps.length === 0) return;
    const latest = Math.max(...stamps);
    const remaining = latest + ACTIVE_MS - Date.now();
    if (remaining <= 0) return;
    const id = setTimeout(() => setNow(Date.now()), remaining + 50);
    return () => clearTimeout(id);
  }, [tableActivity]);

  const refreshCatalog = useCallback(async () => {
    try {
      const ts = await fetchTables();
      setTables(ts);
      if (!activeId && ts.length) {
        const first = ts.find((t) => t.exists) || ts[0];
        setActiveId(first.id);
      }
    } catch (e) {
      console.error(e);
    }
  }, [activeId]);

  useEffect(() => {
    refreshCatalog();
  }, [refreshCatalog]);

  // When a tool fires, jump the explorer to the table it touched.
  useEffect(() => {
    const touched = Object.entries(tableActivity).sort((a, b) => b[1] - a[1])[0]?.[0];
    if (touched) setActiveId(touched);
  }, [tableActivity]);

  // Load rows whenever the active table or search changes.
  useEffect(() => {
    if (!activeId) return;
    let cancelled = false;
    setLoading(true);
    fetchTableRows(activeId, { limit: 100, search: search || undefined })
      .then((r) => {
        if (!cancelled) setRows(r);
      })
      .catch(() => {
        if (!cancelled) setRows(null);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [activeId, search]);

  const activeMeta = useMemo(
    () => tables.find((t) => t.id === activeId) || null,
    [tables, activeId]
  );

  return (
    <div className="pane h-full">
      <div className="pane-header">
        <div className="flex items-center gap-2">
          <Database size={13} className="text-accent-oracle" />
          <div className="pane-title">Data explorer</div>
          {activeMeta && (
            <span className="text-[10px] text-text-muted ml-2 font-mono">
              {activeMeta.label}
              {activeMeta.row_count != null && ` · ${activeMeta.row_count.toLocaleString()} rows`}
            </span>
          )}
        </div>
        <button
          onClick={refreshCatalog}
          className="text-text-muted hover:text-text-primary transition-colors"
          title="Refresh table list"
        >
          <RefreshCcw size={12} />
        </button>
      </div>

      {/* Table tabs */}
      <div className="flex overflow-x-auto border-b border-border-subtle bg-bg-panel shrink-0">
        {tables.map((t) => {
          const age = now - (tableActivity[t.id] || 0);
          const active = age < ACTIVE_MS;
          const isSelected = t.id === activeId;
          return (
            <button
              key={t.id}
              onClick={() => setActiveId(t.id)}
              disabled={!t.exists}
              className={`relative shrink-0 px-3 py-2 text-left text-[11px] font-mono border-r border-border-subtle transition-colors ${
                isSelected
                  ? "bg-overlay-medium text-text-primary"
                  : "text-text-secondary hover:bg-overlay-soft"
              } ${!t.exists ? "opacity-40" : ""} ${active ? "animate-pulse-store" : ""}`}
            >
              <div className="flex items-center gap-1.5">
                <Table size={11} className="text-text-muted" />
                <span className="truncate">{t.label}</span>
                <span className={`chip ${KIND_BADGE[t.kind]} text-[9px]`}>{t.kind}</span>
              </div>
              <div className="text-[10px] text-text-muted mt-0.5">
                {t.row_count != null
                  ? `${t.row_count.toLocaleString()} rows`
                  : t.exists
                    ? "—"
                    : "not seeded"}
              </div>
            </button>
          );
        })}
      </div>

      {/* Purpose blurb + search */}
      {activeMeta && (
        <div className="px-3 py-2 border-b border-border-subtle bg-bg-panel flex items-center gap-3 shrink-0">
          <div className="text-[11px] text-text-secondary flex-1 truncate">
            {activeMeta.purpose}
          </div>
          <div className="flex items-center gap-1.5 text-[11px] text-text-muted">
            <Search size={11} />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="filter rows (case-insensitive)"
              className="bg-bg-elev border border-border-subtle rounded px-2 py-1 text-[11px] font-mono w-64 focus:outline-none focus:border-accent-skill text-text-primary placeholder:text-text-muted"
            />
          </div>
        </div>
      )}

      {/* Grid */}
      <div className="flex-1 min-h-0 overflow-auto">
        {loading && <div className="px-3 py-2 text-[11px] text-text-muted">loading…</div>}
        {!loading && rows && rows.rows.length === 0 && (
          <div className="px-3 py-6 text-[11px] text-text-muted">no rows match.</div>
        )}
        {!loading && rows && rows.rows.length > 0 && (
          <table className="w-full text-[11px] font-mono">
            <thead className="sticky top-0 bg-bg-panel z-10">
              <tr className="border-b border-border-subtle">
                {rows.columns.map((c) => (
                  <th
                    key={c.name}
                    className="text-left px-3 py-1.5 font-semibold border-r border-border-subtle whitespace-nowrap"
                  >
                    <span className="text-text-primary">{c.name}</span>
                    <span
                      className={`ml-1.5 text-[9px] ${TYPE_COLOR[c.type] || "text-text-muted"}`}
                    >
                      {c.type}
                    </span>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.rows.map((row, i) => (
                <tr key={i} className="border-b border-border-subtle hover:bg-overlay-soft">
                  {row.map((cell, j) => (
                    <Cell key={j} value={cell} type={rows.columns[j]?.type} />
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

function Cell({ value, type }: { value: unknown; type: string | undefined }) {
  let body: React.ReactNode;
  let cls = "px-3 py-1 border-r border-border-subtle whitespace-nowrap max-w-[28ch] truncate";

  if (value === null || value === undefined) {
    body = <span className="italic text-text-muted">null</span>;
  } else if (typeof value === "number" || (type === "NUMBER" && !isNaN(Number(value)))) {
    cls += " text-right text-accent-tool";
    body = Number(value).toLocaleString(undefined, { maximumFractionDigits: 4 });
  } else if (typeof value === "string" && value.startsWith("<") && value.endsWith(">")) {
    body = <span className="text-text-muted italic">{value}</span>;
  } else {
    const text = String(value);
    body = text.length > 80 ? text.slice(0, 80) + "…" : text;
    if (type === "JSON" || type === "VECTOR") cls += " text-accent-skill";
    else cls += " text-text-accent";
  }

  return (
    <td className={cls} title={value == null ? "null" : String(value)}>
      {body}
    </td>
  );
}
