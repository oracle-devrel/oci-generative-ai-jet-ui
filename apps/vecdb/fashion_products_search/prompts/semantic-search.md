# Run the Oracle VecDB Semantic Search Sample

Help the user run the existing public Oracle AI Developer Hub `fashion_products_search` sample against an existing Oracle VecDB endpoint. Do not build a new application or replace the sample's architecture. Sparse-checkout only this application, then use its README as the source of truth for dependencies, configuration, dataset loading, startup, and future modifications.

Use Oracle Autonomous AI Vector Database or an existing Oracle AI Database 26ai+ deployment at database version `23.26.3` or later, with an existing ORDS endpoint at version `26.2.2` or later. Do not provision or create a database instance, tenancy, ORDS deployment, schema, user, or credentials. Use the sample's Python SDK → ORDS → database route.

Install the public SDK with:

```bash
python -m pip install oracle-vecdb
```

From the intended working directory, use a Git sparse checkout so only the
mapped application is fetched:

```bash
git clone --depth 1 --filter=blob:none --sparse --branch main \
  https://github.com/oracle-devrel/oracle-ai-developer-hub.git
cd oracle-ai-developer-hub
git sparse-checkout set apps/vecdb/fashion_products_search
cd apps/vecdb/fashion_products_search
```

Read `apps/vecdb/fashion_products_search/README.md` before taking setup or runtime actions. Preserve the sample as the baseline.

## Dataset choice

Before downloading data, present the user with these choices and ask which one they want:

- **Small** — quicker to download and run, but the lower-resolution images will look pixelated.
- **High** — much better visual quality, but takes longer to download and set up.

Do not choose on the user's behalf. Pass the user's choice through to the README's corresponding dataset/profile instructions; do not invent alternate loader commands or settings.

## Connection configuration

After the user chooses a dataset, copy `backend/.env.example` to `backend/.env`. Tell the user the absolute path to the `.env` file and ask them to populate the connection details themselves. Do not display, read back, copy, or include those details in logs, generated content, source control, or completion reports. Pause until the user confirms that the file is complete, then continue with the README instructions.

Treat Kaggle or Hugging Face credentials as optional secrets: ask only if the README or the download requires them, and keep them out of generated content and source control.

## Setup, loading, and running

Once the user confirms `.env` completion, follow the sample README exactly for:

- virtual-environment and dependency installation (including the public `oracle-vecdb` SDK and any documented TLS/trust-store setup);
- the selected Small or High dataset download and loader;
- local backend and frontend startup.

Before running any command that downloads data or writes to VecDB, confirm that the user-selected dataset is the one being used. Only create or populate the application vector tables documented by the README. Never create schemas, users, credentials, ORDS resources, database instances, or unrelated tables.

At completion, report the sample path, README instructions followed, selected dataset, whether loading succeeded, local URLs, and the README location for modifying the sample.

## Oracle Version Notes (19c vs 26ai)

Oracle Database 19c does not support this VecDB sample. Use Oracle AI Database
26ai+ at database version `23.26.3` or later with ORDS `26.2.2` or later.

## Sources

- Oracle VecDB Python SDK API reference: https://docs.oracle.com/en/cloud/paas/autonomous-vector-database/vcapi/index.html
- Oracle AI Developer Hub semantic-search sample: https://github.com/oracle-devrel/oracle-ai-developer-hub/tree/main/apps/vecdb/fashion_products_search
