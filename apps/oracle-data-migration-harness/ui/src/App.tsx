import { useState } from "react";
import { ChatPane } from "./components/ChatPane";
import { MigrateButton } from "./components/MigrateButton";
import { MigrateProgress } from "./components/MigrateProgress";
import { AssessmentCard } from "./components/AssessmentCard";
import { startMigration, streamMigration, resetMigration, type StageEvent } from "./api/migrate";
import "./index.css";

export default function App() {
  const [events, setEvents] = useState<StageEvent[]>([]);
  const [unlocked, setUnlocked] = useState(false);
  const [migrating, setMigrating] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);
  const [resetKey, setResetKey] = useState(0);

  async function migrate() {
    setMigrating(true);
    setEvents([]);
    await startMigration();
    streamMigration(
      (e) => {
        setEvents((prev) => [...prev, e]);
        if (e.stage === "unlocked") {
          setUnlocked(true);
          setRefreshKey((k) => k + 1);
        }
      },
      () => setMigrating(false)
    );
  }

  async function reset() {
    await resetMigration();
    setEvents([]);
    setUnlocked(false);
    setMigrating(false);
    setRefreshKey((k) => k + 1);
    setResetKey((k) => k + 1);
  }

  return (
    <div className="h-screen flex">
      <section className="flex-1 border-r border-oracle-ink/10 p-6">
        <ChatPane side="mongo" refreshKey={refreshKey} resetKey={resetKey} />
      </section>
      <aside className="h-screen w-[30rem] flex flex-col items-center justify-start gap-4 p-6 bg-oracle-cream/40 overflow-hidden">
        <div className="w-full shrink-0 flex flex-col items-center gap-4">
          <h2 className="text-sm font-semibold uppercase tracking-wide opacity-70">Migrate</h2>
          <AssessmentCard refreshKey={refreshKey} />
          <MigrateButton onClick={migrate} disabled={migrating || unlocked} />
        </div>
        <div className="w-full flex-1 min-h-0 overflow-y-auto pr-1">
          <MigrateProgress events={events} />
        </div>
        <div className="w-full shrink-0 border-t border-oracle-ink/10 pt-3 text-center bg-oracle-cream/40">
          <button
            onClick={reset}
            className="text-xs text-oracle-ink/40 hover:text-oracle-red underline-offset-2 hover:underline"
          >
            reset for next rehearsal
          </button>
        </div>
      </aside>
      <section className="flex-1 border-l border-oracle-ink/10 p-6">
        <ChatPane side="oracle" locked={!unlocked} refreshKey={refreshKey} resetKey={resetKey} />
      </section>
    </div>
  );
}
