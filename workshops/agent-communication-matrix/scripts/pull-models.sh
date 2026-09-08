#!/usr/bin/env bash
# scripts/pull-models.sh
# Pulls the models used by the three patterns. Run once after first compose up.

set -euo pipefail

source .env

echo "Pulling embedding model: ${EMBED_MODEL}"
docker exec ollama ollama pull "${EMBED_MODEL}"

echo "Pulling chat model: ${CHAT_MODEL}"
docker exec ollama ollama pull "${CHAT_MODEL}"

echo "Done. Models available:"
docker exec ollama ollama list
