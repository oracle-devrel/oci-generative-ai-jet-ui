#!/usr/bin/env bash
# Download Oracle's prebuilt augmented all-MiniLM-L12-v2 ONNX model into oracle/models/.
# Resolves Oracle's CURRENT download link at runtime (the pre-authenticated URLs rotate,
# so we follow the stable docs redirect instead of hard-coding a link).
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p models

if [ -f models/all_MiniLM_L12_v2.onnx ]; then
  echo "model already present: models/all_MiniLM_L12_v2.onnx"
  exit 0
fi

echo "resolving current Oracle model index..."
INDEX=$(curl -fsSL -o /dev/null -w '%{url_effective}' \
  "https://docs.oracle.com/pls/topic/lookup?ctx=en/database/oracle/oracle-database/26/vecse&id=oml_ai_models_object_storage")

echo "finding the MiniLM model link..."
ZIP=$(curl -fsSL "$INDEX" | grep -oE 'https://[^"]*all_MiniLM_L12_v2_augmented\.zip' | head -1)
if [ -z "${ZIP:-}" ]; then
  echo "Could not resolve the model URL automatically."
  echo "Download the augmented all_MiniLM_L12_v2 ONNX model from Oracle's docs and place"
  echo "the .onnx file at oracle/models/all_MiniLM_L12_v2.onnx — see setup/01_load_onnx_model.sql"
  exit 1
fi

echo "downloading model (~120MB)..."
curl -fsSL "$ZIP" -o models/all_MiniLM_L12_v2_augmented.zip
unzip -o models/all_MiniLM_L12_v2_augmented.zip -d models >/dev/null

# Integrity check: this file gets loaded INTO your database (dbms_vector.load_onnx_model),
# so verify it's the exact model this repo was built and tested against — not whatever a
# compromised mirror/redirect happened to serve. If Oracle publishes a new model version,
# verify it deliberately, then update this pin.
EXPECTED_SHA256="3929907d138051f818619fce3ba054185f748f2739d7a4dbc26e2502dd2499ea"
ACTUAL_SHA256=$( (shasum -a 256 models/all_MiniLM_L12_v2.onnx 2>/dev/null || sha256sum models/all_MiniLM_L12_v2.onnx) | awk '{print $1}')
if [ "$ACTUAL_SHA256" != "$EXPECTED_SHA256" ]; then
  echo "ERROR: model checksum mismatch — refusing to keep it."
  echo "  expected: $EXPECTED_SHA256"
  echo "  actual:   $ACTUAL_SHA256"
  echo "If Oracle released a new model version, verify it from their docs, then update"
  echo "EXPECTED_SHA256 in this script. (Override once with MODEL_SHA256_SKIP=1 if you"
  echo "have independently verified the file.)"
  if [ "${MODEL_SHA256_SKIP:-}" != "1" ]; then
    rm -f models/all_MiniLM_L12_v2.onnx models/all_MiniLM_L12_v2_augmented.zip
    exit 1
  fi
  echo "MODEL_SHA256_SKIP=1 set — keeping unverified file at YOUR risk."
fi
echo "done (checksum verified): models/all_MiniLM_L12_v2.onnx"
