# Run the Oracle VecDB Ask the Parks Sample

Help the user run the existing public Oracle AI Developer Hub `vecdb_ask_parks`
sample. This is an existing sample, not an application to build from scratch.
Use the sample README as the source of truth for installation, configuration,
data loading, and usage. Preserve the sample's Python HTTP server, local CSV
fallback, map interface, and Oracle VecDB integration.

The sample has two supported modes:

- **Local fallback** runs from the bundled CSV and does not require a database
  or database credentials. Use this mode for UI exploration.
- **Oracle VecDB mode** uses an existing Oracle AI Database deployment through
  the Oracle VecDB Python SDK. It requires an existing SDK REST endpoint and
  either a bearer token or vector-user username and password.

Do not provision or create a database instance, tenancy, ORDS deployment,
schema, user, or credentials. Never print, copy, or commit database connection
values. Ask for existing connection details only when the user chooses Oracle
VecDB mode, and keep them out of logs and completion reports.

From the intended working directory, use a Git sparse checkout so only the
mapped application is fetched:

```bash
git clone --depth 1 --filter=blob:none --sparse --branch main \
  https://github.com/oracle-devrel/oracle-ai-developer-hub.git
cd oracle-ai-developer-hub
git sparse-checkout set apps/vecdb/vecdb_ask_parks
cd apps/vecdb/vecdb_ask_parks
```

Read `README.md` and `requirements.txt` before taking setup or runtime actions.
Create a virtual environment and install the requirements as documented. Use
the platform's Python command when `python3` is not available.

## Local fallback mode

If the user chooses local fallback mode, run the application from the sample
directory with the README's command:

```bash
python3 app.py
```

Open `http://127.0.0.1:8000`. Do not ask for database credentials or run the
VecDB loader in this mode.

## Oracle VecDB mode

If the user chooses Oracle VecDB mode, copy `.env.example` to `.env` in the
sample directory. Tell the user the absolute path and ask them to populate the
connection values themselves. Do not display, read back, copy, or include
those values in generated content. Wait for the user to confirm that the file
is complete before using the connection.

Follow the README configuration exactly. The application accepts
`VECDB_REST_URL` with either `VECDB_ACCESS_TOKEN` or
`VECDB_USERNAME` and `VECDB_PASSWORD`; bearer-token authentication takes
precedence when both methods are present. Keep TLS verification enabled by
default. Set `VECDB_SELF_SIGNED_SSL=true` only for a trusted development
endpoint with a self-signed certificate; this disables certificate verification.

Before loading data, inspect `VECDB_EMBED_MODEL` in `.env` and confirm that it
matches the model used to generate the bundled vectors. The README's example
uses `all_MiniLM_L12_v2`; do not silently accept a conflicting template value
or change the model without confirming that matching vectors are available.

After the user confirms the configuration, ask for explicit confirmation before
running the loader because it creates and populates the configured application
table:

```bash
python3 load_parks_vecdb.py --csv-file data/us_national_parks_dataset_spatial.csv
```

Run it from the sample directory. The default table is `national_parks`; the
configured embedding model must already be available in VecDB and match the
bundled vectors. Do not use `--recreate` without explicit confirmation because
it drops the named table. Do not write to tables outside the sample's
configured table.

After loading succeeds, run the README's application command and report the
local URL. If the user only wants to inspect the UI, stop after local fallback
starts. Point the user back to the README for changes to the sample.

## Sources

- Ask the Parks README: https://github.com/oracle-devrel/oracle-ai-developer-hub/tree/main/apps/vecdb/vecdb_ask_parks
- Oracle VecDB Python SDK API reference: https://docs.oracle.com/en/cloud/paas/autonomous-vector-database/vcapi/index.html
