"""OCI Sandbox tool contract, lifecycle, execution and file transfer."""

import re
import time
import uuid

import oci
from pydantic import BaseModel, ConfigDict, Field

from demo_utils import ModelOutputError, available_files, store_outputs

WORKSPACE = "/workspace"


class SandboxTask(BaseModel):
    """The model's request to execute a Python analysis."""

    model_config = ConfigDict(extra="forbid")
    purpose: str = Field(description="A brief explanation of the requested calculation.")
    code: str = Field(description="Complete Python 3.11 program, without Markdown fences. Use relative file paths and print findings to stdout.")
    input_files: list[str] = Field(description="Names from the available file list. Use a JSON array, or [] when no files are needed.")
    output_files: list[str] = Field(description="New files the program will create: CSV, JSON, TXT or a .chart.json chart specification. Use [] if stdout is sufficient.")


class Sandboxes:
    """Manage one active Sandbox at a time, using the existing OCI SDK."""

    def __init__(self, settings, *, auth, run, runtime, shape, expires_in_minutes, execution_timeout_seconds):
        config = oci.config.from_file(profile_name=settings["profile"])
        config["region"] = settings["region"]
        endpoint = f"https://inference.generativeai.{settings['region']}.oci.oraclecloud.com"
        self.client = oci.generative_ai_sandbox.GenerativeAiSandboxClient(
            config=config, signer=auth.signer, service_endpoint=endpoint,
            retry_strategy=oci.retry.NoneRetryStrategy(), timeout=(5, 60),
        )
        self.runtime = runtime
        self.shape = shape
        self.expires_in_minutes = expires_in_minutes
        self.execution_timeout_seconds = execution_timeout_seconds
        self.project_id = settings["project_id"]
        self.run = run
        self.sandbox_id = None

    def prepare_payload(self, arguments):
        """Validate execution arguments before creating a Sandbox."""
        files = available_files(self.run)
        try:
            task = SandboxTask.model_validate(arguments)
            if len(task.input_files) != len(set(task.input_files)) or not set(task.input_files) <= set(files):
                raise ValueError(f"Choose unique inputs from the available files: {sorted(files)}")
            if len(task.output_files) > 8 or len(task.output_files) != len(set(task.output_files)):
                raise ValueError("Choose at most eight distinct output files.")
            for name in task.output_files:
                if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}\.(csv|json|txt|chart\.json)", name):
                    raise ValueError("Output names must be simple filenames ending in .csv, .json, .txt or .chart.json.")
                if name in files:
                    raise ValueError(f"Existing files are read-only. Choose a new output name instead of {name}.")
        except ValueError as error:
            raise ModelOutputError(str(error)) from error
        return task

    def create_sandbox(self):
        if self.sandbox_id is not None:
            raise RuntimeError("Shut down the current Sandbox before creating another.")
        attempt_id = uuid.uuid4().hex
        details = oci.generative_ai_sandbox.models.CreateSandboxDetails(
            display_name=f"sandboxes-demo-{attempt_id[:12]}",
            runtime=self.runtime, shape=self.shape, expires_in_minutes=self.expires_in_minutes,
        )
        response = self.client.create_sandbox(self.project_id, details, opc_retry_token=attempt_id)
        self.sandbox_id = response.data.id
        return self

    def _read_file(self, name):
        return self.client.read_sandbox_file(self.sandbox_id, f"{WORKSPACE}/{name}").data.content

    def _upload_file(self, name, content):
        self.client.base_client.call_api(
            resource_path="/sandboxes/{sandboxId}/files/write", method="POST",
            path_params={"sandboxId": self.sandbox_id}, query_params={"filePath": f"{WORKSPACE}/{name}"},
            header_params={"content-type": "application/octet-stream", "accept": "application/json"},
            body=content, response_type="SandboxFile",
        )
        if self._read_file(name) != content:
            raise ValueError(f"Upload verification failed: {name}")

    def run_payload(self, payload):
        files = available_files(self.run)
        inputs = {name: files[name] for name in payload.input_files}
        self._wait_for_sandbox(self.sandbox_id, "RUNNING", timeout=120)
        for name, content in inputs.items():
            self._upload_file(name, content)
        self._upload_file("analysis.py", payload.code.encode("utf-8"))
        command = oci.generative_ai_sandbox.models.RunSandboxCommandDetails(
            command="python", args=["analysis.py"], cwd=WORKSPACE, timeout=f"PT{self.execution_timeout_seconds}S",
        )
        output = self.client.run_sandbox_command_and_wait(self.sandbox_id, command).data.output
        for name, original in inputs.items():
            if self._read_file(name) != original:
                raise RuntimeError(f"Analysis modified an input file: {name}")
        if output.exit_code != 0:
            raise ModelOutputError(f"Program exited with code {output.exit_code}: {(output.stderr or '')[-4000:]}")
        try:
            artifacts = {name: self._read_file(name) for name in payload.output_files}
        except oci.exceptions.ServiceError as error:
            if error.status == 404:
                raise ModelOutputError("A declared output file is missing or the Sandbox expired.") from error
            raise
        return store_outputs(self.run, artifacts, output.stdout or "")

    def shutdown(self):
        if self.sandbox_id is not None:
            self._delete_sandbox(self.sandbox_id)
            self.sandbox_id = None

    def cleanup(self):
        """Delete remaining demo Sandboxes in this project, including unlogged ones."""
        sandboxes = oci.pagination.list_call_get_all_results(
            self.client.list_sandboxes, project_id=self.project_id,
        ).data
        errors = []
        for sandbox in sandboxes:
            if (sandbox.display_name or "").startswith("sandboxes-demo-") and sandbox.lifecycle_state != "DELETED":
                try:
                    self._delete_sandbox(sandbox.id)
                except Exception as error:
                    errors.append(f"{sandbox.id}: {error}")
        if errors:
            raise RuntimeError("Some Sandboxes still need cleanup:\n" + "\n".join(errors))

    def _wait_for_sandbox(self, sandbox_id, target, timeout=15):
        """Wait briefly for startup or deletion; expiration is enforced by the service."""
        deadline = time.monotonic() + timeout
        while True:
            try:
                state = self.client.get_sandbox(sandbox_id).data.lifecycle_state
            except oci.exceptions.ServiceError as error:
                if target == "DELETED" and error.status == 404:
                    return
                raise
            if state == target:
                return
            if state == "FAILED" or time.monotonic() >= deadline:
                raise RuntimeError(f"Sandbox is {state}; did not reach {target} within {timeout}s.")
            time.sleep(1)

    def _delete_sandbox(self, sandbox_id):
        try:
            deadline = time.monotonic() + 60
            state = self.client.get_sandbox(sandbox_id).data.lifecycle_state
            while state in {"CREATING", "UPDATING"}:
                if time.monotonic() >= deadline:
                    raise RuntimeError(
                        f"Sandbox {sandbox_id} is still {state}; retry cleanup after it finishes transitioning."
                    )
                time.sleep(1)
                state = self.client.get_sandbox(sandbox_id).data.lifecycle_state
            if state not in {"STOPPED", "FAILED", "DELETED"}:
                if state != "STOPPING":
                    self.client.stop_sandbox(
                        sandbox_id, oci.generative_ai_sandbox.models.StopSandboxDetails(is_force=False),
                    )
                self._wait_for_sandbox(sandbox_id, "STOPPED")
            if state != "DELETED":
                self.client.delete_sandbox(sandbox_id)
                self._wait_for_sandbox(sandbox_id, "DELETED")
        except oci.exceptions.ServiceError as error:
            if error.status != 404:
                raise RuntimeError(f"Could not delete Sandbox {sandbox_id}; retry the final cleanup cell.") from error
