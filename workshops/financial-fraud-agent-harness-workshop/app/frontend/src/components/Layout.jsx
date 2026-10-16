import { useEffect, useRef, useState } from "react";
import { Plus, History } from "lucide-react";
import Header from "./Header";
import ChatPane from "./ChatPane";
import InstrumentPanel from "./InstrumentPanel";
import HistoryDrawer from "./HistoryDrawer";
import { useWorldFocus } from "../hooks/useWorldFocus";
import { useAmlLoop } from "../hooks/useAmlLoop";

const MIN_FRAC = 0.26;
const MAX_FRAC = 0.72;
const DEFAULT_FRAC = 0.46;

function RailButton({ icon: Icon, label, onClick, active }) {
  return (
    <button
      onClick={onClick}
      title={label}
      className={`group relative w-9 h-9 rounded-md flex items-center justify-center transition-colors ${
        active
          ? "bg-white/10 text-text-primary"
          : "text-text-secondary hover:text-text-primary hover:bg-white/5"
      }`}
    >
      <Icon size={16} />
      <span className="pointer-events-none absolute left-11 z-50 whitespace-nowrap rounded border border-white/10 bg-bg-elev px-2 py-1 text-[10px] text-text-secondary opacity-0 group-hover:opacity-100 transition-opacity">
        {label}
      </span>
    </button>
  );
}

/**
 * Split analyst workspace.
 *
 *   Header
 *   ├─ slim rail (new thread · conversations)
 *   └─ workspace (resizable split)
 *      ├─ ChatPane
 *      └─ InstrumentPanel  [World | Context | Data | Autonomous]
 *
 * The globe lives in the World tab and is visible by default, in parallel with
 * the chat. Conversation history moved off the permanent left column into a
 * slide-over toggled from the rail. The split between chat and instruments is
 * drag-resizable and remembered per browser.
 */
export default function Layout({ connected, chat, identity, socket, live }) {
  const [tab, setTab] = useState("world");
  const [historyOpen, setHistoryOpen] = useState(false);
  const [panelFrac, setPanelFrac] = useState(() => {
    const saved = Number(window.localStorage.getItem("ffw.panelFrac"));
    return Number.isFinite(saved) && saved >= MIN_FRAC && saved <= MAX_FRAC ? saved : DEFAULT_FRAC;
  });

  const workspaceRef = useRef(null);
  const dragging = useRef(false);
  const worldFocus = useWorldFocus(socket);
  const aml = useAmlLoop(socket);

  // Auto-surface the World tab whenever the agent drives the globe.
  useEffect(() => {
    if (worldFocus.agentFocus) setTab("world");
  }, [worldFocus.agentFocus]);

  useEffect(() => {
    window.localStorage.setItem("ffw.panelFrac", String(panelFrac));
  }, [panelFrac]);

  // Esc closes the history drawer.
  useEffect(() => {
    const onKey = (e) => {
      if (e.key === "Escape") setHistoryOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const onHandleDown = (e) => {
    const rect = workspaceRef.current?.getBoundingClientRect();
    if (!rect) return;
    dragging.current = true;
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";
    const onMove = (ev) => {
      if (!dragging.current) return;
      const frac = (rect.right - ev.clientX) / rect.width;
      setPanelFrac(Math.min(MAX_FRAC, Math.max(MIN_FRAC, frac)));
    };
    const onUp = () => {
      dragging.current = false;
      document.removeEventListener("mousemove", onMove);
      document.removeEventListener("mouseup", onUp);
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
    };
    document.addEventListener("mousemove", onMove);
    document.addEventListener("mouseup", onUp);
    e.preventDefault();
  };

  const selectThread = (tid) => {
    chat.loadThread(tid);
    setHistoryOpen(false);
  };

  return (
    <div className="h-screen flex flex-col bg-bg-base text-text-primary overflow-hidden">
      <Header
        connected={connected}
        threadId={chat.threadId}
        identities={identity.identities}
        identityId={identity.identityId}
        onIdentityChange={identity.setIdentityId}
        live={live}
      />

      <div className="flex-1 flex overflow-hidden relative min-h-0">
        {/* Slim rail — replaces the permanent thread column */}
        <nav className="w-12 shrink-0 border-r border-white/5 bg-bg-panel flex flex-col items-center py-2 gap-1">
          <RailButton icon={Plus} label="New thread" onClick={chat.newThread} />
          <RailButton
            icon={History}
            label="Conversations"
            active={historyOpen}
            onClick={() => setHistoryOpen((v) => !v)}
          />
        </nav>

        {/* Workspace — resizable chat / instruments split */}
        <div
          ref={workspaceRef}
          className="flex-1 flex flex-col lg:flex-row overflow-hidden min-w-0 min-h-0 relative"
          style={{ "--panel-frac": `${panelFrac * 100}%` }}
        >
          <ChatPane chat={chat} identity={identity.identity} />

          {/* Drag handle (desktop only) */}
          <div
            onMouseDown={onHandleDown}
            className="hidden lg:flex w-1.5 shrink-0 cursor-col-resize items-center justify-center bg-bg-base hover:bg-accent-skill/20 transition-colors group"
            title="drag to resize"
          >
            <span className="w-px h-8 bg-white/10 group-hover:bg-accent-skill/60" />
          </div>

          <InstrumentPanel
            tab={tab}
            onTabChange={setTab}
            identityId={identity.identityId}
            agentFocus={worldFocus.agentFocus}
            focusTarget={worldFocus.focusTarget}
            lastActivity={worldFocus.lastActivity}
            autoFollow={worldFocus.autoFollow}
            onToggleAutoFollow={() => worldFocus.setAutoFollow((v) => !v)}
            onDismissFocus={worldFocus.dismiss}
            contextWindow={chat.contextWindow}
            tokenUsage={chat.tokenUsage}
            touched={chat.touched}
            trace={chat.liveTrace}
            isThinking={chat.isThinking}
            live={live}
            identity={identity.identity}
            aml={aml}
          />

          <HistoryDrawer
            open={historyOpen}
            onClose={() => setHistoryOpen(false)}
            threads={chat.threads}
            currentThreadId={chat.threadId}
            onSelect={selectThread}
            onDelete={chat.deleteThread}
            onNewThread={chat.newThread}
          />
        </div>
      </div>
    </div>
  );
}
