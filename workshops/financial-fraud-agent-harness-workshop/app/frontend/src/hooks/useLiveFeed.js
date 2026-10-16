import { useCallback, useEffect, useState } from "react";

const MAX_EVENTS = 40;

/**
 * Subscribes to the backend's simulated live transaction feed.
 *
 * The server inserts one new banking transaction every few seconds and
 * broadcasts it as `live_txn`; this hook keeps the most recent events plus
 * running counters so the World panel can pulse markers, draw arcs, and show a
 * live ticker. `setFeed(false)` pauses the simulator server-side (a global
 * switch — the feed is one process-wide stream), and `enabled` reflects the
 * authoritative server state, not just local intent.
 */
export function useLiveFeed(socket) {
  const [enabled, setEnabled] = useState(true);
  const [known, setKnown] = useState(false);
  const [events, setEvents] = useState([]);
  const [counts, setCounts] = useState({ total: 0, flagged: 0, blocked: 0 });
  const [seq, setSeq] = useState(0);

  useEffect(() => {
    if (!socket) return;

    const onStatus = (p) => {
      if (!p) return;
      setEnabled(!!p.enabled);
      setKnown(true);
    };
    const onTxn = (p) => {
      if (!p) return;
      // Stamp arrival so the globe can fade live arcs/points out after a short
      // window instead of letting every line accumulate.
      setEvents((prev) => [{ ...p, receivedAt: Date.now() }, ...prev].slice(0, MAX_EVENTS));
      setSeq((s) => s + 1);
      setCounts((c) => ({
        total: c.total + 1,
        flagged: c.flagged + (p.status === "FLAGGED" ? 1 : 0),
        blocked: c.blocked + (p.status === "BLOCKED" ? 1 : 0),
      }));
    };
    const request = () => socket.emit("live_feed_status_request");

    socket.on("live_feed_status", onStatus);
    socket.on("live_txn", onTxn);
    socket.on("connect", request);
    if (socket.connected) request();

    return () => {
      socket.off("live_feed_status", onStatus);
      socket.off("live_txn", onTxn);
      socket.off("connect", request);
    };
  }, [socket]);

  const setFeed = useCallback(
    (next) => {
      setEnabled(next);
      socket?.emit("live_feed_control", { enabled: next });
    },
    [socket],
  );

  return {
    enabled,
    known,
    events,
    counts,
    lastEvent: events[0] || null,
    seq,
    setFeed,
  };
}
