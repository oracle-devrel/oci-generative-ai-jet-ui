import { useCallback, useEffect, useRef, useState } from "react";

const AUTO_FOLLOW_KEY = "ffw.worldAutoFollow";
const PENDING_MAX_MS = 15_000;

/**
 * Listens for the agent's globe-driving events and exposes them as state.
 *
 * The globe reacts to two kinds of events, both delivered on the `focus_world`
 * channel:
 *   - source:"explicit" — the model called the focus_world tool.
 *   - source:"auto"     — inferred from the query the agent just ran (a region
 *                         in a SQL result, an account's home branch, a region
 *                         named in the user's question, …).
 *
 * `autoFollow` (persisted per browser) gates the automatic ones: when it is on
 * the globe flies on its own as the agent works; when off only explicit calls
 * move it, but the latest activity is still reported so the panel can show
 * what the agent just looked at.
 *
 *   tool_started {name:"focus_world"}  → agentFocus {pending:true}  (banner)
 *   focus_world  {…}                   → agentFocus + focusTarget  (banner + fly)
 */
export function useWorldFocus(socket) {
  const [agentFocus, setAgentFocus] = useState(null);
  const [focusTarget, setFocusTarget] = useState(null);
  const [lastActivity, setLastActivity] = useState(null);
  const [autoFollow, setAutoFollow] = useState(() => {
    const saved = window.localStorage.getItem(AUTO_FOLLOW_KEY);
    return saved == null ? true : saved === "1";
  });
  const autoFollowRef = useRef(autoFollow);
  autoFollowRef.current = autoFollow;
  const clearTimer = useRef(null);

  const dismiss = useCallback(() => {
    if (clearTimer.current) window.clearTimeout(clearTimer.current);
    setAgentFocus(null);
  }, []);

  useEffect(() => {
    window.localStorage.setItem(AUTO_FOLLOW_KEY, autoFollow ? "1" : "0");
  }, [autoFollow]);

  useEffect(() => {
    if (!socket) return;

    const onToolStarted = (p) => {
      // The model is *about to* fly the globe — show a pending banner so the
      // panel reacts even before the resolve round-trip finishes.
      if (p && p.name === "focus_world") {
        const args = p.args || {};
        setAgentFocus({
          kind: args.target_kind || "—",
          target: args.target || "",
          label: `resolving ${args.target_kind || ""} ${args.target || ""}…`.trim(),
          lat: 0,
          lng: 0,
          altitude: args.altitude,
          pending: true,
          source: "explicit",
        });
        // If the tool fails no `focus_world` event ever replaces this banner.
        if (clearTimer.current) window.clearTimeout(clearTimer.current);
        clearTimer.current = window.setTimeout(() => setAgentFocus(null), PENDING_MAX_MS);
      }
    };

    // Resolved banners are replaced by the `focus_world` event; one still
    // pending when its tool call ends means the call failed — drop it.
    const onToolFinished = (p) => {
      if (p && p.name === "focus_world") {
        setAgentFocus((cur) => (cur && cur.pending ? null : cur));
      }
    };

    const onFocus = (p) => {
      if (!p) return;
      const isAuto = p.source === "auto";
      setLastActivity({ ...p, _ts: Date.now() });
      if (isAuto && !autoFollowRef.current) return;
      setAgentFocus(p);
      setFocusTarget({ ...p, _seq: Date.now() });
      if (clearTimer.current) window.clearTimeout(clearTimer.current);
      clearTimer.current = window.setTimeout(() => setAgentFocus(null), isAuto ? 5000 : 6000);
    };

    socket.on("tool_started", onToolStarted);
    socket.on("tool_finished", onToolFinished);
    socket.on("focus_world", onFocus);
    return () => {
      socket.off("tool_started", onToolStarted);
      socket.off("tool_finished", onToolFinished);
      socket.off("focus_world", onFocus);
      if (clearTimer.current) window.clearTimeout(clearTimer.current);
    };
  }, [socket]);

  return { agentFocus, focusTarget, lastActivity, dismiss, autoFollow, setAutoFollow };
}
