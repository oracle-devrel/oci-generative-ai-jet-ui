#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
if [ ! -x .venv/bin/python ]; then
  UV_CACHE_DIR="${TMPDIR:-/tmp}/hf-uv-cache" uv venv --python 3.13 .venv
fi
UV_CACHE_DIR="${TMPDIR:-/tmp}/hf-uv-cache" uv pip install --python .venv/bin/python -r requirements.txt
.venv/bin/python scripts/local_env.py
if [ ! -f models/embed.zip ] && [ ! -f models/all_MiniLM_L12_v2.onnx ]; then
  curl -fL --retry 2 'https://adwc4pm.objectstorage.us-ashburn-1.oci.customer-oci.com/p/TtH6hL2y25EypZ0-rrczRZ1aXp7v1ONbRBfCiT-BDBN8WLKQ3lgyW6RxCfIFLdA6/n/adwc4pm/b/OML-ai-models/o/all_MiniLM_L12_v2_augmented.zip' -o models/embed.zip
fi
.venv/bin/python scripts/bootstrap.py
