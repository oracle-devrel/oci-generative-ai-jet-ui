import { useCallback, useEffect, useState } from "react";

const STORAGE_KEY = "eda_identity_id";
const FALLBACK_IDENTITIES = [
  {
    id: "agent",
    label: "AGENT (default)",
    description: "Default DB principal — full visibility on what AGENT was granted.",
    clearance: "STANDARD",
    regions: null,
    mask_cols: [],
    forbid_tables: [],
  },
];

/**
 * Tracks the active "Use As:" identity. Persists choice in localStorage so
 * a refresh keeps the persona. Returns the identity object plus a setter that
 * accepts an id (e.g. "cfo", "analyst.east").
 */
export function useIdentity() {
  const [identities, setIdentities] = useState(FALLBACK_IDENTITIES);
  const [identityId, setIdentityIdState] = useState(() => {
    try {
      return window.localStorage.getItem(STORAGE_KEY) || "agent";
    } catch {
      return "agent";
    }
  });

  useEffect(() => {
    fetch("/api/identities")
      .then((r) => r.json())
      .then((d) => {
        if (Array.isArray(d.identities) && d.identities.length > 0) {
          setIdentities(d.identities);
        }
      })
      .catch(() => {});
  }, []);

  const setIdentityId = useCallback((id) => {
    setIdentityIdState(id);
    try {
      window.localStorage.setItem(STORAGE_KEY, id);
    } catch {
      /* storage disabled — non-fatal */
    }
  }, []);

  const identity =
    identities.find((i) => i.id === identityId) || identities[0];

  return { identities, identityId, setIdentityId, identity };
}
