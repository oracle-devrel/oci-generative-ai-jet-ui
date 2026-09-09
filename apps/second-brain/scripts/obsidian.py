"""Collect step (Obsidian / any local vault): notes AND documents -> the brain.

  OBSIDIAN_VAULT=/path/to/vault   in oracle/.env, then:
  ./.venv/bin/python scripts/obsidian.py          (or let the daily sync run it)

No export, no API, no account: an Obsidian vault is a plain folder of markdown, so this
reads it directly — which also makes it safe for the scheduled sync (local files only).
Works for ANY markdown folder, not just Obsidian: course notes, e-book highlights, an
Apple Notes export, a docs directory.

Conventions (all optional, read from YAML frontmatter):
  title:      overrides the filename
  tags:       stored in the caption header (searchable)
  series:     maps to the posts.series field (by_series tool picks it up)
  visibility: 'content' (default) or anything else to keep a note OUT of the
              searchable brain (e.g. 'private') — enforced like every other source
  created:    ISO date -> published_at

Wikilinks [[note]] / [[note|alias]] become plain text. The .obsidian/, .trash/ and
templates/ folders are skipped. Idempotent: each note gets a stable obsidian://<relpath>
url; unchanged notes are skipped (content hash), edited notes are re-imported in place.

DOCUMENTS TOO: .pdf and .epub files in the vault get their FULL TEXT extracted and
ingested as kind='reference' — searchable when you ask, but excluded from the wiki
compiler (your wiki synthesizes your work, not your library). .txt files load as
plain notes. Drop a book in the folder; it's searchable by the next sync.
"""
import hashlib
import os
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "oracle" / "agent"))
import db                      # noqa: E402
from content import doc_chunks, note_chunks  # noqa: E402

SKIP_DIRS = {".obsidian", ".trash", "templates", ".git"}
DOC_EXTS = {".pdf", ".epub"}


def extract_pdf(path):
    """Pure-ish: full text from a PDF (pypdf). Page furniture stays; search copes."""
    from pypdf import PdfReader
    out = []
    for page in PdfReader(str(path)).pages:
        out.append(page.extract_text() or "")
    return "\n".join(out)


def extract_epub(path):
    """Full text from an EPUB using only the stdlib: an epub is a zip of XHTML."""
    import html
    import zipfile
    out = []
    with zipfile.ZipFile(path) as z:
        for name in z.namelist():
            if name.lower().endswith((".xhtml", ".html", ".htm")):
                raw = z.read(name).decode("utf-8", errors="replace")
                text = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", raw,
                              flags=re.S | re.I)
                text = re.sub(r"</(p|div|h[1-6]|li|br)[^>]*>", "\n", text, flags=re.I)
                text = re.sub(r"<[^>]+>", " ", text)
                text = html.unescape(text)
                text = re.sub(r"[ \t]+", " ", text)
                text = re.sub(r"\n\s*", "\n", text).strip()
                if text:
                    out.append(text)
    return "\n\n".join(out)


def parse_note(text):
    """Pure: (frontmatter dict, plain body) from raw markdown. Testable without a DB."""
    meta = {}
    body = text
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) == 3:
            for line in parts[1].splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    meta[k.strip().lower()] = v.strip().strip("'\"")
            body = parts[2]
    body = re.sub(r"\[\[([^\]|]+)\|([^\]]+)\]\]", r"\2", body)   # [[note|alias]] -> alias
    body = re.sub(r"\[\[([^\]]+)\]\]", r"\1", body)              # [[note]] -> note
    body = re.sub(r"^#+ ", "", body, flags=re.M)                 # heading markers
    return meta, body.strip()


def vault_files(vault, exts):
    for p in sorted(vault.rglob("*")):
        if p.suffix.lower() in exts and not any(part in SKIP_DIRS for part in p.parts):
            yield p


def main():
    vault = os.environ.get("OBSIDIAN_VAULT")
    if not vault or not pathlib.Path(vault).is_dir():
        raise SystemExit("OBSIDIAN_VAULT is not set (or not a folder). Put "
                         "OBSIDIAN_VAULT=/path/to/your/vault in oracle/.env — any folder "
                         "of markdown works, not just Obsidian.")
    vault = pathlib.Path(vault)

    conn = db.connect()
    cur = conn.cursor()
    cur.execute("alter session disable parallel dml")
    cur.execute("merge into platforms p using (select 'obsidian' id from dual) s "
                "on (p.platform_id=s.id) when not matched then "
                "insert (platform_id, display_name) values ('obsidian','Obsidian vault')")

    new = updated = unchanged = private = docs = 0
    for path in vault_files(vault, {".md", ".txt"} | DOC_EXTS):
        rel = path.relative_to(vault).as_posix()
        kind = "note"
        meta = {}
        if path.suffix.lower() == ".pdf":
            body, kind, docs = extract_pdf(path), "reference", docs + 1
        elif path.suffix.lower() == ".epub":
            body, kind, docs = extract_epub(path), "reference", docs + 1
        else:
            meta, body = parse_note(path.read_text(errors="replace"))
        if len(body) < 15:
            continue
        url = f"obsidian://{rel}"
        h = hashlib.sha256(body.encode()).hexdigest()[:16]
        title = meta.get("title") or path.stem
        visibility = meta.get("visibility", "content")
        if visibility != "content":
            private += 1
        tags = meta.get("tags", "")
        series = meta.get("series") or ("books" if kind == "reference" else None)
        caption = (f"[tags: {tags}]\n{body}" if tags else body)[:28000]

        marker = f"§{h}§"
        cur.execute("SELECT post_id FROM posts WHERE url = :u "
                    "AND DBMS_LOB.INSTR(caption, :m) > 0", u=url, m=marker)
        if cur.fetchone():
            unchanged += 1
            continue
        cur.execute("SELECT post_id FROM posts WHERE url = :u", u=url)
        row = cur.fetchone()
        caption = f"{caption}\n{marker}"   # hash rides the tail, out of search snippets
        if row:
            cur.execute("DELETE FROM content_chunks WHERE post_id = :p", p=row[0])
            cur.execute("DELETE FROM posts WHERE post_id = :p", p=row[0])
            updated += 1
        else:
            new += 1
        cur.execute(
            """INSERT INTO posts (platform_id, kind, title, caption, url, series,
                   published_at, visibility, content_embedding)
               VALUES ('obsidian', :k, :t, :c, :u, :s,
                   TO_TIMESTAMP_TZ(:d, 'YYYY-MM-DD"T"HH24:MI:SS TZH:TZM'), :v,
                   VECTOR_EMBEDDING(MINILM USING :e AS DATA))
               RETURNING post_id INTO :pid""",
            k=kind, t=title[:490], c=caption, u=url, s=series,
            d=(meta.get("created", "")[:10] + "T00:00:00 +00:00"
               if meta.get("created") else None),
            v=visibility, e=(title + "\n" + body)[:3500], pid=(pid := cur.var(int)))
        post_id = pid.getvalue()[0]
        if visibility == "content":
            chunker = doc_chunks if kind == "reference" else note_chunks
            for i, ch in enumerate(chunker(body)):
                cur.execute(
                    """INSERT INTO content_chunks (post_id, seq, chunk, embedding)
                       VALUES (:p, :s, :t, VECTOR_EMBEDDING(MINILM USING :t AS DATA))""",
                    p=post_id, s=i, t=ch)
    conn.commit()
    conn.close()
    print(f"obsidian: {new} new, {updated} updated, {unchanged} unchanged"
          + (f", {docs} documents (reference)" if docs else "")
          + (f", {private} kept non-content" if private else ""))


if __name__ == "__main__":
    main()
