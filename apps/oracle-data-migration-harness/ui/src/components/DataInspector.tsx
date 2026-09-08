import { useEffect, useState } from "react";
import { fetchInspect } from "../api/inspect";
import type { Side } from "../types";

export function DataInspector({
  side,
  open,
  onClose,
}: {
  side: Side;
  open: boolean;
  onClose: () => void;
}) {
  const [data, setData] = useState<any>(null);
  const [tab, setTab] = useState("overview");

  useEffect(() => {
    if (!open) return;
    setData(null);
    setTab("overview");
    fetchInspect(side)
      .then(setData)
      .catch((e) => setData({ error: String(e) }));
  }, [side, open]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/20" onClick={onClose}>
      <aside
        className="h-full w-[44rem] max-w-[92vw] overflow-y-auto bg-oracle-cream shadow-2xl border-l border-oracle-ink/10"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="sticky top-0 z-10 flex items-center justify-between border-b border-oracle-ink/10 bg-oracle-cream/95 px-5 py-4 backdrop-blur">
          <div>
            <h2 className="text-lg font-semibold">
              {side === "mongo" ? "MongoDB source data" : "Oracle target data"}
            </h2>
            <p className="text-xs text-oracle-ink/60">
              {side === "mongo"
                ? "Document shape before migration"
                : "Relational, JSON Duality, vectors, and memory after migration"}
            </p>
          </div>
          <button
            onClick={onClose}
            className="rounded-full border border-oracle-ink/15 px-3 py-1 text-sm hover:border-oracle-red hover:text-oracle-red"
          >
            Close
          </button>
        </div>

        <div className="p-5">
          {!data && <p className="text-sm opacity-60">Loading database snapshot...</p>}
          {data?.error && <p className="text-sm text-oracle-red">{data.error}</p>}
          {data && data.migrated === false && (
            <p className="text-sm opacity-70">
              Oracle has not been migrated yet. Click Migrate first.
            </p>
          )}
          {data && data.migrated !== false && !data.error && (
            <>
              <Stats data={data} />
              {side === "mongo" ? (
                <MongoInspect data={data} />
              ) : (
                <OracleInspect data={data} tab={tab} setTab={setTab} />
              )}
            </>
          )}
        </div>
      </aside>
    </div>
  );
}

function Stats({ data }: { data: any }) {
  const stats = data.stats ?? {};
  const items = [
    ["products", stats.products],
    ["reviews", stats.reviews],
    ["vectors", stats.vectors],
    ["memory", stats.memory_messages],
  ];
  if (stats.duality_views !== undefined) items.splice(2, 0, ["duality views", stats.duality_views]);
  return (
    <div className="mb-4 grid grid-cols-2 gap-2 md:grid-cols-4">
      {items.map(([label, value]) => (
        <div
          key={label as string}
          className="rounded-lg border border-oracle-ink/10 bg-white/70 p-3"
        >
          <div className="text-lg font-semibold">{String(value ?? 0)}</div>
          <div className="text-[11px] uppercase tracking-wide text-oracle-ink/50">{label}</div>
        </div>
      ))}
    </div>
  );
}

function MongoInspect({ data }: { data: any }) {
  return (
    <div className="space-y-4">
      <InfoCard title="Source">
        <div className="text-sm font-mono break-all">{data.connection}</div>
        <div className="mt-1 text-xs text-oracle-ink/60">
          Database: {data.database} · Collection: {data.collection}
        </div>
      </InfoCard>
      <InfoCard title="Document Shape">
        <CodeBlock value={data.sample_document} />
      </InfoCard>
      <InfoCard title="What This Shows">
        <p className="text-sm leading-relaxed text-oracle-ink/75">
          The source app sees each product as one document-shaped object. Reviews are nested, and
          the review embedding is attached before migration.
        </p>
      </InfoCard>
    </div>
  );
}

