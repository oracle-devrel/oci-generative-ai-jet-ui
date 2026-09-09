"""Hosted MCP server — the same brain tools as mcp_server.py, but over HTTP so Claude (web/mobile),
ChatGPT, or any device can reach the brain over the internet.

It reuses the exact same FastMCP instance + tools from mcp_server.py and connects to whatever
oracle/.env points at (the cloud Autonomous DB). Auth: WorkOS OAuth + allowlist when AUTHKIT_DOMAIN
is set, else an `Authorization: Bearer $MCP_AUTH_TOKEN` header. Open probes:
  GET /health  — shallow liveness (no DB), for the load balancer's fast check
  GET /ready   — readiness: actually touches the DB (SELECT 1), 200 if reachable else 503

Run locally:
  MCP_AUTH_TOKEN=$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))') \\
      ../../.venv/bin/uvicorn mcp_http:app --host 0.0.0.0 --port 8000
Deploy: see docs/HOSTED_MCP.md (Dockerfile + Fly.io).
"""
import hmac
import os
import threading
import time

from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

import db                       # noqa: E402
from mcp_server import mcp   # same FastMCP server + all tools (see mcp_server.py's registry)

TOKEN = os.environ.get("MCP_AUTH_TOKEN")

# FAIL CLOSED: a hosted brain must never start without auth. OAuth (AUTHKIT_DOMAIN) or a bearer
# token (MCP_AUTH_TOKEN) — one of them is required. MCP_ALLOW_ANON=1 is an explicit, deliberate
# escape hatch for local experiments only (never set it on a public deployment).
if (not os.environ.get("AUTHKIT_DOMAIN") and not TOKEN
        and os.environ.get("MCP_ALLOW_ANON") != "1"):
    raise SystemExit(
        "refusing to start with NO auth configured — set AUTHKIT_DOMAIN (OAuth) or "
        "MCP_AUTH_TOKEN (bearer), or MCP_ALLOW_ANON=1 for a local-only experiment.")

# ...and the escape hatch itself refuses on a real deployment: a copied-over env var must
# not silently serve the brain with no auth on a public host.
if os.environ.get("MCP_ALLOW_ANON") == "1" and os.environ.get("FLY_APP_NAME"):
    raise SystemExit("MCP_ALLOW_ANON=1 is local-only — refusing on a Fly deployment "
                     "(unset it and configure AUTHKIT_DOMAIN or MCP_AUTH_TOKEN).")

# a bearer token on a public URL must not be guessable: enforce a floor when it is the
# only auth. NOTE: bearer is mounted ONLY when AUTHKIT_DOMAIN is unset — with OAuth on,
# MCP_AUTH_TOKEN authenticates nothing (fails closed; don't rely on it for API clients).
if TOKEN and not os.environ.get("AUTHKIT_DOMAIN") and len(TOKEN) < 32:
    raise SystemExit(
        "MCP_AUTH_TOKEN is too short for a public deployment (min 32 chars). "
        "Generate one:  python3 -c \"import secrets; print(secrets.token_urlsafe(32))\"")


def _keep_warm():
    """Periodically run an embedding so the Always-Free Autonomous DB doesn't idle out and the
    in-DB ONNX model stays resident — the first real query skips the cold path. Acquires and
    RELEASES a connection each cycle (with pooling on, holding one forever would hog a pool slot)."""
    interval = int(os.environ.get("KEEP_WARM_SECONDS", "240"))
    while True:
        conn = None
        try:
            conn = db.connect()
            with conn.cursor() as cur:
                cur.execute("SELECT VECTOR_EMBEDDING(MINILM USING 'warm' AS DATA) FROM dual").fetchone()
        except Exception:
            pass
        finally:
            if conn is not None:
                try:
                    conn.close()
                except Exception:
                    pass
        time.sleep(interval)


if os.environ.get("KEEP_WARM", "1") == "1":
    threading.Thread(target=_keep_warm, daemon=True).start()


_READY_CACHE = {"at": 0.0, "ok": False}   # /ready is unauthenticated — cache so it can't be
_READY_TTL = 10.0                          # hammered to hold DB pool slots (cheap DoS guard)


def _readiness():
    """Deep health: prove the DB link actually works so the platform can route away from a wedged
    machine. Result cached ~10s (the probe is open to the internet; uncached, a request loop could
    monopolize the small connection pool). No error detail in the body — don't leak internals."""
    now = time.monotonic()
    if now - _READY_CACHE["at"] < _READY_TTL:
        return JSONResponse({"ready": _READY_CACHE["ok"]},
                            status_code=200 if _READY_CACHE["ok"] else 503)
    conn = None
    try:
        conn = db.connect()
        conn.cursor().execute("SELECT 1 FROM dual").fetchone()
        _READY_CACHE.update(at=now, ok=True)
        return JSONResponse({"ready": True})
    except Exception as e:
        print(f"[ready] DB check failed: {e}", flush=True)
        _READY_CACHE.update(at=now, ok=False)
        return JSONResponse({"ready": False}, status_code=503)
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass


