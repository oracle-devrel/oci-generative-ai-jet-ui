"""Collect step (Google Drive): folders you SHARE with the loader -> the brain.

One-time setup (~10 minutes):
  1. console.cloud.google.com -> create a project -> enable the "Google Drive API"
  2. IAM & Admin -> Service Accounts -> create one -> Keys -> add JSON key ->
     save the file OUTSIDE the repo (e.g. ~/keys/brain-gdrive.json)
  3. In Google Drive, share each folder you want ingested with the service
     account's email address (Viewer is enough). THE LOADER CAN ONLY SEE WHAT
     YOU SHARE — the rest of your Drive is invisible to it, by construction.
  4. In oracle/.env:
       GDRIVE_KEY=/absolute/path/to/key.json
       GDRIVE_FOLDERS=<folderId>[,<folderId>...]     (the id from the folder URL)
       GDRIVE_EXCLUDE=<folderId>[,...]   (optional: subtrees to skip — e.g. a
                                          contracts/ folder inside a shared tree)

What it ingests (recursively): Google Docs (exported as plain text), .md/.txt,
PDFs and EPUBs. Everything else — video, audio, images, spreadsheets, slides —
is skipped by design (your footage stays footage). Files over 30 MB are skipped.

kind mapping: Docs/notes -> 'note'; PDFs/EPUBs -> 'reference' (searchable, but
the wiki compiler ignores reference material — it synthesizes your work, not
your library). series: the top-level shared folder's name, lowercased.

Idempotent on Drive's modifiedTime: unchanged files are skipped, edited ones
re-import in place. Safe for the scheduled daily sync (pure API, no browser).
"""
import hashlib
import io
import os
import pathlib
import re
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "oracle" / "agent"))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import db                                    # noqa: E402
from content import doc_chunks, note_chunks  # noqa: E402
from obsidian import extract_epub            # noqa: E402

API = "https://www.googleapis.com/drive/v3"
MAX_BYTES = 30 * 1024 * 1024

# mimeType -> how to get text ('export' = Google Doc; 'text'/'pdf'/'epub' = download)
ROUTES = {
    "application/vnd.google-apps.document": ("export", "note"),
    "text/markdown": ("text", "note"),
    "text/plain": ("text", "note"),
    "application/pdf": ("pdf", "reference"),
    "application/epub+zip": ("epub", "reference"),
}
EXT_ROUTES = {".md": ("text", "note"), ".txt": ("text", "note"),
              ".pdf": ("pdf", "reference"), ".epub": ("epub", "reference")}


def route(mime, name):
    """Pure: (handler, kind) for a Drive file, or None to skip. Folders excluded."""
    if mime == "application/vnd.google-apps.folder":
        return None
    if mime in ROUTES:
        return ROUTES[mime]
    return EXT_ROUTES.get(pathlib.Path(name or "").suffix.lower())


def _session():
    import json as _json
    from google.auth.transport.requests import AuthorizedSession
    from google.oauth2 import service_account
    key = os.environ["GDRIVE_KEY"]
    scopes = ["https://www.googleapis.com/auth/drive.readonly"]
    if key.lstrip().startswith("{"):      # keychain-resolved JSON content
        creds = service_account.Credentials.from_service_account_info(
            _json.loads(key), scopes=scopes)
    else:                                  # plain file path
        creds = service_account.Credentials.from_service_account_file(key, scopes=scopes)
    return AuthorizedSession(creds)


def walk(sess, folder_id, exclude=frozenset()):
    """Yield file dicts in a folder, recursively; excluded subtree ids are skipped."""
    if folder_id in exclude:
        return
    page = None
    while True:
        params = {"q": f"'{folder_id}' in parents and trashed = false",
                  "fields": "nextPageToken, files(id, name, mimeType, modifiedTime, size)",
                  "pageSize": 200}
        if page:
            params["pageToken"] = page
        r = sess.get(f"{API}/files", params=params, timeout=60)
        r.raise_for_status()
        data = r.json()
        for f in data.get("files", []):
            if f["mimeType"] == "application/vnd.google-apps.folder":
                yield from walk(sess, f["id"], exclude)
            else:
                yield f
        page = data.get("nextPageToken")
        if not page:
            return


