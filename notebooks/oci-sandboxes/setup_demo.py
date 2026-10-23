"""Create or delete a Sandbox-enabled project using an OCI CLI session profile."""

import argparse
import json
from pathlib import Path
import uuid

import oci
from oci_genai_auth import OciSessionAuth

CONFIG_FILE = Path(__file__).with_name("config.local.json")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("create", help="Create a project and save config.local.json")
    create.add_argument("--compartment-id", required=True)
    create.add_argument("--region", required=True)
    create.add_argument("--profile", default="DEFAULT")
    commands.add_parser("delete", help="Delete the project in config.local.json")
    args = parser.parse_args()
    creating = args.command == "create"
    settings = (
        {"profile": args.profile, "region": args.region, "model_id": "openai.gpt-oss-120b"}
        if creating else json.loads(CONFIG_FILE.read_text())
    )
    if not creating and input(f"Delete {settings['project_id']} and its conversations? [y/N] ").lower() != "y":
        return
    config = oci.config.from_file(profile_name=settings["profile"])
    config["region"] = settings["region"]
    client = oci.generative_ai.GenerativeAiClient(
        config, signer=OciSessionAuth(profile_name=settings["profile"]).signer,
        retry_strategy=oci.retry.NoneRetryStrategy(), timeout=(5, 60),
    )
    if creating:
        token = uuid.uuid4().hex
        models = oci.generative_ai.models
        details = models.CreateGenerativeAiProjectDetails(
            compartment_id=args.compartment_id,
            display_name=f"sandboxes-demo-project-{token[:8]}",
            description="Project for the OCI Sandboxes demo.",
            sandbox_config=models.SandboxConfig(
                is_enabled=True,
                sandbox_outbound_networking_config=models.ManagedSandboxOutboundNetworkingConfig(
                    network_policy=models.SandboxDenyAllNetworkPolicy(),
                ),
            ),
        )
        with CONFIG_FILE.open("x", encoding="utf-8") as output:
            print(f"Creating project: {details.display_name}", flush=True)
            try:
                project = client.create_generative_ai_project(details, opc_retry_token=token).data
            except Exception:
                output.close()
                CONFIG_FILE.unlink()
                raise
            settings["project_id"] = project.id
            print(f"Created project: {project.id}", flush=True)
            json.dump(settings, output, indent=2)
            output.write("\n")
    target = "ACTIVE" if creating else "DELETED"
    try:
        if not creating:
            client.delete_generative_ai_project(settings["project_id"])
        response = oci.wait_until(
            client, client.get_generative_ai_project(settings["project_id"]),
            "lifecycle_state", (target, "FAILED"), max_interval_seconds=5,
            max_wait_seconds=300, succeed_on_not_found=not creating,
        )
        if response and response.data.lifecycle_state == "FAILED":
            raise RuntimeError(f"Project failed: {response.data.lifecycle_details}")
    except oci.exceptions.ServiceError as error:
        if creating or error.status != 404:
            raise
    if creating:
        print('Ready. Select read_json("config.local.json") in the notebook.')
    else:
        CONFIG_FILE.unlink()
        print("Deleted project and config.local.json.")


if __name__ == "__main__":
    main()
