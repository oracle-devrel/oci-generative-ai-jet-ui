import { useState, useRef, useEffect } from "react";
import { ChevronUp, ChevronDown, RefreshCw, Search, Database, Table2, Radar } from "lucide-react";
import { useTables } from "../hooks/useTables";

// Palantir-ish color palette for column types & schema badges
const TYPE_COLORS = {
  NUMBER:    "text-accent-tool",
  VARCHAR2:  "text-text-accent",
  CHAR:      "text-text-accent",
  CLOB:      "text-accent-skill",
  DATE:      "text-accent-memory",
  TIMESTAMP: "text-accent-memory",
  "TIMESTAMP(6)": "text-accent-memory",
  JSON:      "text-accent-skill",
  VECTOR:    "text-accent-vector || text-accent-skill",
  SDO_GEOMETRY: "text-accent-oracle",
  RAW:       "text-text-secondary",
  BLOB:      "text-text-secondary",
};

const STATUS_PILL_COLORS = {
  ACTIVE:        "bg-accent-memory/20 text-accent-memory",
  DELAYED:       "bg-accent-tool/20 text-accent-tool",
  COMPLETED:     "bg-text-secondary/20 text-text-secondary",
  SCHEDULED:     "bg-accent-skill/20 text-accent-skill",
  CANCELLED:     "bg-accent-sql/20 text-accent-sql",
  IN_TRANSIT:    "bg-accent-skill/20 text-accent-skill",
  LOADED:        "bg-accent-memory/20 text-accent-memory",
  DISCHARGED:    "bg-text-secondary/20 text-text-secondary",
  CUSTOMS_HOLD:  "bg-accent-sql/20 text-accent-sql",
  PACIFIC:       "bg-accent-skill/20 text-accent-skill",
  ATLANTIC:      "bg-accent-memory/20 text-accent-memory",
  INDIAN:        "bg-accent-tool/20 text-accent-tool",
  MEDITERRANEAN: "bg-accent-oracle/20 text-accent-oracle",
};

function Pill({ value }) {
  const cls = STATUS_PILL_COLORS[value];
  if (!cls) return <span className="font-mono text-text-accent">{value}</span>;
  return (
    <span className={`inline-block px-1.5 py-0.5 rounded text-[10px] font-mono ${cls}`}>
      {value}
    </span>
  );
}

function renderCell(value, colName, colType) {
  if (value === null || value === undefined) {
    return <span className="text-text-muted/50 italic">null</span>;
  }
  if (value === "[REDACTED]") {
    return (
      <span className="font-mono text-[10px] px-1.5 py-0.5 rounded bg-accent-sql/15 text-accent-sql"
            title="masked by current identity's column policy">
        [REDACTED]
      </span>
    );
  }
  // Status / region columns get pills
  if (
    typeof value === "string" &&
    (colName.endsWith("STATUS") || colName.endsWith("REGION") ||
     colName.endsWith("TYPE") || colName === "OCEAN_REGION" || colName === "CONTAINER_TYPE" ||
     colName === "VESSEL_TYPE")
  ) {
    return <Pill value={value} />;
  }
  // POINT(lon, lat)
  if (typeof value === "string" && value.startsWith("POINT(")) {
    return <span className="font-mono text-accent-oracle">{value}</span>;
  }
  // Numbers right-aligned
  if (typeof value === "number") {
    return (
      <span className="font-mono text-accent-tool">
        {Number.isInteger(value) ? value : value.toFixed(4)}
      </span>
    );
  }
  // Truncate long strings (CLOB previews)
  if (typeof value === "string" && value.length > 80) {
    return (
      <span title={value} className="text-text-accent">
        {value.slice(0, 80)}…
      </span>
    );
  }
  return <span className="text-text-accent">{String(value)}</span>;
}

