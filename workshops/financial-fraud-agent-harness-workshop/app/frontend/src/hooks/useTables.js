import { useCallback, useEffect, useRef, useState } from "react";

export function useTables(identityId) {
  const [tables, setTables] = useState([]);
  const [active, setActive] = useState(null);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [search, setSearch] = useState("");

  const asUserParam = `as_user=${encodeURIComponent(identityId || "agent")}`;

  // Row requests can resolve out of order (fast tab clicks, one request per
  // keystroke in the filter box); only the newest one may touch state.
  const rowsReq = useRef(0);

  const fetchTableList = useCallback(() => {
    fetch(`/api/data/tables?${asUserParam}`)
      .then((r) => r.json())
      .then((d) => {
        const list = d.tables || [];
        setTables(list);
        // Keep the current selection (same object, so the rows effect does not
        // re-fire); fall back to the first table when there is none.
        setActive((cur) =>
          cur && list.some((t) => t.schema === cur.schema && t.name === cur.name)
            ? cur
            : list[0] || null,
        );
      })
      .catch((e) => setError(String(e)));
  }, [asUserParam]);

  const fetchRows = useCallback(
    (table, q = "") => {
      if (!table) return;
      const req = ++rowsReq.current;
      setLoading(true);
      setError(null);
      const url = `/api/data/tables/${table.schema}/${table.name}/rows`
        + `?limit=200&offset=0&${asUserParam}`
        + (q ? `&search=${encodeURIComponent(q)}` : "");
      fetch(url)
        .then((r) => r.json())
        .then((d) => {
          if (req !== rowsReq.current) return;
          if (d.error) {
            setError(d.error);
            setData(null);
          } else {
            setData(d);
          }
        })
        .catch((e) => {
          if (req === rowsReq.current) setError(String(e));
        })
        .finally(() => {
          if (req === rowsReq.current) setLoading(false);
        });
    },
    [asUserParam]
  );

  useEffect(() => {
    fetchTableList();
  }, [fetchTableList]);

  // When the table or identity changes, drop the row filter (a term typed for
  // one table rarely fits another, and it would silently hide every row) and
  // refetch so masks/filters apply.
  useEffect(() => {
    setSearch("");
    if (active) fetchRows(active, "");
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
      fetch(`/api/data/scan/${encodeURIComponent(schema)}`, { method: "POST" })
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
