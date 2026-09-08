import { useState } from "react";
import { Plus, Database, Info } from "lucide-react";
import IdentitySelector from "./IdentitySelector";
import AboutModal from "./AboutModal";

export default function Header({
  connected, threadId, onNewThread,
  identities, identityId, onIdentityChange,
}) {
  const [aboutOpen, setAboutOpen] = useState(false);

  return (
    <>
      <header className="border-b border-white/5 bg-bg-panel px-4 py-2.5 flex items-center justify-between gap-3 flex-wrap">
        <div className="flex items-center gap-2">
          <Database size={18} className="text-accent-oracle" />
          <h1 className="text-sm font-semibold tracking-wide">
            Enterprise Data Agent
          </h1>
          <span className="text-xs text-text-secondary ml-2">on Oracle AI Database 26ai</span>
          <button
            onClick={() => setAboutOpen(true)}
            className="ml-1 flex items-center gap-1 text-[10px] px-1.5 py-0.5 rounded border border-white/5 text-text-muted hover:text-text-primary hover:border-accent-skill/40"
            title="What is this app?"
          >
            <Info size={10} className="text-accent-skill" />
            About
          </button>
        </div>
        <div className="flex items-center gap-3 flex-wrap">
          <IdentitySelector
            identities={identities}
            identityId={identityId}
            onChange={onIdentityChange}
          />
          <span className="text-xs text-text-muted font-mono">thread: {threadId}</span>
          <span className={`text-xs px-2 py-0.5 rounded ${connected ? "bg-accent-memory/15 text-accent-memory" : "bg-accent-sql/15 text-accent-sql"}`}>
            {connected ? "connected" : "disconnected"}
          </span>
          <button
            onClick={onNewThread}
            className="flex items-center gap-1 text-xs px-2 py-1 rounded bg-white/5 hover:bg-white/10"
          >
            <Plus size={12} /> new thread
          </button>
        </div>
      </header>
      <AboutModal open={aboutOpen} onClose={() => setAboutOpen(false)} />
    </>
  );
}
