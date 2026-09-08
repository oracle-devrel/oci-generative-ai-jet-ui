import { useEffect } from "react";
import { X, Database, Cpu, Shield, Globe2 } from "lucide-react";

/**
 * About modal — explains the application to a first-time visitor.
 *
 * Triggered from the Header's "About" button. Dismissable via the close icon,
 * the backdrop, or the Escape key.
 */
export default function AboutModal({ open, onClose }) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center bg-black/70 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="w-[min(720px,92vw)] max-h-[88vh] overflow-y-auto bg-bg-elev border border-white/10 rounded-lg shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-start justify-between px-5 py-4 border-b border-white/5 sticky top-0 bg-bg-elev z-10">
          <div className="flex items-center gap-2">
            <Database size={20} className="text-accent-oracle" />
            <div>
              <h2 className="text-sm font-semibold tracking-wide">
                About Enterprise Data Agent
              </h2>
              <p className="text-[11px] text-text-muted">
                A natural-language interface to Oracle AI Database 26ai
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-text-muted hover:text-text-primary p-1 rounded"
            title="close (esc)"
          >
            <X size={16} />
          </button>
        </div>

        {/* Body */}
        <div className="px-5 py-4 space-y-4 text-[13px] leading-relaxed text-text-accent">
          <p>
            This application is the runnable mirror of the{" "}
            <code className="px-1 py-0.5 rounded bg-white/5 text-accent-skill">
              enterprise_data_agent.ipynb
            </code>{" "}
            notebook. The notebook walks through how to build an agent harness
            from Oracle primitives; this app lets you exercise it in a browser
            against a live database.
          </p>

          <section>
            <div className="flex items-center gap-2 text-text-primary font-semibold mb-1">
              <Cpu size={14} className="text-accent-memory" /> What's running
            </div>
            <ul className="list-disc pl-5 space-y-1">
              <li>
                A Flask + Socket.IO backend wrapping the §11 agent loop —
                tool retrieval, OAMP memory, MLE-sandboxed JS, the full skillbox.
              </li>
              <li>
                Oracle AI Database 26ai with{" "}
                <code className="text-accent-vector">VECTOR</code> columns,
                HNSW indexes, in-database ONNX embedder + reranker, JSON
                Relational Duality Views, and a DBFS scratchpad.
              </li>
              <li>
                A React + Vite + Tailwind front-end — chat pane, live tool-call
                trace, right-side memory context, and the data + globe explorers
                below.
              </li>
            </ul>
          </section>

          <section>
            <div className="flex items-center gap-2 text-text-primary font-semibold mb-1">
              <Shield size={14} className="text-accent-tool" /> The "Use As:" selector
            </div>
            <p>
              Top-right of the header. Pick a persona (CFO, regional analyst,
              ops viewer, …) and the app will reshape what you can see — both
              in the Data Explorer (rows filtered by ocean region, columns
              redacted by clearance) and inside the agent loop, where the
              persona is stamped into the system prompt so the model can
              explain authorization-driven empty results. This mirrors the
              Deep Data Security (DDS) pattern in §14.4 of the notebook.
            </p>
          </section>

          <section>
            <div className="flex items-center gap-2 text-text-primary font-semibold mb-1">
              <Database size={14} className="text-accent-oracle" /> Data Explorer
            </div>
            <p>
              Browses the SUPPLYCHAIN demo schema (carriers, vessels, ports,
              voyages, vessel positions, containers, cargo) plus the agent's
              own bookkeeping tables (toolbox, skillbox, schema_acl, …) and the
              DBFS scratchpad. Click a tab, search, scan-into-OAMP — the same
              path the agent uses.
            </p>
          </section>

          <section>
            <div className="flex items-center gap-2 text-text-primary font-semibold mb-1">
              <Globe2 size={14} className="text-accent-skill" /> World Explorer
            </div>
            <p>
              A 3D globe showing every port, vessel, voyage arc, and carrier
              HQ pulled from the same SUPPLYCHAIN tables — sourced from
              SDO_GEOMETRY columns indexed by{" "}
              <code className="text-accent-oracle">MDSYS.SPATIAL_INDEX_V2</code>.
              Use the search box to fly to a port code, vessel name, carrier,
              or HS-coded cargo description. The globe respects the Use As
              identity: pick analyst.east and only Atlantic + Mediterranean
              voyages render.
            </p>
          </section>

          <section className="border-t border-white/5 pt-3 text-xs text-text-muted">
            <p>
              Send a message in the chat pane to start a turn. The agent will
              call <code className="text-text-secondary">search_knowledge</code>,{" "}
              <code className="text-text-secondary">run_sql</code>,{" "}
              <code className="text-text-secondary">exec_js</code>, and the
              skillbox tools as needed; every step shows up live in the trace.
              The right-side Memory Context pane snapshots exactly what entered
              the model's prompt this turn.
            </p>
          </section>
        </div>

        <div className="px-5 py-3 border-t border-white/5 flex items-center justify-between text-[11px] text-text-muted">
          <span>Press ESC or click outside to close</span>
          <button
            onClick={onClose}
            className="px-3 py-1 rounded border border-white/10 hover:bg-white/[0.05]"
          >
            Got it
          </button>
        </div>
      </div>
    </div>
  );
}
