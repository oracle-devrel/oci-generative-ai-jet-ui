import { useEffect, useRef, useState } from "react";
import { ShieldCheck, ChevronDown } from "lucide-react";

const CLEARANCE_BADGE = {
  EXECUTIVE: "bg-accent-tool/20 text-accent-tool",
  STANDARD: "bg-accent-skill/20 text-accent-skill",
};

/**
 * Header dropdown that lets the user pick which persona ("identity") the app
 * should act as. Selecting an identity reshapes both the data explorer (rows
 * filtered by ocean region, columns redacted by clearance) and the agent loop
 * (the system prompt is told who's asking, so denials read as DDS-style
 * authorization, not random empty results).
 */
export default function IdentitySelector({ identities, identityId, onChange }) {
  const [open, setOpen] = useState(false);
  const wrapRef = useRef(null);

  useEffect(() => {
    if (!open) return;
    const onDoc = (e) => {
      if (!wrapRef.current?.contains(e.target)) setOpen(false);
    };
    const onKey = (e) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", onDoc);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDoc);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  const current = identities.find((i) => i.id === identityId) || identities[0];

  return (
    <div ref={wrapRef} className="relative">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-1.5 text-xs px-2 py-1 rounded border border-white/10 bg-white/[0.03] hover:bg-white/[0.07] hover:border-accent-oracle/40"
        title="Switch the active identity (persona). Affects data explorer + agent."
      >
        <ShieldCheck size={12} className="text-accent-oracle" />
        <span className="text-text-muted">use as:</span>
        <span className="font-mono text-text-primary">{current?.label || "—"}</span>
        <ChevronDown size={11} className="text-text-muted" />
      </button>

      {open && (
        <div className="absolute right-0 mt-1 w-[360px] z-50 bg-bg-elev border border-white/10 rounded shadow-2xl">
          <div className="px-3 py-2 border-b border-white/5 text-[10px] uppercase tracking-wider text-text-muted">
            Acting identity
          </div>
          <ul>
            {identities.map((id) => {
              const isActive = id.id === identityId;
              const clearanceCls =
                CLEARANCE_BADGE[id.clearance] || "bg-text-secondary/20 text-text-secondary";
              return (
                <li
                  key={id.id}
                  className={`px-3 py-2 cursor-pointer border-b border-white/[0.03] last:border-0 ${
                    isActive ? "bg-white/[0.05]" : "hover:bg-white/[0.03]"
                  }`}
                  onClick={() => {
                    onChange(id.id);
                    setOpen(false);
                  }}
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-mono text-xs text-text-primary">{id.label}</span>
                    <span className={`text-[9px] px-1.5 py-0.5 rounded font-mono ${clearanceCls}`}>
                      {id.clearance}
                    </span>
                  </div>
                  <div className="text-[10px] text-text-muted mt-0.5 leading-snug">
                    {id.description}
                  </div>
                  <div className="flex flex-wrap gap-1 mt-1">
                    {id.regions ? (
                      id.regions.map((r) => (
                        <span
                          key={r}
                          className="text-[9px] px-1 py-0.5 rounded bg-accent-skill/15 text-accent-skill font-mono"
                        >
                          {r}
                        </span>
                      ))
                    ) : (
                      <span className="text-[9px] px-1 py-0.5 rounded bg-accent-memory/15 text-accent-memory font-mono">
                        all regions
                      </span>
                    )}
                    {(id.mask_cols || []).map((c) => (
                      <span
                        key={c}
                        className="text-[9px] px-1 py-0.5 rounded bg-accent-sql/15 text-accent-sql font-mono"
                        title={`Column masked: ${c}`}
                      >
                        mask: {c.split(".").pop()}
                      </span>
                    ))}
                    {(id.forbid_tables || []).map((t) => (
                      <span
                        key={t}
                        className="text-[9px] px-1 py-0.5 rounded bg-accent-sql/15 text-accent-sql font-mono"
                        title={`Forbidden: ${t}`}
                      >
                        deny: {t.split(".").pop()}
                      </span>
                    ))}
                  </div>
                </li>
              );
            })}
          </ul>
        </div>
      )}
    </div>
  );
}
