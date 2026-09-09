# OCI Generative AI setup

The workshop's runtime LLM is **Grok 4 via OCI Generative AI Inference**. The client is a thin HTTPS wrapper using bearer-token auth — no OCI Python SDK needed.

You need these four env vars in `.env`. The instructor can provide the first three on workshop day, or attendees can use values from their own OCI tenancy. Never commit real values.

```
OCI_GENAI_ENDPOINT=REPLACE_ME_WORKSHOP_DAY_ENDPOINT
OCI_GENAI_API_KEY=sk-REPLACE_ME_WORKSHOP_DAY
OCI_COMPARTMENT_ID=ocid1.compartment.oc1..REPLACE_ME_WORKSHOP_DAY
OCI_GENAI_MODEL_ID=xai.grok-4
```

If you want to stage the values before the event without touching `.env`, put them in a local ignored file such as `.env.workshop.local`, then copy/merge them into `.env` right before verification.

## Where to get each value

1. **OCI_GENAI_ENDPOINT** — Pick the regional endpoint for OCI Generative AI Inference. The instructor can provide the exact endpoint on workshop day. If using your own tenancy, choose the region where Grok is enabled. The URL format is always `https://inference.generativeai.<region>.oci.oraclecloud.com`.

2. **OCI_GENAI_API_KEY** — A bearer key starting with `sk-`. Get it from the OCI Console: **Generative AI** → **API keys** → create one. Save the secret immediately; the console does not show it again. If using instructor-provided shared access, paste the provided key into local `.env` only.

3. **OCI_COMPARTMENT_ID** — The OCID of the compartment that hosts your GenAI workloads. Get it from the OCI Console under **Tenancy** or **Compartments**. Format: `ocid1.compartment.oc1..aaaaaa...`. If using instructor-provided shared access, paste the provided compartment OCID into local `.env` only; do not publish it in docs/slides.

4. **OCI_GENAI_MODEL_ID** — Short model ID. The workshop uses `xai.grok-4`. Other options on OCI today include `xai.grok-3`. Visit OCI Console → Generative AI → Models for the full live catalog in your region.

## Verify

```bash
uv run python scripts/verify.py
```

The last check ("Grok 4") sends a one-word prompt to Grok and expects "pong" in the reply. If you see ✓ next to that line, the endpoint, key, compartment, and model ID are all correct.

## Common failures

| Symptom | Likely cause |
|---|---|
| `401 Unauthorized` | `OCI_GENAI_API_KEY` is wrong, expired, or has a typo (especially missing the `sk-` prefix). |
| `403 Forbidden` | Compartment is correct but the user/tenancy doesn't have access to that specific model. Submit an access request through the OCI Console. |
| `404 Entity not found` | `OCI_GENAI_MODEL_ID` is misspelled or the model is not available in the chosen region. |
| `400 Serving Mode must be provided` | The client built the request without the `servingMode` object — only happens if `grok_client.py` was edited in a breaking way. |

## Embeddings

The workshop does NOT use OCI for embeddings. Embeddings happen **inside Oracle AI Database** via `VECTOR_EMBEDDING(ALL_MINILM_L6_V2 USING :t AS DATA)`. The ONNX model is loaded once at setup time by `scripts/load_onnx_model.py` (uses the `onnx2oracle` Python package).
