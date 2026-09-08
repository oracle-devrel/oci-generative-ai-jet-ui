"""Minimal file-like wrapper over Oracle DBFS — mirrors the notebook's §7.2 DBFS
class. The DBFS store + mount must already exist (created by `dbfs_setup.ensure`)."""

from __future__ import annotations

import oracledb


DBFS_TABLESPACE = "AGENT_DBFS_TS"
DBFS_STORE = "AGENT_SCRATCH"
DBFS_MOUNT = "/scratch"


class DBFS:
    """Minimal file-like wrapper over Oracle DBFS."""

    def __init__(self, conn, mount: str = DBFS_MOUNT):
        self.conn = conn
        self.mount = mount.rstrip("/")

    def _full(self, path: str) -> str:
        """Resolve a user-supplied path to the absolute DBFS path.

        Accepts both forms:
            'foo.sql'             → /scratch/foo.sql
            '/foo.sql'            → /scratch/foo.sql
            '/scratch/foo.sql'    → /scratch/foo.sql   (already mount-qualified)

        The third form was tripping ORA-64001 because we used to blindly
        prepend the mount and end up at /scratch/scratch/foo.sql.
        """
        if not path.startswith("/"):
            path = "/" + path
        if path == self.mount or path.startswith(self.mount + "/"):
            return path
        return f"{self.mount}{path}"

    def _ensure_dir(self, full_path: str) -> None:
        """Create the directory at `full_path` (and every parent inside the
        DBFS mount that doesn't exist yet) so that a subsequent CREATEFILE on
        a deeper path doesn't raise ORA-64001 / ORA-01403.

        The SFS provider requires every parent directory in the path to exist
        before a file can be created beneath it. We walk from the mount down,
        calling CREATEDIRECTORY on each segment and swallowing the "already
        exists" failure.
        """
        if not full_path or full_path == self.mount:
            return
        # Build the list of directories to ensure, in mount-order:
        #   /scratch/threads          ←
        #   /scratch/threads/abc      ←
        rel = full_path[len(self.mount):].lstrip("/")
        parts = [p for p in rel.split("/") if p]
        if not parts:
            return
        cur_path = self.mount
        plsql = (
            "DECLARE "
            "  l_props DBMS_DBFS_CONTENT_PROPERTIES_T := DBMS_DBFS_CONTENT_PROPERTIES_T(); "
            "BEGIN "
            "  DBMS_DBFS_CONTENT.CREATEDIRECTORY(path => :p, properties => l_props); "
            "  COMMIT; "
            "EXCEPTION WHEN OTHERS THEN NULL; "
            "END;"
        )
        with self.conn.cursor() as cur:
            for seg in parts:
                cur_path = f"{cur_path}/{seg}"
                cur.execute(plsql, p=cur_path)
        self.conn.commit()

    def write(self, path: str, content) -> None:
        data = content.encode("utf-8") if isinstance(content, str) else content
        full = self._full(path)
        # Ensure every intermediate directory exists so SFS won't refuse the
        # CREATEFILE on a nested path like /scratch/threads/<tid>/foo.sql.
        parent = full.rsplit("/", 1)[0]
        if parent and parent != self.mount:
            self._ensure_dir(parent)
        delete_plsql = (
            "BEGIN "
            "  DBMS_DBFS_CONTENT.DELETEFILE(:p); "
            "EXCEPTION WHEN OTHERS THEN NULL; "
            "END;"
        )
        create_plsql = (
            "DECLARE "
            "  l_props DBMS_DBFS_CONTENT_PROPERTIES_T := DBMS_DBFS_CONTENT_PROPERTIES_T(); "
            "  l_blob  BLOB := :b; "
            "BEGIN "
            "  DBMS_DBFS_CONTENT.CREATEFILE("
            "    path       => :p,"
            "    properties => l_props,"
            "    content    => l_blob); "
            "  COMMIT; "
            "END;"
        )
        with self.conn.cursor() as cur:
            cur.execute(delete_plsql, p=full)
            cur.setinputsizes(b=oracledb.DB_TYPE_BLOB)
            cur.execute(create_plsql, p=full, b=data)
        self.conn.commit()

    def append(self, path: str, content) -> None:
        """Append `content` to the file at `path`. If the file doesn't exist
        yet, behaves like `write`. Use this for running findings logs,
        transcripts, anything you want to grow over time without losing prior
        entries."""
        new = content.encode("utf-8") if isinstance(content, str) else content
        try:
            existing_text = self.read(path)
            existing = existing_text.encode("utf-8")
            sep = b"" if existing.endswith(b"\n") or not existing else b"\n"
            self.write(path, existing + sep + new)
        except FileNotFoundError:
            self.write(path, new)

    def read(self, path: str) -> str:
        full = self._full(path)
        read_plsql = (
            "DECLARE "
            "  l_props     DBMS_DBFS_CONTENT_PROPERTIES_T := DBMS_DBFS_CONTENT_PROPERTIES_T(); "
            "  l_blob      BLOB; "
            "  l_item_type NUMBER; "
            "BEGIN "
            "  DBMS_DBFS_CONTENT.GETPATH("
            "    path       => :p,"
            "    properties => l_props,"
            "    content    => l_blob,"
            "    item_type  => l_item_type); "
            "  :out := l_blob; "
            "END;"
        )
        try:
            with self.conn.cursor() as cur:
                out = cur.var(oracledb.DB_TYPE_BLOB)
                cur.execute(read_plsql, p=full, out=out)
                blob = out.getvalue()
            if blob is None:
                raise FileNotFoundError(full)
            return blob.read().decode("utf-8", errors="replace")
        except oracledb.DatabaseError as e:
            # SFS provider raises ORA-64002 for non-existent paths instead
            # of returning NULL — translate so callers (esp. append) can
            # treat both the same way via FileNotFoundError.
            if e.args and e.args[0].code in (64002, 64007):
                raise FileNotFoundError(full) from e
            raise

    def list(self, path: str = "/") -> list[str]:
        """List every file under `path` in DBFS.

        Two strategies, in order:

        1. `DBMS_DBFS_CONTENT.LIST(path, '*', 1)` — the documented API. Works on
           some providers; the SecureFile (SFS) provider on Oracle Free 26ai
           raises `ORA-64003` ("unsupported operation") instead.

        2. Direct query on the SFS storage table created by
           `DBMS_DBFS_SFS.CREATEFILESYSTEM` (we named it `AGENT_SCRATCH_T`).
           We introspect `user_tab_columns` to find the right path column —
           `PATHNAME` on most SFS versions, `PATH` on some — and filter to the
           prefix passed in.
        """
        full = self._full(path)
        out: list[str] = []

        # Strategy 1 — DBMS_DBFS_CONTENT.LIST
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    "SELECT * FROM TABLE(DBMS_DBFS_CONTENT.LIST(:p, '*', 1))",
                    p=full,
                )
                descs = cur.description or []
                path_idx = next(
                    (i for i, d in enumerate(descs)
                     if "PATH" in (d[0] or "").upper()),
                    0,
                )
                for row in cur:
                    v = row[path_idx]
                    if v:
                        out.append(v)
            if out:
                return out
        except oracledb.DatabaseError:
            pass

        # Strategy 2 — query the SFS storage table directly.
        #
        # IMPORTANT subtlety: SFS stores pathnames *without* the mount prefix
        # (just '/comment.txt', not '/scratch/comment.txt'). We translate the
        # caller's mount-qualified `full` path into an SFS-relative prefix for
        # the LIKE filter, then prepend the mount back onto every result so
        # callers get a consistent absolute path.
        store_table = f"{DBFS_STORE}_T"
        try:
            with self.conn.cursor() as cur:
                # Translate /scratch/<rest> → /<rest> for the SFS-side filter.
                if full == self.mount or full == self.mount + "/":
                    sfs_prefix = "/"
                elif full.startswith(self.mount + "/"):
                    sfs_prefix = full[len(self.mount):]
                    if not sfs_prefix.endswith("/"):
                        sfs_prefix += "/"
                else:
                    sfs_prefix = "/"

                # pathtype = 1 → file ; std_deleted = 0 → not tombstoned.
                cur.execute(
                    f"SELECT pathname FROM {store_table} "
                    f" WHERE pathtype = 1 AND std_deleted = 0 "
                    f"   AND pathname LIKE :p "
                    f" ORDER BY pathname",
                    p=f"{sfs_prefix}%",
                )
                for (n,) in cur:
                    if n:
                        # Prepend the mount so callers see /scratch/foo.txt
                        out.append(f"{self.mount}{n}")
        except oracledb.DatabaseError:
            pass

        return out