function OracleInspect({
  data,
  tab,
  setTab,
}: {
  data: any;
  tab: string;
  setTab: (t: string) => void;
}) {
  const tabs = ["overview", "tables", "duality", "vectors", "memory", "ddl"];
  const tabLabels: Record<string, string> = {
    overview: "Overview",
    tables: "Relational Tables",
    duality: "JSON Duality View",
    vectors: "Vectors",
    memory: "Memory",
    ddl: "Generated Definitions",
  };
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-2">
        {tabs.map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`rounded-full border px-3 py-1 text-xs ${tab === t ? "border-oracle-red bg-oracle-red text-white" : "border-oracle-ink/15 bg-white/70"}`}
          >
            {tabLabels[t]}
          </button>
        ))}
      </div>

      {tab === "overview" && (
        <InfoCard title="Access Paths Unlocked">
          <p className="text-sm leading-relaxed text-oracle-ink/75">
            The migrated data is now available as relational tables, a JSON Relational Duality
            shape, vector-searchable rows, and restored conversation memory.
          </p>
        </InfoCard>
      )}
      {tab === "tables" && (
        <div className="space-y-4">
          <InfoCard title="Products Relational Table">
            {Array.isArray(data.tables?.products) ? (
              <TablePreview rows={data.tables.products} />
            ) : (
              <CodeBlock value={data.tables?.raw_json ?? []} />
            )}
          </InfoCard>
          <InfoCard title="Reviews Relational Table">
            {Array.isArray(data.tables?.reviews) ? (
              <TablePreview rows={data.tables.reviews} />
            ) : (
              <TablePreview rows={data.tables?.scalar_projection ?? []} />
            )}
          </InfoCard>
        </div>
      )}
      {tab === "duality" && (
        <InfoCard title="JSON Duality Shape">
          <CodeBlock
            value={
              data.duality_sample ??
              data.tables?.raw_json ??
              "Not generated for generic JSON migration."
            }
          />
        </InfoCard>
      )}
      {tab === "vectors" && (
        <InfoCard title="Raw Vector Rows">
          <RawVectorRows rows={data.vector_rows ?? []} />
        </InfoCard>
      )}
      {tab === "memory" && (
        <InfoCard title="Conversation Memory">
          <CodeBlock
            value={{
              migrated_messages: data.stats?.memory_messages,
              store: "agent_chat_memory",
              source: "MongoDB chat_history",
            }}
          />
        </InfoCard>
      )}
      {tab === "ddl" && (
        <div className="space-y-4">
          <InfoCard title="Products Table Definition">
            <CodeBlock value={data.schema?.products_ddl ?? data.schema?.raw_ddl} />
          </InfoCard>
          <InfoCard title="Reviews Table Definition">
            <CodeBlock value={data.schema?.reviews_ddl ?? data.schema?.projection_ddl} />
          </InfoCard>
          <InfoCard title="Duality View Definition">
            <CodeBlock
              value={data.schema?.duality_view ?? "Not generated for generic JSON migration."}
            />
          </InfoCard>
          <InfoCard title="Vector Column Definition">
            <CodeBlock
              value={data.schema?.vector_ddl ?? "No vector column generated for this migration."}
            />
          </InfoCard>
        </div>
      )}
    </div>
  );
}

function InfoCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="rounded-xl border border-oracle-ink/10 bg-white/70 p-4">
      <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-oracle-ink/50">
        {title}
      </h3>
      {children}
    </section>
  );
}

function RawVectorRows({
  rows,
}: {
  rows: { row: number; values?: number[]; truncated?: boolean; error?: string }[];
}) {
  if (!rows || rows.length === 0)
    return <p className="text-sm text-oracle-ink/55">No vector rows to show.</p>;
  return (
    <div className="space-y-2 rounded-lg bg-oracle-ink p-3 font-mono text-[11px] leading-relaxed text-oracle-cream">
      {rows.map((r) => (
        <div key={r.row} className="break-all">
          <span className="text-oracle-cream/60">row {r.row}</span>
          {"  "}
          {r.error ? (
            <span>{r.error}</span>
          ) : (
            <span>
              [{(r.values ?? []).join(", ")}
              {r.truncated ? ", ..." : ""}]
            </span>
          )}
        </div>
      ))}
    </div>
  );
}

function TablePreview({ rows }: { rows: Record<string, any>[] }) {
  if (!rows || rows.length === 0)
    return <p className="text-sm text-oracle-ink/55">No rows to show.</p>;
  const columns = Object.keys(rows[0]);
  return (
    <div className="max-h-80 overflow-auto rounded-lg border border-oracle-ink/10 bg-white">
      <table className="min-w-full border-collapse text-left text-[11px]">
        <thead className="sticky top-0 bg-oracle-cream">
          <tr>
            {columns.map((c) => (
              <th
                key={c}
                className="border-b border-oracle-ink/10 px-2 py-2 font-semibold uppercase tracking-wide text-oracle-ink/55"
              >
                {c.replaceAll("_", " ")}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i} className="odd:bg-white even:bg-oracle-cream/40">
              {columns.map((c) => (
                <td
                  key={c}
                  className="max-w-64 truncate border-b border-oracle-ink/5 px-2 py-2"
                  title={String(row[c] ?? "")}
                >
                  {String(row[c] ?? "")}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function CodeBlock({ value }: { value: any }) {
  const text = typeof value === "string" ? value : JSON.stringify(value, null, 2);
  return (
    <pre className="max-h-96 overflow-auto rounded-lg bg-oracle-ink p-3 text-[11px] leading-relaxed text-oracle-cream">
      <code>{text}</code>
    </pre>
  );
}
