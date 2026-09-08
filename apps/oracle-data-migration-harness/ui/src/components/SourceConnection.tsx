import { useEffect, useState } from "react";
import {
  connectSource,
  disconnectSource,
  fetchSource,
  testSource,
  type SourceInfo,
} from "../api/source";

export function SourceConnection({ onChange }: { onChange?: () => void }) {
  const [source, setSource] = useState<SourceInfo | null>(null);
  const [open, setOpen] = useState(false);

  async function refresh() {
    const next = await fetchSource().catch(() => null);
    setSource(next);
    onChange?.();
  }

  useEffect(() => {
    refresh();
  }, []);

  async function disconnect() {
    await disconnectSource();
    await refresh();
  }

  if (!source) return null;

  const connected = source.status === "connected";

  return (
    <>
      <div className="mb-3 rounded-lg border border-oracle-ink/10 bg-white/70 p-3">
        <div className="mb-1 flex items-center justify-between gap-2">
          <span className="text-[10px] font-semibold uppercase tracking-wide text-oracle-ink/50">
            Source
          </span>
          <span
            className={`rounded-full px-2 py-0.5 text-[10px] ${connected ? "bg-green-100 text-green-700" : "bg-yellow-100 text-yellow-800"}`}
          >
            ● {source.status}
          </span>
        </div>
        <div className="truncate font-mono text-[11px] text-oracle-ink/75" title={source.uri}>
          {source.uri}
        </div>
        <div className="mt-1 text-[11px] text-oracle-ink/55">
          Database: {source.database} · Collection: {source.collection}
        </div>
        {typeof source.document_count === "number" && (
          <div className="mt-1 text-[11px] text-oracle-ink/55">
            {source.document_count.toLocaleString()} documents
          </div>
        )}
        {source.error && <div className="mt-1 text-[11px] text-oracle-red">{source.error}</div>}
        <div className="mt-2 flex gap-2">
          <button
            onClick={() => setOpen(true)}
            className="rounded-full border border-oracle-ink/15 px-2.5 py-1 text-[10px] hover:border-oracle-red hover:text-oracle-red"
          >
            {connected ? "Change source" : "Connect source"}
          </button>
          {connected && (
            <button
              onClick={disconnect}
              className="rounded-full border border-oracle-ink/15 px-2.5 py-1 text-[10px] text-oracle-ink/60 hover:border-oracle-red hover:text-oracle-red"
            >
              Disconnect
            </button>
          )}
        </div>
      </div>
      {open && <SourceModal source={source} onClose={() => setOpen(false)} onConnected={refresh} />}
    </>
  );
}

function SourceModal({
  source,
  onClose,
  onConnected,
}: {
  source: SourceInfo;
  onClose: () => void;
  onConnected: () => void;
}) {
  const [uri, setUri] = useState(source.uri);
  const [database, setDatabase] = useState(source.database);
  const [collection, setCollection] = useState(source.collection);
  const [result, setResult] = useState<any>(null);
  const [busy, setBusy] = useState(false);

  async function test() {
    setBusy(true);
    setResult(await testSource({ uri, database, collection }));
    setBusy(false);
  }

  async function connect() {
    setBusy(true);
    const r = await connectSource({ uri, database, collection });
    setResult(r);
    setBusy(false);
    if (r.ok) {
      await onConnected();
      onClose();
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/25"
      onClick={onClose}
    >
      <div
        className="w-[34rem] max-w-[92vw] rounded-xl bg-oracle-cream p-5 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-4 flex items-start justify-between gap-4">
          <div>
            <h2 className="text-lg font-semibold">MongoDB source</h2>
            <p className="text-xs text-oracle-ink/60">
              Connect a MongoDB URI, database, and collection for assessment and migration.
            </p>
          </div>
          <button onClick={onClose} className="text-sm opacity-60 hover:opacity-100">
            Close
          </button>
        </div>
        <label className="mb-3 block text-xs font-semibold uppercase tracking-wide text-oracle-ink/50">
          Connection string
        </label>
        <input
          value={uri}
          onChange={(e) => setUri(e.target.value)}
          className="mb-3 w-full rounded-md border border-oracle-ink/15 bg-white px-3 py-2 font-mono text-xs"
        />
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-oracle-ink/50">
              Database
            </label>
            <input
              value={database}
              onChange={(e) => setDatabase(e.target.value)}
              className="w-full rounded-md border border-oracle-ink/15 bg-white px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-oracle-ink/50">
              Collection
            </label>
            <input
              value={collection}
              onChange={(e) => setCollection(e.target.value)}
              className="w-full rounded-md border border-oracle-ink/15 bg-white px-3 py-2 text-sm"
            />
          </div>
        </div>
        {result && (
          <div
            className={`mt-3 rounded-lg border p-3 text-xs ${result.ok ? "border-green-200 bg-green-50 text-green-800" : "border-red-200 bg-red-50 text-red-800"}`}
          >
            {result.ok
              ? `Connected. ${result.document_count?.toLocaleString?.() ?? result.source?.document_count ?? 0} documents found.`
              : result.error}
          </div>
        )}
        <div className="mt-4 flex justify-end gap-2">
          <button
            onClick={test}
            disabled={busy}
            className="rounded-md border border-oracle-ink/15 px-3 py-2 text-sm disabled:opacity-50"
          >
            Test connection
          </button>
          <button
            onClick={connect}
            disabled={busy}
            className="rounded-md bg-oracle-red px-3 py-2 text-sm font-medium text-white disabled:opacity-50"
          >
            Connect
          </button>
        </div>
      </div>
    </div>
  );
}