def fetch_text(sess, f, handler):
    if handler == "export":
        r = sess.get(f"{API}/files/{f['id']}/export",
                     params={"mimeType": "text/plain"}, timeout=120)
        r.raise_for_status()
        return r.text
    r = sess.get(f"{API}/files/{f['id']}", params={"alt": "media"}, timeout=300)
    r.raise_for_status()
    if handler == "text":
        return r.content.decode("utf-8", errors="replace")
    if handler == "pdf":
        from pypdf import PdfReader
        return "\n".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(r.content)).pages)
    if handler == "epub":
        with tempfile.NamedTemporaryFile(suffix=".epub") as t:
            t.write(r.content)
            t.flush()
            return extract_epub(pathlib.Path(t.name))
    return ""


def main():
    key = os.environ.get("GDRIVE_KEY")
    folders = [x.strip() for x in os.environ.get("GDRIVE_FOLDERS", "").split(",") if x.strip()]
    exclude = frozenset(x.strip() for x in os.environ.get("GDRIVE_EXCLUDE", "").split(",")
                        if x.strip())
    valid_key = key and (key.lstrip().startswith("{") or pathlib.Path(key).is_file())
    if not valid_key or not folders:
        raise SystemExit("GDRIVE_KEY (service-account json) and GDRIVE_FOLDERS "
                         "(comma-separated folder ids) must be set in oracle/.env — "
                         "see the setup steps in this file's docstring.")
    sess = _session()
    conn = db.connect()
    cur = conn.cursor()
    cur.execute("alter session disable parallel dml")
    cur.execute("merge into platforms p using (select 'gdrive' id from dual) s "
                "on (p.platform_id=s.id) when not matched then "
                "insert (platform_id, display_name) values ('gdrive','Google Drive')")

    new = updated = unchanged = skipped = 0
    for fid in folders:
        r = sess.get(f"{API}/files/{fid}", params={"fields": "name"}, timeout=60)
        r.raise_for_status()
        words = re.findall(r"[a-z0-9]+", r.json()["name"].lower())
        series = ""
        for w in words:                       # pack whole words into the 20-char column
            if len(series) + len(w) + bool(series) > 20:
                break
            series = f"{series}_{w}" if series else w
        for f in walk(sess, fid, exclude):
            routed = route(f["mimeType"], f.get("name"))
            if not routed or int(f.get("size") or 0) > MAX_BYTES:
                skipped += 1
                continue
            handler, kind = routed
            url = f"gdrive://{f['id']}"
            marker = f"§{hashlib.md5(f['modifiedTime'].encode()).hexdigest()[:12]}§"
            cur.execute("SELECT post_id FROM posts WHERE url = :u "
                        "AND DBMS_LOB.INSTR(caption, :m) > 0", u=url, m=marker)
            if cur.fetchone():
                unchanged += 1
                continue
            try:
                body = fetch_text(sess, f, handler).strip()
            except Exception as e:
                print(f"  ! {f['name']}: {e}")
                continue
            if len(body) < 15:
                continue
            cur.execute("SELECT post_id FROM posts WHERE url = :u", u=url)
            row = cur.fetchone()
            if row:
                cur.execute("DELETE FROM content_chunks WHERE post_id = :p", p=row[0])
                cur.execute("DELETE FROM posts WHERE post_id = :p", p=row[0])
                updated += 1
            else:
                new += 1
            caption = f"{body[:28000]}\n{marker}"
            cur.execute(
                """INSERT INTO posts (platform_id, kind, title, caption, url, series,
                       visibility, content_embedding)
                   VALUES ('gdrive', :k, :t, :c, :u, :s, 'content',
                       VECTOR_EMBEDDING(MINILM USING :e AS DATA))
                   RETURNING post_id INTO :pid""",
                k=kind, t=f["name"][:490], c=caption, u=url, s=series,
                e=(f["name"] + "\n" + body)[:3500], pid=(pid := cur.var(int)))
            post_id = pid.getvalue()[0]
            chunker = doc_chunks if kind == "reference" else note_chunks
            for i, ch in enumerate(chunker(body)):
                cur.execute(
                    """INSERT INTO content_chunks (post_id, seq, chunk, embedding)
                       VALUES (:p, :s, :t, VECTOR_EMBEDDING(MINILM USING :t AS DATA))""",
                    p=post_id, s=i, t=ch)
    conn.commit()
    conn.close()
    print(f"gdrive: {new} new, {updated} updated, {unchanged} unchanged, "
          f"{skipped} skipped (folders/media/oversize)")


if __name__ == "__main__":
    main()
