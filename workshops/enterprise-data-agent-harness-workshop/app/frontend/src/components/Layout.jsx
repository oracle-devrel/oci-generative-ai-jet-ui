import Header from "./Header";
import ChatPane from "./ChatPane";
import MemoryContext from "./MemoryContext";
import ThreadList from "./ThreadList";
import DataExplorer from "./DataExplorer";
import WorldExplorer from "./WorldExplorer";

export default function Layout({ connected, chat, identity, socket }) {
  return (
    <div className="h-screen flex flex-col bg-bg-base text-text-primary">
      <Header
        connected={connected}
        threadId={chat.threadId}
        onNewThread={chat.newThread}
        identities={identity.identities}
        identityId={identity.identityId}
        onIdentityChange={identity.setIdentityId}
      />
      <div className="flex-1 flex flex-col overflow-hidden">
        <div className="flex-1 flex overflow-hidden">
          <ThreadList
            threads={chat.threads}
            currentThreadId={chat.threadId}
            onSelect={chat.loadThread}
            onDelete={chat.deleteThread}
          />
          <ChatPane chat={chat} identity={identity.identity} />
          <MemoryContext contextWindow={chat.contextWindow} tokenUsage={chat.tokenUsage} />
        </div>
        <DataExplorer identityId={identity.identityId} touched={chat.touched} />
        <WorldExplorer identityId={identity.identityId} socket={socket} />
      </div>
    </div>
  );
}
