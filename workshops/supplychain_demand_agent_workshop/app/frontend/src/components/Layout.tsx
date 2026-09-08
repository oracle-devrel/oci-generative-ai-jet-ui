import { ArchitectureExplorer } from "./ArchitectureExplorer";
import { ChatPane } from "./ChatPane";
import { DataExplorer } from "./DataExplorer";
import { Header } from "./Header";
import { MemoryContext } from "./MemoryContext";
import { ThreadList } from "./ThreadList";
import { useAgentSocket } from "../useAgentSocket";

const WS_URL = (() => {
  const proto = window.location.protocol === "https:" ? "wss" : "ws";
  return `${proto}://${window.location.host}/ws/chat`;
})();

export function Layout() {
  const {
    threadId,
    connected,
    isThinking,
    chat,
    agents,
    edgeActivity,
    nodeActivity,
    tableActivity,
    send,
  } = useAgentSocket(WS_URL);

  return (
    <div className="flex flex-col h-full bg-bg-base">
      <Header connected={connected} threadId={threadId} />

      {/* Top row — three panes */}
      <div className="flex flex-1 min-h-0 gap-px bg-border-subtle">
        <ThreadList threadId={threadId} />
        <ChatPane chat={chat} connected={connected} isThinking={isThinking} onSend={send} />
        <MemoryContext agents={agents} />
      </div>

      {/* Bottom row — two stacked-side-by-side explorers */}
      <div className="flex shrink-0 h-[36vh] min-h-[280px] gap-px bg-border-subtle border-t border-border-subtle">
        <div className="flex-1 min-w-0">
          <DataExplorer tableActivity={tableActivity} />
        </div>
        <div className="flex-1 min-w-0">
          <ArchitectureExplorer edgeActivity={edgeActivity} nodeActivity={nodeActivity} />
        </div>
      </div>
    </div>
  );
}