export default function DataExplorer({ identityId, touched = {} }) {
  const [open, setOpen] = useState(false);
  const [height, setHeight] = useState(360);
  const resizing = useRef(false);
  const tables = useTables(identityId);

  // Resolve the agent's touched-table map into a {schema.name → action} that
  // the tab renderer can consult. Wildcard entries like 'SUPPLYCHAIN.*' from
  // scan_database fan out to every matching tab.
  const matchTouched = (schema, name) => {
    const exact = touched[`${schema}.${name}`];
    if (exact) return exact;
    const wild = touched[`${schema}.*`];
    if (wild) return wild;
    return null;
  };

  // Drag-to-resize
  const onMouseDown = (e) => {
    resizing.current = true;
    const onMove = (ev) => {
      if (!resizing.current) return;
      const newH = window.innerHeight - ev.clientY - 60; // 60px buffer for header
      setHeight(Math.max(200, Math.min(720, newH)));
    };
    const onUp = () => {
      resizing.current = false;
      document.removeEventListener("mousemove", onMove);
      document.removeEventListener("mouseup", onUp);
    };
    document.addEventListener("mousemove", onMove);
    document.addEventListener("mouseup", onUp);
    e.preventDefault();
  };

  return (
    <section className="border-t border-white/5 bg-bg-base">
      {/* Toggle bar — always visible */}
      <div className="h-9 flex items-center px-3 gap-3 border-b border-white/5 bg-bg-panel">
        <button
          onClick={() => setOpen(!open)}
          className="flex items-center gap-1.5 text-xs text-text-secondary hover:text-text-primary"
        >
          {open ? <ChevronDown size={12} /> : <ChevronUp size={12} />}
          <Database size={12} className="text-accent-oracle" />
          <span className="uppercase tracking-wider">Data Explorer</span>
        </button>
        <span className="text-[10px] text-text-muted">
          {tables.tables.length} tables · {tables.active ? `${tables.active.schema}.${tables.active.name}` : "—"}
        </span>
        {open && (
          <>
            {/* Scan summary feedback (right-aligns with the buttons) */}
            {tables.scanState.status === "running" && (
              <span className="ml-auto text-[10px] text-text-muted italic">scanning...</span>
            )}
            {tables.scanState.status === "done" && tables.scanState.summary && (
              <span className="ml-auto text-[10px] font-mono text-accent-memory">
                scanned {tables.scanState.summary.owner}: +{tables.scanState.summary.new} new ·
                ~{tables.scanState.summary.updated} updated · {tables.scanState.summary.skipped} skipped
              </span>
            )}
            {tables.scanState.status === "error" && (
              <span className="ml-auto text-[10px] font-mono text-accent-sql">
                scan error: {String(tables.scanState.error).slice(0, 60)}
              </span>
            )}
            {tables.scanState.status === "idle" && <span className="ml-auto" />}

            {/* Scan button — scans the active tab's schema into OAMP */}
            <button
              onClick={() => tables.scan(tables.active?.schema)}
              disabled={!tables.active || tables.scanState.status === "running"}
              className="flex items-center gap-1 text-[10px] px-2 py-0.5 rounded border border-white/5 text-text-secondary hover:text-text-primary hover:border-accent-memory/40 disabled:opacity-40"
              title={
                tables.active
                  ? `Run the schema scanner against ${tables.active.schema} and write facts to OAMP`
                  : "select a table first"
              }
            >
              <Radar size={11} className="text-accent-memory" />
              <span>scan {tables.active ? tables.active.schema : "—"}</span>
            </button>

            {/* Drag handle to resize from this bar */}
            <button
              onMouseDown={onMouseDown}
              className="text-[10px] text-text-muted hover:text-text-secondary cursor-ns-resize"
              title="drag to resize"
            >
              ═
            </button>
            <button
              onClick={tables.refresh}
              className="text-text-muted hover:text-text-primary"
              title="refresh"
            >
              <RefreshCw size={12} />
            </button>
          </>
        )}
      </div>

      {open && (
        <div className="flex flex-col" style={{ height }}>
          {/* Table tabs row */}
          <div className="border-b border-white/5 bg-bg-panel/60 overflow-x-auto whitespace-nowrap">
            {tables.tables.map((t) => {
              const isActive = tables.active && t.schema === tables.active.schema && t.name === tables.active.name;
              const forbidden = t.forbidden;
              const touch = matchTouched(t.schema, t.name);
              const pulseClass = touch
                ? touch.action === "scan"
                  ? "data-explorer-pulse-scan"
                  : touch.action === "write"
                    ? "data-explorer-pulse-write"
                    : "data-explorer-pulse-read"
                : "";
              return (
                <button
                  key={`${t.schema}.${t.name}`}
                  onClick={() => tables.setActive(t)}
                  className={`relative inline-flex items-center gap-1.5 px-3 py-1.5 text-[11px] font-mono border-r border-white/5 hover:bg-white/[0.02] ${
                    isActive ? "bg-white/[0.05] text-text-primary" : "text-text-secondary"
                  } ${forbidden ? "opacity-60" : ""} ${pulseClass}`}
                  title={
                    touch
                      ? `agent ${touch.action === "scan" ? "scanning" : touch.action === "write" ? "writing" : "reading"} this table`
                      : forbidden
                        ? "forbidden by current identity"
                        : undefined
                  }
                >
                  <Table2 size={10} className={t.schema === "AGENT" ? "text-accent-memory" : "text-accent-oracle"} />
                  <span className="text-text-muted">{t.schema}.</span>
                  <span>{t.name}</span>
                  <span className="text-[9px] text-text-muted/70">[{t.row_count ?? "?"}]</span>
                  {touch && (
                    <span className={`text-[9px] px-1 rounded font-mono ${
                      touch.action === "scan" ? "bg-accent-memory/30 text-accent-memory" :
                      touch.action === "write" ? "bg-accent-tool/30 text-accent-tool" :
                      "bg-accent-skill/30 text-accent-skill"
                    }`}>
                      {touch.action === "scan" ? "SCAN" : touch.action === "write" ? "WRITE" : "READ"}
                    </span>
                  )}
                  {forbidden && (
                    <span className="text-[9px] px-1 rounded bg-accent-sql/20 text-accent-sql">DENY</span>
                  )}
                </button>
              );
            })}
          </div>

          {/* Search bar */}
          <div className="px-3 py-1.5 border-b border-white/5 bg-bg-panel/40 flex items-center gap-2">
            <Search size={12} className="text-text-muted" />
            <input
              type="text"
              placeholder="filter rows (case-insensitive substring across text columns)..."
              value={tables.search}
              onChange={(e) => tables.submitSearch(e.target.value)}
              className="flex-1 bg-transparent text-[11px] font-mono text-text-primary placeholder:text-text-muted focus:outline-none"
            />
            {tables.loading && <span className="text-[10px] text-text-muted">loading...</span>}
            {tables.data && (
              <span className="text-[10px] text-text-muted">
                {tables.data.returned} / {tables.data.row_count} rows
              </span>
            )}
          </div>

          {/* Data grid */}
          <div className="flex-1 overflow-auto">
            {tables.error && (
              <div className="px-3 py-2 text-xs text-accent-sql font-mono">
                error: {tables.error}
              </div>
            )}
            {!tables.error && tables.data && (
              <table className="text-[11px] font-mono w-full border-collapse">
                <thead className="sticky top-0 bg-bg-panel border-b border-white/5">
                  <tr>
                    {tables.data.columns.map((c) => {
                      const tcls = TYPE_COLORS[c.type] || "text-text-secondary";
                      return (
                        <th
                          key={c.name}
                          className="text-left px-3 py-1.5 font-semibold border-r border-white/5"
                        >
                          <div className="flex items-center gap-1.5">
                            <span className="text-text-primary">{c.name}</span>
                            <span className={`text-[9px] ${tcls}`}>
                              {c.type}{c.type === "VARCHAR2" && c.length ? `(${c.length})` : ""}
                            </span>
                            {c.masked && (
                              <span className="text-[9px] px-1 rounded bg-accent-sql/20 text-accent-sql"
                                title="redacted by current identity's column mask">
                                MASKED
                              </span>
                            )}
                          </div>
                        </th>
                      );
                    })}
                  </tr>
                </thead>
                <tbody>
                  {tables.data.rows.map((row, i) => (
                    <tr
                      key={i}
                      className="border-b border-white/[0.03] hover:bg-white/[0.03] transition-colors"
                    >
                      {row.map((v, j) => {
                        const c = tables.data.columns[j];
                        return (
                          <td
                            key={j}
                            className="px-3 py-1 border-r border-white/[0.03] align-top"
                          >
                            {renderCell(v, c.name, c.type)}
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                  {tables.data.rows.length === 0 && (
                    <tr>
                      <td colSpan={tables.data.columns.length} className="px-3 py-4 text-center text-text-muted italic">
                        no rows match the filter
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            )}
          </div>
        </div>
      )}
    </section>
  );
}
