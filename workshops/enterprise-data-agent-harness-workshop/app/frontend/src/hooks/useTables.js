import { useCallback, useEffect, useState } from "react";

export function useTables(identityId) {
  const [tables, setTables] = useState([]);
  const [active, setActive] = useState(null);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [search, setSearch] = useState("");

  const asUserParam = `as_user=${encodeURIComponent(identityId || "agent")}`;

  const fetchTableList = useCallback(() => {
    fetch(`/api/data/tables?${asUserParam}`)
      .then((r) => r.json())
      .then((d) => {
        setTables(d.tables || []);
        if (!active && d.tables && d.tables.length > 0) {
          setActive(d.tables[0]);
        }
      })
      .catch((e) => setError(String(e)));
  }, [active, asUserParam]);

  const fetchRows = useCallback(
    (table, q = "") => {
      if (!table) return;
      setLoading(true);
      setError(null);
      const url = `/api/data/tables/${table.schema}/${table.name}/rows`
        + `?limit=200&offset=0&${asUserParam}`
        + (q ? `&search=${encodeURIComponent(q)}` : "");
      fetch(url)
        .then((r) => r.json())
        .then((d) => {
          if (d.error) {
            setError(d.error);
            setData(null);
          } else {
            setData(d);
          }
        })
        .catch((e) => setError(String(e)))
        .finally(() => setLoading(false));
    },
    [asUserParam]
  );

  useEffect(() => {
    fetchTableList();
  }, [fetchTableList]);

  // When identity changes, refetch the rows so masks/filters apply.
  useEffect(() => {
    if (active) fetchRows(active, search);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [active, identityId]);

  const submitSearch = useCallback(
    (q) => {
      setSearch(q);
      if (active) fetchRows(active, q);
    },
    [active, fetchRows]
  );

  const refresh = useCallback(() => {
    fetchTableList();
    if (active) fetchRows(active, search);
  }, [active, fetchRows, fetchTableList, search]);

  const [scanState, setScanState] = useState({ status: "idle", summary: null, error: null });
  const scan = useCallback(
    (schema) => {
      if (!schema) return;
      setScanState({ status: "running", summary: null, error: null });
      fetch(`/api/data/scan/${schema}`, { method: "POST" })
        .then((r) => r.json())
        .then((d) => {
          if (d.error) {
            setScanState({ status: "error", summary: null, error: d.error });
          } else {
            setScanState({ status: "done", summary: d.summary, error: null });
            // Refresh table list so row counts update if scan_history grew
            fetchTableList();
          }
        })
        .catch((e) =>
          setScanState({ status: "error", summary: null, error: String(e) })
        );
    },
    [fetchTableList]
  );

  return {
    tables,
    active,
    setActive,
    data,
    loading,
    error,
    search,
    submitSearch,
    refresh,
    scan,
    scanState,
  };
}
