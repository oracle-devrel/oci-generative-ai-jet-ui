# OCI Sandboxes demo

Run model-generated Python in OCI Sandboxes from a Jupyter notebook, using a synthetic financial dataset.

## Prerequisites

- Python 3.11 and the OCI CLI installed and available in your terminal. On Windows, include the Python launcher (`py`) when installing Python.
- An OCI tenancy with Sandboxes enabled in your chosen region, an existing compartment, and permissions to manage Generative AI projects, conversations and Sandboxes and use on-demand inference.
- Access to the model configured in `config.local.json` (default: `openai.gpt-oss-120b`).

Running the notebook incurs OCI inference and Sandbox compute charges.

## 1. Install dependencies

Open a terminal in the demo folder. Run all commands from that folder. The commands use the virtual environment directly; activation is not required.

**macOS / Linux**

```sh
python3.11 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

**Windows PowerShell**

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## 2. Authenticate and create a project

The first command opens a browser login and creates a session profile named `DEMO` in `~/.oci/config` (Windows: `$HOME\.oci\config`); no existing profile is required. Sign in to your tenancy. You can choose another profile name by replacing `DEMO` in both commands.

Replace the compartment OCID and use a region enabled for your tenancy in both commands.

**All platforms: authenticate**

```text
oci session authenticate --profile-name DEMO --region us-chicago-1
```

**macOS / Linux: create the project**

```sh
.venv/bin/python setup_demo.py create --profile DEMO --region us-chicago-1 --compartment-id "<compartment-ocid>"
```

**Windows PowerShell: create the project**

```powershell
.\.venv\Scripts\python.exe setup_demo.py create --profile DEMO --region us-chicago-1 --compartment-id "<compartment-ocid>"
```

This creates a Sandbox-enabled project with outbound network access disabled and saves `config.local.json`. The file must not already exist; to reuse an existing project configuration, skip the create command. It does not create a Sandbox. If needed, update `model_id` in that file to an available model supporting Responses API tool calls. See Oracle’s [supported models and regions](https://docs.oracle.com/en-us/iaas/Content/generative-ai/agentic-regions.htm).

Use a separate project for each participant: the notebook cleans up all `sandboxes-demo-*` Sandboxes in its selected project.

## 3. Run the notebook

**macOS / Linux**

```sh
.venv/bin/python -m jupyterlab demo.ipynb
```

**Windows PowerShell**

```powershell
.\.venv\Scripts\python.exe -m jupyterlab demo.ipynb
```

Use the **Python 3 (ipykernel)** kernel. Run the cells in order with **Shift+Enter**, including **Finish**.

The **Connect to OCI** cell sets `SANDBOX_RUNTIME` (`python-3.11`), `SANDBOX_SHAPE` (`SMALL`: 1 OCPU, 4 GB memory), `SANDBOX_TTL_MINUTES` (`3`) and `SANDBOX_EXECUTION_TIMEOUT_SECONDS` (`20`). The TTL limits the Sandbox lifetime; the execution timeout limits each command.

Sandboxes are created when the model requests execution and deleted afterwards. Generated report files remain in memory; displayed results are saved with the notebook. Conversation history remains in OCI.

If authentication expires, repeat the login command with the same profile and region, restart the notebook kernel, and run from the first cell.

## 4. Remove the project

After running **Finish**, delete the project when it is no longer needed:

**macOS / Linux**

```sh
.venv/bin/python setup_demo.py delete
```

**Windows PowerShell**

```powershell
.\.venv\Scripts\python.exe setup_demo.py delete
```

Confirm the prompt to delete the project, its conversations, and `config.local.json`.
