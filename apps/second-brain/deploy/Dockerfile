# Hosted MCP server for the Second Brain — serves the brain over HTTP + bearer auth.
# Build context = repo root:  docker build -f deploy/Dockerfile .
FROM python:3.12-slim

WORKDIR /app
# ffmpeg: audio extraction for the /diagram video intake
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*
COPY deploy/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# the agent code (mcp_http reuses mcp_server's tools; db/content do the DB work)
COPY oracle/agent/ ./agent/
# the read-only web UI (served by webui.py from /app/web when UI_ENABLED; dark otherwise)
COPY web/ ./web/
COPY deploy/entrypoint.sh ./entrypoint.sh
RUN chmod +x ./entrypoint.sh

# run unprivileged: the server needs no root. /wallet is pre-created so the
# entrypoint's unpack (BRAIN_WALLET_B64 -> /wallet) still works without it.
RUN useradd --create-home appuser && mkdir -p /wallet && chown -R appuser /app /wallet
USER appuser

WORKDIR /app/agent
ENV PORT=8000
EXPOSE 8000
# Build stamp: pass at deploy time so /health and the overview tool can report which build is
# live (defaults keep a stampless build working, visibly marked "dev"):
#   fly deploy ... --build-arg GIT_SHA=$(git rev-parse --short HEAD) \
#                  --build-arg BUILD_DATE=$(date -u +%Y-%m-%dT%H:%MZ)
ARG GIT_SHA=dev
ARG BUILD_DATE=unknown
ENV BUILD_SHA=$GIT_SHA BUILD_DATE=$BUILD_DATE
# entrypoint unpacks the wallet (BRAIN_WALLET_B64) then runs uvicorn. Other config comes from
# Fly secrets (DB_DSN, DB_USER, APP_PWD, DB_WALLET_PASSWORD, MCP_AUTH_TOKEN).
CMD ["/app/entrypoint.sh"]
