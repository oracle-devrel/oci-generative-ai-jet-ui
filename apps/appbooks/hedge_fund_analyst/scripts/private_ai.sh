#!/bin/bash
# Deferred component: this script requires Oracle registry login and valid local TLS files.
set -euo pipefail
cd "$(dirname "$0")/.."
docker pull container-registry.oracle.com/database/private-ai:medium-cpu-infer-latest
model_path=models/qwen2.5-3b-instruct-q4_k_m.gguf
if [ ! -f "$model_path" ]; then
  curl -fL --retry 2 -C - 'https://huggingface.co/Qwen/Qwen2.5-3B-Instruct-GGUF/resolve/main/qwen2.5-3b-instruct-q4_k_m.gguf' -o "$model_path.part"
  mv "$model_path.part" "$model_path"
fi
if [ ! -f var/privateai-secrets/keystore ] || [ ! -f var/privateai-secrets/privateai-ssl-pwd ] || [ ! -f var/privateai-secrets/api-key ]; then
  echo 'Configure TLS with Oracle secretsSetup.sh; place keystore, privateai-ssl-pwd and api-key in var/privateai-secrets. Set PRIVATE_AI_CA_FILE and PRIVATE_AI_API_KEY in .env.'
  exit 1
fi
docker compose --profile private-ai up -d private-ai
printf '%s\n' 'Verify /v1/models and a chat completion before claiming Private AI Services is running.'
