# Run the Oracle VecDB RAG Sample

Help the user run the public Oracle AI Developer Hub `doc_chatbot` RAG sample
against an existing Oracle VecDB endpoint. This is an existing sample, not an
application to build from scratch: use a sparse checkout, install its
documented dependencies, and run it. Once it is running, point the user to the
sample README for instructions on modifying or extending it.

Use an existing Oracle AI Database deployment that meets the supported database
and ORDS versions in the sample README. Before running the mapped sample
against VecDB, determine whether ORDS is available. Ask for missing existing
connection details only when the user wants to run against a database: the SDK
REST URL plus username/password or a bearer token. Never print or commit those
values.

Do not provision or create a database instance, tenancy, ORDS deployment,
schema, user, or credentials.

From the intended working directory, use a Git sparse checkout so only the
mapped application is fetched:

```bash
git clone --depth 1 --filter=blob:none --sparse --branch main \
  https://github.com/oracle-devrel/oracle-ai-developer-hub.git
cd oracle-ai-developer-hub
git sparse-checkout set apps/vecdb/doc_chatbot
cd apps/vecdb/doc_chatbot
```

Read the sample's README and dependency files. The README is the source of
truth for installation, configuration, and usage: follow its documented
commands and run the application from the documented entry point, currently
`streamlit run app/main.py`. Install the declared dependencies in the sample's
virtual environment; `requirements.txt` includes the public `oracle-vecdb`
package. Preserve the sample as
the baseline; adapt it rather than substituting an unrelated app, LLM
architecture, or vector-store abstraction.

## TLS

Keep TLS certificate and hostname verification enabled. Do not use `curl -k`,
disable certificate verification, or change the sample's source code to bypass
TLS checks. If the endpoint uses a private or self-signed certificate, stop and
ask the user to configure trust on the host according to their environment
before continuing.

## Run the application

Follow the instructions in the README to run the application.

## Oracle Version Notes

Oracle Database 19c does not support this VecDB sample. Follow the supported
database and ORDS versions stated in the sample README.

## Sources

- Oracle VecDB Python SDK API reference: https://docs.oracle.com/en/cloud/paas/autonomous-vector-database/vcapi/index.html
- Oracle AI Developer Hub RAG sample: https://github.com/oracle-devrel/oracle-ai-developer-hub/tree/main/apps/vecdb/doc_chatbot
