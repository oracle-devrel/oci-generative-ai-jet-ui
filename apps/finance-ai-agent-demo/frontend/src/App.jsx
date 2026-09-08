import { useWebSocket } from "./hooks/useWebSocket";
import { useChat } from "./hooks/useChat";
import Layout from "./components/Layout";

export default function App() {
  const { socket, connected, comparisonAvailable } = useWebSocket();
  const chat = useChat(socket);

  return (
    <Layout
      connected={connected}
      chat={chat}
      socket={socket}
      comparisonAvailable={comparisonAvailable}
    />
  );
}