class _Bucket:
    """Token-bucket rate limiter, PER CLIENT IP (MCP spec: servers MUST rate-limit tool
    invocations). Per-IP so one misbehaving client throttles only itself, never the owner —
    plus a global backstop that protects the database no matter how many IPs attack.
    Not distributed (per-machine), which is fine at this scale."""

    MAX_IPS = 10_000   # memory backstop; oldest buckets evicted beyond this

    def __init__(self, burst=30, per_sec=5.0):
        self.capacity = float(os.environ.get("RATE_BURST", burst))
        self.rate = float(os.environ.get("RATE_PER_SEC", per_sec))
        # global backstop: generous multiple of the per-IP rate
        self.gcapacity = self.capacity * 4
        self.grate = self.rate * 4
        self.gtokens, self.gat = self.gcapacity, time.monotonic()
        self.ips = {}          # ip -> [tokens, last_refill]
        self.lock = threading.Lock()

    def allow(self, ip="?"):
        with self.lock:
            now = time.monotonic()
            # global backstop first
            self.gtokens = min(self.gcapacity, self.gtokens + (now - self.gat) * self.grate)
            self.gat = now
            if self.gtokens < 1.0:
                return False
            # per-IP bucket
            b = self.ips.get(ip)
            if b is None:
                if len(self.ips) >= self.MAX_IPS:   # evict stalest
                    oldest = min(self.ips, key=lambda k: self.ips[k][1])
                    del self.ips[oldest]
                b = self.ips[ip] = [self.capacity, now]
            b[0] = min(self.capacity, b[0] + (now - b[1]) * self.rate)
            b[1] = now
            if b[0] >= 1.0:
                b[0] -= 1.0
                self.gtokens -= 1.0
                return True
            return False


def _client_ip(request):
    """Real client IP behind Fly's proxy. Fly sets Fly-Client-IP; fall back to the first
    X-Forwarded-For hop, then the socket peer. Never trust these for auth — only for
    fairness bucketing (worst case a spoofer gets its own bucket)."""
    return (request.headers.get("fly-client-ip")
            or (request.headers.get("x-forwarded-for", "").split(",")[0].strip() or None)
            or (request.client.host if request.client else "?"))


_bucket = _Bucket()

import webui as _WEBUI      # read-only web UI (static shell + /api/*); dark unless UI_ENABLED

try:                       # optional private HTTP routes (never present in the public repo)
    import http_ext as _HTTP_EXT
except ImportError:
    _HTTP_EXT = None


class Gateway(BaseHTTPMiddleware):
    """Outermost middleware: serve the open probes, rate-limit, and time/log tool traffic.
      /health -> shallow 200 (no DB)      /ready -> deep DB check (cached ~10s)
    Because this runs before auth, /health and /ready stay open in BOTH auth modes; everything
    else falls through to the auth layer. /mcp calls are timed and logged (path + status + latency,
    never query text / note bodies — no PII)."""

    async def dispatch(self, request, call_next):
        path = request.url.path
        if path == "/health":
            return JSONResponse({"ok": True})
        if path == "/ready":
            return _readiness()
        # Read-only web UI (static shell + /api/*). Like http_ext it runs BEFORE auth and
        # self-authenticates every /api/* call; returns None for paths it doesn't own. Dark
        # (returns None for everything) unless UI_ENABLED. Owns /, /assets/*, /api/* — never
        # /mcp, /health, /ready, or the OAuth metadata routes.
        _ui = await _WEBUI.maybe_handle(request, lambda: _bucket.allow(_client_ip(request)))
        if _ui is not None:
            return _ui
        if _HTTP_EXT is not None:
            # Extension hook: private routes (see http_ext in your private deploy) get first
            # look at the request; None means "not mine" and the public gateway continues.
            # SECURITY: this runs BEFORE rate limiting and BEFORE BearerAuth/OAuth — any
            # route an extension handles is served with NO auth unless the extension
            # authenticates it itself. Every http_ext route MUST self-auth (check its own
            # token/OAuth) and should call the passed rate_limit callback.
            _ip = _client_ip(request)
            ext_resp = await _HTTP_EXT.maybe_handle(request, lambda: _bucket.allow(_ip))
            if ext_resp is not None:
                return ext_resp
        if path.startswith("/mcp") and not _bucket.allow(_client_ip(request)):
            return JSONResponse({"error": "rate limited — slow down"}, status_code=429)
        start = time.monotonic()
        resp = await call_next(request)
        if path.startswith("/mcp"):
            ms = int((time.monotonic() - start) * 1000)
            print(f"[mcp] {request.method} {path} -> {resp.status_code} {ms}ms", flush=True)
        return resp


class BearerAuth(BaseHTTPMiddleware):
    """Require `Authorization: Bearer <MCP_AUTH_TOKEN>`. Only mounted when WorkOS OAuth is off;
    open probes are already handled by Gateway (outer), so this only ever sees protected paths.
    compare_digest = constant-time comparison (no timing oracle on the token)."""

    async def dispatch(self, request, call_next):
        if TOKEN:
            supplied = request.headers.get("authorization") or ""
            if not hmac.compare_digest(supplied, f"Bearer {TOKEN}"):
                return JSONResponse({"error": "unauthorized"}, status_code=401)
        return await call_next(request)


# When AUTHKIT_DOMAIN is set, FastMCP's WorkOS OAuth (+ allowlist) protects /mcp; otherwise the
# bearer-token middleware does. Gateway is outermost, so /health + /ready stay open in both.
# stateless_http=True: no in-memory session affinity, so tool calls work across multiple Fly
# machines (otherwise a call can land on a machine without the connect-time session).
_mw = [Middleware(Gateway)]
if not os.environ.get("AUTHKIT_DOMAIN"):
    _mw.append(Middleware(BearerAuth))
app = mcp.http_app(middleware=_mw, stateless_http=True)
