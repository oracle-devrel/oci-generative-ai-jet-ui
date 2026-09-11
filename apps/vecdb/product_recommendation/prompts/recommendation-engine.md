# Run the Oracle VecDB Recommendation Sample

Help the user run the public Oracle AI Developer Hub
`product_recommendation` sample against an existing Oracle VecDB endpoint.
This is an existing sample, not an application to build from scratch: use a
sparse checkout, install its documented dependencies, and run it. Once it is
running, point the user to the sample README for instructions on modifying or
extending it.

Use Oracle Autonomous AI Vector Database or an existing Oracle AI Database
deployment that meets the supported database and ORDS versions in the sample
README. Before running the mapped sample against VecDB, determine whether ORDS
is available. Ask for missing existing connection details: REST URL plus
username/password or a bearer token.

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

Inspect the sample's README and dependency files. The README is the source of
truth for installation, configuration, dataset loading, and usage. Preserve the
sample as the baseline; adapt it rather than substituting an unrelated app or
architecture.

## Connection configuration

Follow the README configuration instructions exactly. If the
sample provides an `.env.example`, copy it to the documented local `.env`
path. Tell the user the absolute path to that local configuration file and ask
them to populate its connection details themselves. Do not display, read back,
or copy those details.

Pause and wait for the user to confirm that the configuration is complete
before running the SDK preflight, downloading a dataset, creating or populating
vector tables, or starting the application.

## TLS

Keep TLS certificate and hostname verification enabled. Do not use `curl -k`,
disable certificate verification, or change the sample's source code to bypass
TLS checks. If the endpoint uses a private or self-signed certificate, stop and
ask the user to configure trust on the host according to their environment
before continuing.

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

## Oracle Version Notes

Oracle Database 19c does not support this VecDB sample. Follow the supported
database and ORDS versions stated in the sample README.

## Sources

- Oracle VecDB Python SDK API reference: https://docs.oracle.com/en/cloud/paas/autonomous-vector-database/vcapi/index.html
- Oracle AI Developer Hub recommendation sample: https://github.com/oracle-devrel/oracle-ai-developer-hub/tree/main/apps/vecdb/product_recommendation
