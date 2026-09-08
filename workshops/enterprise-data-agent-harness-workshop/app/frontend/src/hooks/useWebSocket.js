import { useEffect, useState } from "react";
import { io } from "socket.io-client";

export function useWebSocket() {
  const [socket, setSocket] = useState(null);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    const s = io({
      transports: ["websocket"],
      reconnection: true,
    });
    s.on("connect", () => setConnected(true));
    s.on("disconnect", () => setConnected(false));
    setSocket(s);
    return () => {
      s.removeAllListeners();
      s.disconnect();
    };
  }, []);

  return { socket, connected };
}
