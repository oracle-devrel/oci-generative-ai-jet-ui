"""Read-only WEB UI over the second brain — a browser-facing memory view (graph + search +
wiki reader + feed + health), served from the SAME Fly app as the MCP server.

Why a separate JSON layer at all: /mcp speaks the MCP streamable-HTTP protocol and carries
no CORS, so a browser can't call it directly. This module exposes a small read-only JSON API
(/api/*) plus the static shell (/, /assets/*), wired into mcp_http's Gateway via the same
extension hook the private /diagram routes use. It runs BEFORE auth, so — exactly like
http_ext — it authenticates itself.

Enablement (fail-closed, mirroring mcp_http's auth stance):
  UI_ENABLED=1        turn the UI on (unset -> every path here 404s; the app is unchanged)
  UI_AUTH_TOKEN=...   >=32-char bearer; every /api/* call must send `Authorization: Bearer <it>`
  UI_PUBLIC_READ=1    explicit, deliberate anonymous read (no token) — for a public showcase
                      deploy only; defensible because the API is read-only and every query is
                      already limited to visibility='content'. Never a default.
  UI_TITLE=...        display name surfaced via /api/ping (default "Second Brain")
UI_ENABLED with neither UI_AUTH_TOKEN nor UI_PUBLIC_READ refuses to start — no open data door.

The static shell (/, /assets/*) is served WITHOUT auth: it contains zero brain data, only the
app that then asks for the token. All content flows through /api/*, which is gated.
"""
import hmac
import json
import os
import pathlib

from starlette.responses import FileResponse, JSONResponse, Response

import db
import content
import memory
import semantic_memory
import conversation
import procedural
import registry
import mcp_server as _srv   # reuse the tools' helpers so the UI pages identically to MCP

ENABLED = os.environ.get("UI_ENABLED") == "1"
UI_TOKEN = os.environ.get("UI_AUTH_TOKEN")
PUBLIC_RO = os.environ.get("UI_PUBLIC_READ") == "1"
UI_TITLE = os.environ.get("UI_TITLE", "Second Brain")

# FAIL CLOSED — the same discipline as mcp_http: no accidental open data door.
if ENABLED and not UI_TOKEN and not PUBLIC_RO:
    raise SystemExit(
        "UI_ENABLED=1 but no access configured — set UI_AUTH_TOKEN (a >=32-char bearer) "
        "or, for a deliberately public read-only showcase, UI_PUBLIC_READ=1. Refusing to "
        "serve brain data with no gate.\n  python3 -c \"import secrets; print(secrets.token_urlsafe(32))\"")
if UI_TOKEN and len(UI_TOKEN) < 32:
    raise SystemExit("UI_AUTH_TOKEN is too short (min 32 chars). Generate one:  "
                     "python3 -c \"import secrets; print(secrets.token_urlsafe(32))\"")

HERE = pathlib.Path(__file__).resolve().parent
# Docker copies web/ to /app/web (HERE=/app/agent); locally it's <repo>/web (HERE=<repo>/oracle/agent).
WEB_DIR = next((p for p in (HERE.parent / "web", HERE.parent.parent / "web",
                            HERE.parent.parent.parent / "web") if p.is_dir()), None)

_ALLOWED_EXT = {".html", ".js", ".css", ".svg", ".png", ".woff2", ".ico", ".webmanifest"}


def _authorized(request):
    """True if this /api request may proceed. Public-read mode lets anyone in; otherwise the
    bearer token must match exactly (constant-time — no timing oracle)."""
    if PUBLIC_RO:
        return True
    if not UI_TOKEN:
        return False
    return hmac.compare_digest(request.headers.get("authorization") or "", f"Bearer {UI_TOKEN}")


# Structural back-stop for the whole XSS class: even if an escaping bug slips into the JS,
# the browser refuses inline/foreign scripts. Everything the UI needs is same-origin (the
# vendored graph lib included); inline style *attributes* are used by index.html, so styles
# allow unsafe-inline — the win is blocking inline SCRIPT, which stays 'self'-only.
_SEC_HEADERS = {
    "Content-Security-Policy": (
        "default-src 'none'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; connect-src 'self'; font-src 'self'; "
        "frame-ancestors 'none'; base-uri 'none'; form-action 'none'"
    ),
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
}


def _static(path):
    """Serve the static shell. Traversal-guarded: the resolved file must live under WEB_DIR and
    carry an allowlisted extension. Returns a Response, or None if there's nothing to serve."""
    if WEB_DIR is None:
        return None
    base = WEB_DIR.resolve()
    rel = "index.html" if path == "/" else path.lstrip("/")   # "/assets/app.js" -> "assets/app.js"
    target = (base / rel).resolve()
    if not target.is_relative_to(base) or not target.is_file():   # blocks ../ escapes
        return None
    if target.suffix.lower() not in _ALLOWED_EXT:
        return None
    # The app files (html/js/css) change on every redeploy and share a stable URL, so they must
    # revalidate — otherwise a redeploy serves stale UI for up to the max-age. Only the vendored,
    # version-pinned lib under assets/vendor/ is safe to cache long.
    long_cache = "/vendor/" in ("/" + rel)
    cache = "public, max-age=604800, immutable" if long_cache else "no-cache"
    return FileResponse(target, headers={"Cache-Control": cache, **_SEC_HEADERS})


def _json(data, status=200):
    return Response(json.dumps(data, default=str), status_code=status,
                    media_type="application/json", headers=_SEC_HEADERS)


def _err(msg, status):
    return _json({"error": msg}, status)


# ---- API handlers. Each owns its connection; DB failures log server-side and return a
# sanitized 503 (never raw ORA text) — same rule as the MCP tools' _unavailable. ----

