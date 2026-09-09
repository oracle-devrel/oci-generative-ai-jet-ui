# Hosting & Security Architecture (long-term)

How to take the brain from "local on my laptop" to a **hosted, secure, headless** system
that holds a lot of personal content and is reachable from Claude, ChatGPT, and any device —
done with best practices. This started as the target; **the repo now implements the core of
it** (fail-closed OAuth + allowlist, connection pooling, rate limiting, read/write tool
scoping — see `oracle/agent/mcp_http.py` and [SECURITY.md](../SECURITY.md)). Kept as the map
of the full posture.

## Target shape

```
  SOURCES                INGESTION (scheduled)            BRAIN (hosted)
  YouTube, Notion,  ─►   delta pulls + redaction    ─►   Oracle Autonomous DB 26ai
  chats, code,           (jobs / serverless)              · encrypted at rest (TDE)
  Gmail→Notion, ...      least-priv writer user           · mTLS wallet, private endpoint
                                                           · auto-backup + PITR
                                                                   ▲
                                                                   │ mTLS, least-priv user
  CLIENTS                       ACCESS LAYER                        │
  Claude desktop/web/mobile ─►  Hosted MCP server  ────────────────┘
  ChatGPT, phone            (HTTPS + OAuth/bearer)  FastMCP / Streamable HTTP
       (per-user token,      read vs write scopes   pooled connections, rate-limited,
        revocable)           human-in-loop on writes audit-logged
```

The brain is the **single, app-independent source of truth**; the MCP server is the **one
authenticated door** every client uses. No client talks to the DB directly.

## Components & hosting choices

| Component | Recommended | Notes |
|---|---|---|
| **Database** | **Oracle Autonomous Database 26ai** (Always Free to start; scale up later) | managed: encryption, backups, patching, mTLS. Same engine as local. |
| **MCP server** | FastMCP over **Streamable HTTP**, containerized | host on OCI compute, Fly.io, or Cloud Run. Implemented here: `oracle/agent/mcp_http.py` + [HOSTED_MCP.md](HOSTED_MCP.md). |
| **Ingestion/sync** | scheduled jobs (cron / serverless / a small worker) | per-source delta pulls + redaction. Implemented here: `scripts/sync.py` (LaunchAgent-ready). |
| **Secrets** | a secrets manager (OCI Vault / Fly secrets / cloud KMS) | NOT `.env` files on the server. |

**Two clean deployment patterns:**
1. **All-OCI:** Autonomous DB + OCI container instance for the MCP server, on a private VCN —
   the DB has a **private endpoint**, only the MCP server can reach it. Most locked-down.
2. **Hybrid:** Autonomous DB (OCI) + MCP server on Fly.io/Cloud Run. Restrict DB access with an
   **access-control list** (only the MCP host's egress IPs) + mTLS wallet. Simpler MCP hosting.

## Security best practices (the core)

**Authentication & authorization**
- MCP endpoint requires auth — **OAuth 2.1** (the MCP spec direction) or bearer tokens to start,
  with **scopes**: `read:brain` vs `write:brain`. Per-client, **revocable, rotated** tokens.
- The DB user the MCP server uses is a **least-privilege app user** (not `ADMIN`/`SYSTEM`) — read +
  only the writes it needs. Read-only clients get a read-only user.

**Transport & encryption**
- **TLS everywhere** (HTTPS for the MCP endpoint; mTLS wallet for the DB).
- **Encryption at rest** is on by default in Autonomous DB (TDE).

**Secrets management**
- Never in code/repo (already enforced: `.env`, `private/`, wallets are gitignored).
- In production use a **secrets manager**; mount secrets at runtime, don't bake into images.
- **Rotate** all keys (DB, Anthropic, Notion, MCP tokens) on a schedule and on any exposure.

**Data protection / minimization (critical — this holds personal content)**
- **Redact secrets on ingestion** (already done for chats/code) — keep doing it for every source.
- **Minimize**: ingest summaries/curated data, not raw dumps; keep financials/PII/contacts OUT of
  embeddings (as done for brand deals — brand+status only, no rates/contacts).
- **Scope sensitive sources** (e.g., email → only deal/sponsorship threads, never the whole inbox).
- Keep the most sensitive data **local** if you don't need it remote.

**Network**
- DB is **never publicly exposed** — private endpoint or ACL limited to the MCP host.
- MCP server runs **least-privilege**, restricted egress.

**Prompt-injection safety (LLM-specific, often missed)**
- Retrieved content (chats, web, emails) is **untrusted data, not instructions** — the agent/MCP
  must not let returned text override system instructions.
- **Write tools are gated**: `ingest_note` is additive/low-risk; anything destructive or external
  (e.g., updating Notion) is **human-in-the-loop** (suggest → you approve), idempotent, logged.

**Audit, monitoring, durability**
- **Audit-log every MCP tool call** (who/what/when) — the brain already has a memory/audit pattern.
- **Rate-limit** the MCP endpoint; alert on failures (failures-only notifications).
- **Backups**: Autonomous auto-backup + point-in-time recovery; also keep the canonical `sources/`.

## The MCP server, "done well"
- OAuth/bearer **auth seam** (start bearer, grow to OAuth) with read/write **scopes**.
- **Connection pooling** (hot session pool) instead of per-call connect.
- **Token-efficient responses**: `search` returns snippets → `fetch` pulls detail on demand.
- **Prescriptive tool descriptions** (tell the model *when* to call each).
- **Rate limiting + health checks + structured logging/tracing**.
- **Containerized + infrastructure-as-code** so it's reproducible and versioned.

## Migration path (local → hosted), phased
1. **Now (local):** keep building features on local Oracle (fast iteration).
2. **Cloud DB:** provision Autonomous DB (Always Free); migrate schema + reload (or `DBMS_CLOUD`
   data move); load the ONNX model from object storage; point the app at the wallet.
3. **Hosted MCP:** containerize the MCP server with **bearer auth + pooling + rate limits**; deploy;
   lock DB access to the MCP host; store secrets in a secrets manager.
4. **Connect clients:** Claude (web/mobile) + ChatGPT via the hosted MCP URL + token.
5. **Harden:** OAuth, audit logging, alerting, rotation schedule, private endpoint.

> Single-user system → simpler than multi-tenant, but the same fundamentals apply: authenticate
> the one user, least-privilege everything, encrypt, redact, gate writes, audit, rotate.
