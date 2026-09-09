# Provision OCI Generative AI for in-database classify + extract

This step registers a credential inside the database so that `DBMS_VECTOR_CHAIN.UTL_TO_GENERATE_TEXT` can call OCI Generative AI (`meta.llama-3.3-70b-instruct` by default) from a SQL statement. After this is done, **field extraction** happens inside the database — no external Bedrock/OpenAI call from your application. (Classification is separate: it uses pure vector search and never calls an LLM.)

Cost: OCI Generative AI is pay-per-use. Only the field-extraction step calls it — one chat request per document — so it costs a fraction of a cent per doc. Classification and embeddings run on vectors inside the database and cost nothing per call.

Takes ~3 minutes.

## 1. Create the API key and grab four of the five values from one screen

OCI console → top-right profile avatar → **My profile**.

You will land on a page with tabs (`Details`, `My groups`, `My requests`, `My resources`, **`Tokens and keys`**, ...). Click **Tokens and keys**.

In the **API keys** section:

1. **Add API key** → **Generate API key pair**.
2. **Download private key** — save to `~/.oci/idp.pem` (or any stable path; you'll point `.env` at it). The public key is uploaded automatically.
3. **Add**.

After the key is added, OCI shows a **configuration file preview** on the same screen. It looks like this:

```ini
[DEFAULT]
user=ocid1.user.oc1..aaaaaaaa....
fingerprint=aa:bb:cc:dd:ee:ff:00:11:22:33:44:55:66:77:88:99
tenancy=ocid1.tenancy.oc1..aaaaaaaa....
region=eu-frankfurt-1
key_file=<path to your private keyfile> # TODO
```

This single block gives you **four of the five values** at once:

| `.env` variable    | Where in the preview                                                             |
| ------------------ | -------------------------------------------------------------------------------- |
| `OCI_USER_OCID`    | `user=...`                                                                       |
| `OCI_FINGERPRINT`  | `fingerprint=...`                                                                |
| `OCI_TENANCY_OCID` | `tenancy=...`                                                                    |
| `OCI_GENAI_REGION` | `region=...` (only if you want a region other than the default `eu-frankfurt-1`) |

The fifth value is the **compartment OCID**. For Always Free / single-user setups, use the **root compartment**, whose OCID is identical to the tenancy OCID. (Multi-team setups: Identity & Security → Compartments → pick a sub-compartment.)

The sixth `.env` line, `OCI_PRIVATE_KEY_PATH`, points at the `.pem` you downloaded in step 2.

Tighten the key's permissions on disk:

```bash
chmod 600 ~/.oci/idp.pem
```

## 3. Populate `.env`

Append to `.env`:

```
OCI_USER_OCID=ocid1.user.oc1..xxxx
OCI_TENANCY_OCID=ocid1.tenancy.oc1..xxxx
OCI_COMPARTMENT_OCID=ocid1.tenancy.oc1..xxxx
OCI_FINGERPRINT=aa:bb:cc:dd:ee:ff:00:11:22:33:44:55:66:77:88:99
OCI_PRIVATE_KEY_PATH=/Users/you/.oci/idp.pem
OCI_GENAI_REGION=eu-frankfurt-1
OCI_GENAI_MODEL=meta.llama-3.3-70b-instruct
```

`OCI_GENAI_REGION` must be a region where OCI Generative AI is enabled. Frankfurt, Chicago, Phoenix, London, and São Paulo all work. The inference endpoint is derived as `https://inference.generativeai.<region>.oci.oraclecloud.com`.

`OCI_GENAI_MODEL` is the chat model ID. It must be a **current, non-retired** model — check OCI console → **Analytics & AI → Generative AI → Playground** for the live list in your region:

| Model                                         | Notes                                                                                                                                                                                   |
| --------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `meta.llama-3.3-70b-instruct`                 | Default in this repo. The model Oracle's own docs use in their `UTL_TO_GENERATE_TEXT` example. Good price and reliable structured JSON for purchase orders / delivery notes / invoices. |
| `cohere.command-a-03-2025`                    | Cohere Command A — the successor to the retired Command R+. Strong on nested schemas (`lineItems[]`).                                                                                   |
| `meta.llama-4-maverick-17b-128e-instruct-fp8` | Newer Llama 4 option if you want to experiment.                                                                                                                                         |

> **Do not use** `cohere.command-r-plus-08-2024` or `cohere.command-r-08-2024`: both are deprecated and scheduled to retire on **2026-07-10** (on-demand). The model must be served in the region in your endpoint URL — verify availability in OCI console → **Analytics & AI → Generative AI**.

Switching is a one-line change in `.env` followed by an API restart — no code changes needed. The same prompt + JSON Schema gets sent to whichever model you point at.

## 4. Register the credential inside the database

```bash
pnpm db:setup-oci-credential
```

This script does three things:

1. As ADMIN: grants `CREATE CREDENTIAL`, `EXECUTE ON DBMS_CLOUD`, `EXECUTE ON DBMS_CLOUD_AI` to the `idp` user, and opens an outbound network ACL to the OCI Generative AI inference host.
2. As `idp`: calls `DBMS_VECTOR_CHAIN.CREATE_CREDENTIAL` to register the credential under the name `OCI_CRED`. The private key is sent with `BEGIN/END` lines stripped.
3. As `idp`: runs a smoke test — `SELECT DBMS_VECTOR_CHAIN.UTL_TO_GENERATE_TEXT('Reply with the single word PONG.', ...) FROM DUAL`. You should see:

   ```
   ✓ response: PONG.
   ```

If the smoke test prints `PONG`, the entire chain (API key → fingerprint → network → credential → model) is correct. The rest of the pipeline now works.

## How `UTL_TO_GENERATE_TEXT` is used

This credential powers exactly one step: **field extraction**. (Classification is done with pure vector search — k-NN over the embeddings — and never touches an LLM.) `packages/db/src/llm.ts` issues a single SQL query:

```sql
SELECT DBMS_VECTOR_CHAIN.UTL_TO_GENERATE_TEXT(
  :prompt,
  JSON('{
    "provider": "ocigenai",
    "credential_name": "OCI_CRED",
    "url": "https://inference.generativeai.eu-frankfurt-1.oci.oraclecloud.com/20231130/actions/chat",
    "model": "meta.llama-3.3-70b-instruct",
    "chatRequest": { "maxTokens": 4096, "temperature": 0 }
  }')
) AS OUT FROM DUAL;
```

`:prompt` is the extracted document text plus the doc-type's JSON Schema (generated from the Zod schema in `@idp/schemas` via `zodToJsonSchema`).

The CLOB returned by the function is parsed in TypeScript and validated against the corresponding Zod schema. On validation failure, `extractFieldsInDb` retries once with the Zod error message fed back into the prompt so the model can self-correct, which catches most cases where the model returns malformed JSON or leaves a required field empty on the first try.

## Troubleshooting

| Symptom                                                  | Cause                                                                                                                                                                                                  |
| -------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `PLS-00201: identifier 'DBMS_CLOUD' must be declared`    | The `idp` user doesn't have `EXECUTE` on `DBMS_CLOUD`. Re-run `pnpm db:setup-oci-credential` — the script grants this before creating the credential.                                                  |
| `PLS-00201: identifier 'DBMS_CLOUD_AI' must be declared` | Same as above for `DBMS_CLOUD_AI`.                                                                                                                                                                     |
| `ORA-29024 Certificate validation failure`               | The outbound network ACL is missing the OCI Gen AI host. The setup script opens it; if you changed `OCI_GENAI_REGION` after running setup, re-run it.                                                  |
| `Service Unavailable` or `404 Not Found` from OCI        | The inference URL is region-derived. Check `OCI_GENAI_REGION` is a region with OCI Gen AI enabled.                                                                                                     |
| `Authorization Failed` (401 / 403)                       | Fingerprint doesn't match the uploaded public key, or the private key file path is wrong, or the user lacks `manage generative-ai-family` policy in the compartment.                                   |
| Zod parse errors on `extractFieldsInDb`                  | The model returned malformed JSON or null on a required field. `extractFieldsInDb` retries once; if it still fails, the doc is marked `failed` with the Zod error stored in `documents.failed_reason`. |