def _q(request, name, default=None):
    return request.query_params.get(name, default)


def _api(request):
    path = request.url.path
    conn = None
    try:
        if path == "/api/ping":
            return _json({"ok": True, "auth": "public" if PUBLIC_RO else "token", "title": UI_TITLE})
        if path == "/api/agents":
            return _json(registry.registry())   # static catalog; no DB needed
        conn = db.connect()
        if path == "/api/graph":
            return _json(content.graph_data(conn))
        if path == "/api/related":
            rid = _q(request, "id")
            if not rid:
                return _err("id is required", 400)
            try:
                kind, key = _srv._parse_id(rid)
            except (ValueError, TypeError):
                return _err("bad id — use 'item:<post_id>', 'wiki:<topic>', or a bare id", 400)
            k = _srv._clampk(_q(request, "k"), 8, hi=25)
            rows = (content.related_topics(conn, key, k) if kind == "wiki"
                    else content.related_posts(conn, key, k))
            links = [{"source": str(rid), "target": f"item:{r['post_id']}", "type": "semantic",
                      "similarity": round(1.0 - float(r["dist"]), 3)} for r in rows]
            nodes = [{"id": f"item:{r['post_id']}", "type": "item",
                      "label": r["title"] or f"item {r['post_id']}", "platform": r["platform_id"],
                      "kind": r["kind"], **({"series": r["series"]} if r.get("series") else {})}
                     for r in rows]
            return _json({"anchor": str(rid), "nodes": nodes, "links": links})
        if path == "/api/search":
            query = _q(request, "q", "")
            if not query.strip():
                return _json({"results": []})
            k = _srv._clampk(_q(request, "k"), 8, hi=25)
            deduped = _srv._dedup_hits(content.search_hybrid(conn, query, max(k * 2 + 4, 20)))
            return _json({"results": [_srv._fmt_hit(rid, r) for rid, r in deduped[:k]]})
        if path == "/api/wiki":
            topic = _q(request, "topic")
            if not topic:
                return _err("topic is required", 400)
            page = content.get_wiki_page(conn, topic)
            if not page:
                return _err(f"no wiki page for {topic!r}", 404)
            page["body"] = _srv._cap(page["body"])
            return _json(page)
        if path == "/api/topics":
            return _json(content.list_topics(conn))
        if path == "/api/item":
            try:
                pid = int(_q(request, "id", ""))
            except (TypeError, ValueError):
                return _err("id must be a post id", 400)
            post = content.get_post(conn, pid)
            if not post:
                return _err("no such item", 404)
            post["caption"] = _srv._cap(post.get("caption"))
            return _json(post)
        if path == "/api/recent":
            k = _srv._clampk(_q(request, "k"), 10, hi=50)
            with conn.cursor() as cur:
                cur.execute("SELECT post_id, platform_id, kind, title, url, "
                            "TO_CHAR(published_at,'YYYY-MM-DD') AS published FROM posts "
                            "WHERE published_at IS NOT NULL AND NVL(visibility,'content')='content' "
                            "ORDER BY published_at DESC FETCH FIRST :k ROWS ONLY", k=k)
                cols = [c[0].lower() for c in cur.description]
                return _json([dict(zip(cols, row)) for row in cur.fetchall()])
        if path == "/api/series":
            name = _q(request, "name")
            if not name:
                return _json({"available": content.list_series(conn)})
            k = _srv._clampk(_q(request, "k"), 25, hi=50)
            return _json({"series": name, "items": content.list_by_series(conn, name, k)})
        if path == "/api/overview":
            ov = content.stats(conn)
            ov["memory"] = memory.memory_counts(conn)   # counts for the memory tiles
            return _json(ov)
        if path == "/api/memory":
            # The agent's "experience" layer, four kinds, all content-scope (episodic +
            # conversational are visibility-filtered; semantic + procedural carry no private
            # data). Business-tagged memories are excluded at the query layer, never here.
            facts = semantic_memory.list_facts(conn, _srv._clampk(_q(request, "facts"), 200, hi=500))
            episodic = memory.list_recent(conn, _srv._clampk(_q(request, "episodic"), 25, hi=100))
            for e in episodic:                         # cap the CLOB action text for the browser
                e["action"] = _srv._cap(e.get("action"))
            return _json({
                "counts": memory.memory_counts(conn),
                "facts": facts,
                "episodic": episodic,
                "tools": procedural.list_tools(conn),
                "conversational": conversation.list_recent_turns(
                    conn, _srv._clampk(_q(request, "turns"), 12, hi=50)),
            })
        if path == "/api/status":
            return _json(_srv._source_status_data(conn))
        return _err("not found", 404)
    except Exception as e:
        print(f"[webui] {path} {e}", flush=True)
        return _err("the second brain is temporarily unreachable — try again shortly", 503)
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass


async def maybe_handle(request, rate_limit_ok):
    """Extension-hook entry point (same signature as http_ext.maybe_handle). Returns None for
    any path this module doesn't own, so the public gateway continues. Owns /, /assets/*, /api/*
    only when UI_ENABLED — never touches /mcp, /health, /ready, or the OAuth metadata routes."""
    if not ENABLED:
        return None
    path = request.url.path
    if path == "/" or path.startswith("/assets/"):
        return _static(path)   # static shell: unauthenticated (holds no data), None -> 404 upstream
    if path.startswith("/api/"):
        if request.method not in ("GET", "HEAD"):
            return _err("method not allowed", 405)
        # rate-limit BEFORE auth so failed token guesses are metered too
        if not rate_limit_ok():
            return _err("rate limited — slow down", 429)
        if not _authorized(request):
            return _err("unauthorized", 401)
        return _api(request)
    return None
