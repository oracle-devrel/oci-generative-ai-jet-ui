"""Ingest a registered repository: chunk its files and replace the index in one transaction, in full or for
what changed since the last run.
"""

import json
import logging
import time
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from pathlib import Path, PurePosixPath

import oracledb

from golestan_code_mcp.config import environment
from golestan_code_mcp.indexing import files as indexing_files
from golestan_code_mcp.indexing import write
from golestan_code_mcp.indexing.files import IngestError
from golestan_code_mcp.memory import consolidate
from golestan_code_mcp.memory.consolidate import Consolidation
from golestan_code_mcp.parsing import chunks as parsing_chunks
from golestan_code_mcp.parsing import tables
from golestan_code_mcp.registry import get_repo
from golestan_code_mcp.search import model
from golestan_code_mcp.wiki import build as wiki_build
from golestan_code_mcp.wiki.build import Refresh

log = logging.getLogger("golestan_code_mcp.ingest")

@dataclass
class Summary:
    repo: str
    commit: str
    dirty: bool
    skipped: Counter
    files: int
    no_grammar: int
    parse_errors: int
    symbols: int
    seconds: float
    mode: str = "full"  # full, incremental, or current (already up to date, nothing written)
    added: int = 0
    changed: int = 0
    removed: int = 0
    unchanged: int = 0
    note: str | None = None  # why a run without --full rebuilt in full
    wiki: Refresh | None = None  # the pages this run marked stale and recompiled; None without a wiki
    memory: Consolidation | str | None = None  # what consolidation did, or why it failed (010 FR-014)
    # unchanged files read again only because their language gained rules, by new language (012 FR-016)
    reparsed: Counter = field(default_factory=Counter)

    @property
    def scanned(self) -> int:
        return self.files + sum(self.skipped.values())


def _lock(cur, name: str, repo_id: int) -> tuple[str | None, bool | None, int | None, dict[str, tuple[str, str]]]:
    """Lock the repository row; return its recorded revision, dirty flag, extract version and path to (hash,
    language) map."""
    try:
        cur.execute("select id from ccctx_repos where id = :i for update nowait", i=repo_id)
    except oracledb.DatabaseError as e:
        if getattr(e.args[0], "full_code", "") == "ORA-00054":
            raise IngestError(f"another ingest of '{name}' is running") from None
        raise
    recorded, was_dirty, version = cur.execute(
        "select indexed_commit, indexed_dirty, extract_version from ccctx_repos where id = :i", i=repo_id).fetchone()
    stored = {path: (digest, language) for path, digest, language in cur.execute(
        "select path, content_hash, language from ccctx_files where repo_id = :i", i=repo_id)}
    return recorded, was_dirty, version, stored


def _full_reason(root: Path, name: str, recorded: str | None, stored: dict) -> tuple[bool, str | None]:
    """Whether an ingest without --full must rebuild in full, and the note saying why."""
    if recorded is None:
        return True, f"no recorded revision for '{name}'; indexing in full" if stored else None
    try:
        indexing_files.git(root, "rev-parse", "--verify", "--quiet", f"{recorded}^{{commit}}")
    except IngestError:
        return True, f"last indexed revision {recorded[:12]} is no longer in the repository; indexing in full"
    return False, None


def _candidates(root: Path, recorded: str, was_dirty: bool) -> tuple[list[str], set[str]]:
    """Paths that may differ from the index, and every path git lists now."""
    listed = set(indexing_files._ls(root, "--cached", "--others", "--exclude-standard"))
    if was_dirty:  # an uncommitted edit was indexed: git cannot tell whether it was reverted since
        return sorted(listed), listed
    changed = indexing_files._paths(root, "diff", "--name-only", "-z", "--no-renames", recorded, "--")
    untracked = indexing_files._ls(root, "--others", "--exclude-standard")
    return sorted(set(changed + untracked) & listed), listed


def _prepare(files: dict[str, str]) -> tuple[list[tuple], int, int]:
    prepared, no_grammar, parse_errors = [], 0, 0
    for rel, text in sorted(files.items()):
        language = parsing_chunks.detect_language(rel)
        parsed = parsing_chunks.parse(language, text)
        if parsed is None:  # line windows have no calls or imports
            if language in tables.GRAMMARS:
                parse_errors += 1
            else:
                no_grammar += 1
            parsed = parsing_chunks.windows(PurePosixPath(rel).name, text), [], [], None, []
        prepared.append((rel, language, text, *parsed))
    return prepared, no_grammar, parse_errors


