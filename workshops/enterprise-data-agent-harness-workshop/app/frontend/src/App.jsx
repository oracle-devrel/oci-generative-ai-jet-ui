import { useWebSocket } from "./hooks/useWebSocket";
import { useChat } from "./hooks/useChat";
import { useIdentity } from "./hooks/useIdentity";
import Layout from "./components/Layout";

export default function App() {
  const { socket, connected } = useWebSocket();
  const identity = useIdentity();
  const chat = useChat(socket, identity.identityId);

  return (
    <Layout
      connected={connected}
      chat={chat}
      identity={identity}
      socket={socket}
    />
  );
}
