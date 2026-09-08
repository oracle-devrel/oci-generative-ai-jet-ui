# Run the Oracle VecDB RAG Sample

Help the user run the public Oracle AI Developer Hub `doc_chatbot` RAG sample
against an existing Oracle VecDB endpoint. This is an existing sample, not an
application to build from scratch: use a sparse checkout, install its
documented dependencies, and run it. Once it is running, point the user to the
sample README for instructions on modifying or extending it.

Use an existing Oracle AI Database 26ai+ deployment at database version
`23.26.3` or later. Before running the mapped sample against VecDB, determine
whether ORDS is available. This Python SDK sample requires an existing ORDS
endpoint at version `26.2.2` or later. Ask for missing existing connection
details: REST URL plus username/password or bearer/API token.

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
git sparse-checkout set apps/vecdb/doc_chatbot
cd apps/vecdb/doc_chatbot
```

Read the sample's README and dependency files. Use the README's documented
installation and run commands for the Streamlit sample. Install the declared
dependencies in the sample's virtual environment, then install the public SDK.
Preserve the sample as
the baseline; adapt it rather than substituting an unrelated app, LLM
architecture, or vector-store abstraction.

## TLS preflight

Keep TLS certificate and hostname verification enabled. Do not change the
sample's source code to handle certificate trust. Instead, configure the
virtual environment to use the operating-system trust store:

```bash
python -m pip install pip-system-certs
```

Run the SDK preflight in a new Python process after this installation. The
preflight must be read-only.

## Run the application

Follow the instructions in the README to run the application.

## Oracle Version Notes (19c vs 26ai)

Oracle Database 19c does not support this VecDB sample. Use Oracle AI Database
26ai+ at database version `23.26.3` or later with ORDS `26.2.2` or later.

## Sources

- Oracle VecDB Python SDK API reference: https://docs.oracle.com/en/cloud/paas/autonomous-vector-database/vcapi/index.html
- Oracle AI Developer Hub RAG sample: https://github.com/oracle-devrel/oracle-ai-developer-hub/tree/main/apps/vecdb/doc_chatbot