def ingest(conn, name: str, env: Mapping[str, str] | None = None, full: bool = False) -> Summary:
    """Index what changed since the last ingest, or everything with full=True. One transaction either way."""
    started = time.monotonic()
    env = environment() if env is None else env
    model.require_model(conn)
    repo_id, root = get_repo(conn, name)
    try:
        indexing_files.git(root, "rev-parse", "--is-inside-work-tree")
    except IngestError:
        raise IngestError(f"{root} is not a git repository") from None
    try:
        commit = indexing_files.git(root, "rev-parse", "--verify", "HEAD").strip()
    except IngestError:
        raise IngestError(f"{root} has no commits yet") from None
    dirty = bool(indexing_files.git(root, "status", "--porcelain", "--untracked-files=no").strip())

    with conn.cursor() as cur:
        try:
            recorded, was_dirty, version, stored = _lock(cur, name, repo_id)
            stale = version != write.EXTRACT_VERSION  # refs from older rules, or none: re-read every listed file
            note = None
            if not full:
                full, note = _full_reason(root, name, recorded, stored)
            reparsed = Counter()
            if full:
                files, skipped = indexing_files.discover(root, env)
                delete, removed = None, []
                mode, added, changed, unchanged = "full", len(files), 0, 0
            else:
                candidates, listed = _candidates(root, recorded, bool(was_dirty) or stale)
                # stored under another language than the one it has now: its language gained rules (research R10)
                relanguaged = {rel for rel, (_, lang) in stored.items()
                               if rel in listed and lang != parsing_chunks.detect_language(rel)}
                candidates = sorted(set(candidates) | relanguaged)
                readable, skipped = indexing_files.discover(root, env, candidates)
                # gone from git's listing (deleted, renamed away, newly ignored), or now gone or skipped on disk
                removed = sorted({rel for rel in stored if rel not in listed}
                                 | {rel for rel in candidates if rel in stored and rel not in readable})
                same = {rel for rel, text in readable.items() if rel in stored and stored[rel][0] == write._sha(text)}
                files = {rel: text for rel, text in readable.items() if stale or rel not in same or rel in relanguaged}
                reparsed = Counter(parsing_chunks.detect_language(rel) for rel in files
                                   if rel in same and rel in relanguaged)
                changed = sum(rel in stored for rel in files)
                added, unchanged = len(files) - changed, len(stored) - changed - len(removed)
                delete = removed
                current = not stale and commit == recorded and not files and not removed and bool(was_dirty) == dirty
                mode = "current" if current else "incremental"
            prepared, no_grammar, parse_errors = _prepare(files)
            has_wiki = mode != "current" and wiki_build.enabled(cur, repo_id)
            if mode == "current":
                conn.rollback()  # nothing to write; releases the lock
                symbols = 0
            else:
                symbols = write._write(cur, repo_id, commit, dirty, prepared, delete,
                                       set() if delete is None else stored.keys() & files.keys())
                # in this transaction, so no reader sees the new code beside a page called fresh
                marked = wiki_build.mark_stale(cur, repo_id) if has_wiki else []
                conn.commit()
        except BaseException:
            conn.rollback()
            raise
    # after the commit and in its own transaction, so a wiki failure cannot cost the ingestion (FR-012)
    pages = replace(wiki_build.refresh(conn, repo_id), stale=marked) if has_wiki else None
    # every ingestion consolidates, after its commit and on its own, so a failure cannot cost the ingestion
    try:
        remembered = consolidate.consolidate(conn, name, env)[0]
    except Exception as e:  # noqa: BLE001 - reported in the summary, never raised
        conn.rollback()
        remembered = str(e) or type(e).__name__

    summary = Summary(name, commit, dirty, skipped, len(files), no_grammar, parse_errors, symbols,
                      round(time.monotonic() - started, 1), mode, added, changed, len(removed), unchanged, note, pages,
                      remembered, reparsed)
    log.info(json.dumps({
        "event": "ingest", "repo": name, "commit": commit, "dirty": dirty, "scanned": summary.scanned,
        "skipped": dict(skipped), "files": summary.files, "no_grammar": no_grammar,
        "parse_errors": parse_errors, "symbols": symbols, "seconds": summary.seconds,
        "mode": mode, "added": added, "changed": changed, "removed": len(removed), "unchanged": unchanged,
        "reparsed": dict(reparsed),
    }))
    return summary
