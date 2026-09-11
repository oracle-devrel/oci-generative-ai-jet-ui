# Run the Oracle VecDB Recommendation Sample

Help the user run the public Oracle AI Developer Hub
`product_recommendation` sample against an existing Oracle VecDB endpoint.
This is an existing sample, not an application to build from scratch: use a
sparse checkout, install its documented dependencies, and run it. Once it is
running, point the user to the sample README for instructions on modifying or
extending it.

Use Oracle Autonomous AI Vector Database or an existing Oracle AI Database
26ai+ deployment at database version `23.26.3` or later, along with an existing
ORDS endpoint at version `26.2.2` or later. Before running the mapped sample
against VecDB, determine whether ORDS is available. Ask for missing existing
connection details: REST URL plus username/password or bearer/API token.

Do not provision or create a database instance, tenancy, ORDS deployment,
schema, user, or credentials.

Use the public Python SDK, installed with:

```bash
python -m pip install oracle-vecdb
```

From the intended working directory, use a Git sparse checkout so only the
mapped application is fetched:

```bash
git clone --depth 1 --filter=blob:none --sparse --branch main \
  https://github.com/oracle-devrel/oracle-ai-developer-hub.git
cd oracle-ai-developer-hub
git sparse-checkout set apps/vecdb/product_recommendation
cd apps/vecdb/product_recommendation
```

Inspect the sample's README and dependency files. Preserve the sample as the baseline; adapt it
rather than substituting an unrelated app or architecture.

## Connection configuration

Follow the README configuration instructions exactly. If the
sample provides an `.env.example`, copy it to the documented local `.env`
path. Tell the user the absolute path to that local configuration file and ask
them to populate its connection details themselves. Do not display, read back,
or copy those details.

Pause and wait for the user to confirm that the configuration is complete
before running the SDK preflight, downloading a dataset, creating or populating
vector tables, or starting the application.

## TLS preflight

Keep TLS certificate and hostname verification enabled. Do not change the
sample's source code to handle certificate trust. Instead, configure the
virtual environment to use the operating-system trust store:

```bash
python -m pip install pip-system-certs
```

Run the SDK preflight in a new Python process after this installation. The
preflight must be read-only.

## Dataset setup and VecDB writes

After the user confirms the configuration, follow the README's single
documented public product-dataset setup flow. Do not invent Quickstart/Full
profiles or choose an undocumented dataset variant.

Ask for explicit confirmation before running:

```bash
cd backend
python load_dataset.py
```

The loader may create and populate only the sample's configured application
vector table, which defaults to `PRODUCT_TEXT_VECTORS`. Inspect the existing
table and relevant jobs before mutation. Ask for explicit confirmation before
any destructive, costly, bulk-load, or rebuild operation. Do not create
schemas, users, credentials, ORDS resources, or database instances. Do not
write to tables outside the approved application scope.

## Local run commands

After the approved dataset setup completes, run the README-declared local services.
If the sample has separate backend and frontend services, start both as
documented, run them concurrently, and leave them running. Verify each service
returns HTTP 200 before reporting its local URL. Treat required long-running
services as final deliverables, not temporary verification steps.

At completion, report the sample used, sparse-checkout path, README
instructions followed, whether the approved dataset loader and services ran,
the local URLs, and the next adaptation step. Never report secrets or customer
data. Do not replace the stable mapping: it is
`apps/vecdb/product_recommendation` from the public repository `main` branch.

## Oracle Version Notes (19c vs 26ai)

Oracle Database 19c does not support this VecDB sample. Use Oracle AI Database
26ai+ at database version `23.26.3` or later with ORDS `26.2.2` or later.

## Sources

- Oracle VecDB Python SDK API reference: https://docs.oracle.com/en/cloud/paas/autonomous-vector-database/vcapi/index.html
- Oracle AI Developer Hub recommendation sample: https://github.com/oracle-devrel/oracle-ai-developer-hub/tree/main/apps/vecdb/product_recommendation
