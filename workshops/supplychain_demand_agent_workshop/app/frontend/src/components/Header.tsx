import { useEffect, useState } from "react";
import { Activity, Database, Moon, Sparkles, Sun } from "lucide-react";
import { fetchHealth } from "../useAgentSocket";
import type { HealthInfo } from "../types";
import { useTheme } from "../theme";

interface Props {
  connected: boolean;
  threadId: string | null;
}

export function Header({ connected, threadId }: Props) {
  const [health, setHealth] = useState<HealthInfo | null>(null);
  const { theme, toggle } = useTheme();

  useEffect(() => {
    fetchHealth()
      .then(setHealth)
      .catch(() => null);
  }, []);

  return (
    <header className="flex items-center justify-between px-5 py-3 border-b border-border-subtle bg-bg-panel">
      <div className="flex items-center gap-3">
        <div className="w-7 h-7 rounded grid place-items-center bg-accent-oracle/20 text-accent-oracle">
          <Database size={16} />
        </div>
        <div className="leading-tight">
          <div className="text-sm font-semibold text-text-primary">
            Supply-chain demand-planning agent
          </div>
          <div className="text-[11px] text-text-secondary">
            multi-agent supervisor on Oracle AI Database
          </div>
        </div>
      </div>

      <div className="flex items-center gap-2 text-[11px] font-mono">
        {health && (
          <>
            <span className="chip bg-accent-skill/15 text-accent-skill">
              <Sparkles size={11} />
              {health.llm_provider}/{health.llm_model}
            </span>
            <span className="chip bg-accent-memory/15 text-accent-memory">
              {health.onnx_model} · {health.onnx_dim}d
            </span>
          </>
        )}
        <span
          className={`chip ${
            connected
              ? "bg-accent-memory/15 text-accent-memory"
              : "bg-accent-sql/15 text-accent-sql"
          }`}
        >
          <Activity size={11} />
          {connected ? "live" : "offline"}
        </span>
        {threadId && (
          <span className="chip bg-overlay-medium text-text-secondary">
            thread {threadId.slice(0, 12)}
          </span>
        )}
        <button
          onClick={toggle}
          aria-label={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
          title={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
          className="ml-1 w-7 h-7 rounded grid place-items-center bg-bg-elev border border-border-subtle text-text-secondary hover:text-text-primary hover:bg-bg-hover transition-colors"
        >
          {theme === "dark" ? <Sun size={13} /> : <Moon size={13} />}
        </button>
      </div>
    </header>
  );
}
