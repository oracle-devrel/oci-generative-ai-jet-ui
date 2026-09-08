#!/usr/bin/env python3
"""CLI for managing the oracle-database-java-agent-memory cloud deployment."""

import configparser
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
from pathlib import Path

import click
from dotenv import load_dotenv
from InquirerPy import inquirer
from jinja2 import Template
from rich.console import Console
from rich.panel import Panel

console = Console()

PROJECT_ROOT = Path(__file__).parent
ENV_FILE = PROJECT_ROOT / ".env"
TF_DIR = PROJECT_ROOT / "deploy" / "tf" / "app"
GENERATED_DIR = PROJECT_ROOT / "deploy" / "generated"
BACKEND_JAR = PROJECT_ROOT / "src" / "chatserver" / "build" / "libs" / "chatserver-0.0.1-SNAPSHOT.jar"
ONNX_MODEL = PROJECT_ROOT / "models" / "all_MiniLM_L12_v2.onnx"

OLLAMA_SHAPE_CHOICES = [
    "VM.Standard.E4.Flex   (CPU, cheap, fine for qwen2.5 smoke tests)",
    "VM.Standard.E5.Flex   (CPU, newer AMD)",
    "VM.GPU.A10.1          (GPU, 1x NVIDIA A10, fast inference)",
    "VM.GPU2.1             (GPU, 1x NVIDIA P100, legacy)",
]


def _shape_from_choice(choice: str) -> str:
    return choice.split()[0]


def _read_oci_config():
    oci_config_path = Path.home() / ".oci" / "config"
    if not oci_config_path.exists():
        console.print(f"[red]Error:[/red] OCI config not found at {oci_config_path}")
        sys.exit(1)

    config = configparser.ConfigParser()
    config.read(oci_config_path)

    profiles = list(config.sections())
    if config.defaults():
        profiles.insert(0, "DEFAULT")
    return profiles, config


def _generate_password(length: int = 20) -> str:
    """Generate Oracle-compliant password (starts with letter, 2+ specials, 2+ digits)."""
    letters = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
    digits = "0123456789"
    specials = "#_-"

    password = [secrets.choice(letters)]
    password.append(secrets.choice(specials))
    password.append(secrets.choice(specials))
    password.append(secrets.choice(digits))
    password.append(secrets.choice(digits))

    alphabet = letters + digits + specials
    for _ in range(length - 5):
        password.append(secrets.choice(alphabet))

    tail = password[1:]
    secrets.SystemRandom().shuffle(tail)
    password[1:] = tail
    return "".join(password)


def _list_regions(oci_config):
    import oci  # lazy import

    try:
        identity_client = oci.identity.IdentityClient(oci_config)
        tenancy_id = oci_config["tenancy"]

        tenancy = identity_client.get_tenancy(tenancy_id).data
        home_region_key = tenancy.home_region_key

        subscriptions = identity_client.list_region_subscriptions(tenancy_id).data
        regions = []
        for sub in subscriptions:
            is_home = sub.region_key == home_region_key
            regions.append({"name": sub.region_name, "key": sub.region_key, "is_home": is_home})

        regions.sort(key=lambda x: (not x["is_home"], x["name"]))
        return regions
    except Exception as e:
        console.print(f"[yellow]Warning:[/yellow] Could not fetch regions: {e}")
        return None


def _list_compartments(oci_config):
    import oci  # lazy import

    try:
        identity_client = oci.identity.IdentityClient(oci_config)
        tenancy_id = oci_config["tenancy"]

        tenancy = identity_client.get_compartment(tenancy_id).data
        compartments = [
            {
                "name": f"{tenancy.name} (root)",
                "id": tenancy_id,
                "description": tenancy.description or "Root compartment",
            }
        ]

        response = oci.pagination.list_call_get_all_results(
            identity_client.list_compartments,
            compartment_id=tenancy_id,
            compartment_id_in_subtree=True,
            access_level="ACCESSIBLE",
        )

        for comp in response.data:
            if comp.lifecycle_state == "ACTIVE":
                compartments.append(
                    {"name": comp.name, "id": comp.id, "description": comp.description or ""}
                )
        return compartments
    except Exception as e:
        console.print(f"[yellow]Warning:[/yellow] Could not fetch compartments: {e}")
        return None


def _check_version(cmd, args, name, min_major):
    try:
        result = subprocess.run([cmd] + args, capture_output=True, text=True, timeout=15)
        output = result.stdout + result.stderr
        match = re.search(r"(\d+)\.\d+", output)
        if not match:
            console.print(f"[red]Error:[/red] Could not parse {name} version from: {output.strip()}")
            return False
        major = int(match.group(1))
        if major < min_major:
            console.print(f"[red]Error:[/red] {name} {major} found, need {min_major}+")
            return False
        console.print(f"  {name} {match.group(0)} [green]OK[/green]")
        return True
    except FileNotFoundError:
        console.print(f"[red]Error:[/red] {name} not found. Install {name} {min_major}+ and try again.")
        return False


def _run_build_step(label, cmd, cwd):
    console.print(f"\n[bold]{label}[/bold]")
    result = subprocess.run(cmd, cwd=cwd, shell=True)
    if result.returncode != 0:
        console.print(f"[red]Error:[/red] {label} failed (exit {result.returncode})")
        return False
    return True


@click.group()
def cli():
    """Oracle Database Java Agent Memory — Cloud Deployment Manager."""


@cli.command()
def setup():
    """Interactive OCI configuration. Stores results in .env."""
    console.print("[bold]Oracle Database Java Agent Memory — Cloud Setup[/bold]\n")

    profiles, oci_config_parser = _read_oci_config()

    profile = inquirer.select(
        message="OCI profile:",
        choices=profiles,
        default=profiles[0] if profiles else None,
    ).execute()

    profile_config = oci_config_parser[profile]
    tenancy_ocid = profile_config.get("tenancy")
    user_ocid = profile_config.get("user")
    fingerprint = profile_config.get("fingerprint")
    key_file = profile_config.get("key_file")
    config_region = profile_config.get("region", "us-phoenix-1")

    sdk_config = {
        "user": user_ocid,
        "key_file": key_file,
        "fingerprint": fingerprint,
        "tenancy": tenancy_ocid,
        "region": config_region,
    }

    # Region selection
    console.print("\nFetching subscribed regions...")
    regions = _list_regions(sdk_config)
    if regions:
        region_choices = [
            f"{reg['name']} (home)" if reg["is_home"] else reg["name"] for reg in regions
        ]
        selected = inquirer.select(
            message="Region:", choices=region_choices, default=region_choices[0]
        ).execute()
        region = selected.replace(" (home)", "")
    else:
        region = click.prompt("Region", default=config_region)
    sdk_config["region"] = region

    # Compartment selection
    console.print("\nFetching compartments...")
    compartments = _list_compartments(sdk_config)
    if compartments:
        comp_choices = [c["name"] for c in compartments]
        comp_map = {c["name"]: c["id"] for c in compartments}
        selected_comp = inquirer.fuzzy(
            message="Compartment (type to search):", choices=comp_choices, default=None
        ).execute()
        compartment_ocid = comp_map[selected_comp]
    else:
        compartment_ocid = click.prompt("Compartment OCID")

    # SSH key
    ssh_dir = Path.home() / ".ssh"
    ssh_keys = (
        sorted(
            f.name
            for f in ssh_dir.iterdir()
            if f.is_file() and not f.suffix and (f.with_suffix(".pub")).exists()
        )
        if ssh_dir.is_dir()
        else []
    )
    if ssh_keys:
        ssh_private_key_path = str(
            ssh_dir / inquirer.fuzzy(message="SSH private key:", choices=ssh_keys).execute()
        )
    else:
        ssh_private_key_path = click.prompt("SSH private key path")

    ssh_public_key_path = ssh_private_key_path + ".pub"
    if Path(ssh_public_key_path).exists():
        ssh_public_key = Path(ssh_public_key_path).read_text().strip()
    else:
        ssh_public_key = click.prompt("SSH public key (paste content)")

    # Read API key content (needed for DBMS_CLOUD credential on the DB)
    key_file_path = Path(key_file).expanduser()
    if key_file_path.exists():
        private_api_key_content = key_file_path.read_text().strip()
    else:
        console.print(f"[yellow]Warning:[/yellow] Key file not found: {key_file}")
        private_api_key_content = click.prompt("Paste OCI API private key content")

    # Ollama shape (CPU / GPU)
    console.print()
    ollama_choice = inquirer.select(
        message="Ollama (LLM) instance shape:",
        choices=OLLAMA_SHAPE_CHOICES,
        default=OLLAMA_SHAPE_CHOICES[0],
    ).execute()
    ollama_shape = _shape_from_choice(ollama_choice)

    ollama_chat_model = inquirer.text(
        message="Ollama chat model to pull:",
        default="qwen2.5",
    ).execute()

    project_name = inquirer.text(
        message="Project name (lowercase letters/digits, used in resource names):",
        default="agentmem",
    ).execute()

    db_admin_password = _generate_password()

    console.print(
        Panel(
            f"Profile:       {profile}\n"
            f"Tenancy:       {tenancy_ocid}\n"
            f"Region:        {region}\n"
            f"Compartment:   {compartment_ocid}\n"
            f"Project name:  {project_name}\n"
            f"SSH key:       {ssh_private_key_path}\n"
            f"Ollama shape:  {ollama_shape}\n"
            f"Ollama model:  {ollama_chat_model}\n"
            f"DB password:   (generated, stored in .env)",
            title="Configuration Summary",
        )
    )

    if not click.confirm("Save configuration?", default=True):
        console.print("[yellow]Setup cancelled.[/yellow]")
        sys.exit(0)

    env_vars = {
        "OCI_PROFILE": profile,
        "OCI_TENANCY_OCID": tenancy_ocid,
        "OCI_USER_OCID": user_ocid,
        "OCI_FINGERPRINT": fingerprint,
        "OCI_KEY_FILE": key_file,
        "OCI_COMPARTMENT_OCID": compartment_ocid,
        "OCI_REGION": region,
        "PROJECT_NAME": project_name,
        "DB_ADMIN_PASSWORD": db_admin_password,
        "SSH_PRIVATE_KEY_PATH": ssh_private_key_path,
        "SSH_PUBLIC_KEY": ssh_public_key,
        "OCI_PRIVATE_API_KEY_CONTENT": private_api_key_content,
        "OLLAMA_SHAPE": ollama_shape,
        "OLLAMA_CHAT_MODEL": ollama_chat_model,
    }

    with open(ENV_FILE, "w") as f:
        for key, value in env_vars.items():
            if "\n" in str(value):
                # multi-line (the API private key)
                escaped = str(value).replace('"', '\\"')
                f.write(f'{key}="{escaped}"\n')
            else:
                f.write(f'{key}="{value}"\n')

    console.print(f"\n[green]Configuration saved to {ENV_FILE}[/green]")
    console.print("\nNext step: [bold]python manage.py build[/bold]")


@cli.command()
def build():
    """Build the backend JAR and verify the ONNX model is present."""
    console.print("[bold]Building backend...[/bold]\n")

    console.print("Checking tools:")
    ok = _check_version("java", ["--version"], "Java", 21)
    if not ok:
        sys.exit(1)

    backend_dir = PROJECT_ROOT / "src" / "chatserver"
    if not _run_build_step("Backend (Gradle)", "./gradlew build -x test", backend_dir):
        sys.exit(1)

    if not BACKEND_JAR.exists():
        console.print(f"[red]Error:[/red] Backend JAR not found at {BACKEND_JAR}")
        sys.exit(1)
    console.print(f"  Backend JAR: [green]{BACKEND_JAR.relative_to(PROJECT_ROOT)}[/green]")

    if not ONNX_MODEL.exists():
        console.print(
            f"\n[red]Error:[/red] ONNX model not found at {ONNX_MODEL}.\n"
            "Download the pre-built all-MiniLM-L12-v2 ONNX model from:\n"
            "  https://blogs.oracle.com/machinelearning/use-our-prebuilt-onnx-model-now-available-for-embedding-generation-in-oracle-database-23ai\n"
            f"and save it to {ONNX_MODEL.relative_to(PROJECT_ROOT)}."
        )
        sys.exit(1)
    size_mb = ONNX_MODEL.stat().st_size / (1024 * 1024)
    console.print(f"  ONNX model:  [green]{ONNX_MODEL.name} ({size_mb:.0f} MB)[/green]")

    console.print("\n[green]Build complete.[/green]")
    console.print("\nNext step: [bold]python manage.py tf[/bold]")


@cli.command()
def tf():
    """Render deploy/tf/app/terraform.tfvars from .env and the Jinja2 template."""
    if not ENV_FILE.exists():
        console.print("[red]Error:[/red] .env not found. Run 'python manage.py setup' first.")
        sys.exit(1)

    load_dotenv(ENV_FILE, override=True)

    required_vars = [
        "OCI_PROFILE",
        "OCI_TENANCY_OCID",
        "OCI_USER_OCID",
        "OCI_FINGERPRINT",
        "OCI_KEY_FILE",
        "OCI_COMPARTMENT_OCID",
        "OCI_REGION",
        "PROJECT_NAME",
        "DB_ADMIN_PASSWORD",
        "SSH_PUBLIC_KEY",
        "SSH_PRIVATE_KEY_PATH",
        "OCI_PRIVATE_API_KEY_CONTENT",
        "OLLAMA_SHAPE",
        "OLLAMA_CHAT_MODEL",
    ]
    missing = [v for v in required_vars if not os.getenv(v)]
    if missing:
        console.print(f"[red]Error:[/red] Missing variables in .env: {', '.join(missing)}")
        sys.exit(1)

    if not BACKEND_JAR.exists():
        console.print(f"[yellow]Warning:[/yellow] Backend JAR missing: {BACKEND_JAR}")
        console.print("Run [bold]python manage.py build[/bold] first.")
        sys.exit(1)
    if not ONNX_MODEL.exists():
        console.print(f"[yellow]Warning:[/yellow] ONNX model missing: {ONNX_MODEL}")
        console.print("Run [bold]python manage.py build[/bold] first.")
        sys.exit(1)

    console.print("[bold]Generating terraform.tfvars...[/bold]\n")

    template_file = TF_DIR / "terraform.tfvars.j2"
    if not template_file.exists():
        console.print(f"[red]Error:[/red] Template not found: {template_file}")
        sys.exit(1)

    template = Template(template_file.read_text())
    tfvars_content = template.render(
        profile=os.getenv("OCI_PROFILE"),
        tenancy_ocid=os.getenv("OCI_TENANCY_OCID"),
        user_ocid=os.getenv("OCI_USER_OCID"),
        fingerprint=os.getenv("OCI_FINGERPRINT"),
        private_api_key_content=os.getenv("OCI_PRIVATE_API_KEY_CONTENT"),
        compartment_ocid=os.getenv("OCI_COMPARTMENT_OCID"),
        region=os.getenv("OCI_REGION"),
        project_name=os.getenv("PROJECT_NAME"),
        db_admin_password=os.getenv("DB_ADMIN_PASSWORD"),
        ssh_public_key=os.getenv("SSH_PUBLIC_KEY"),
        ssh_private_key_path=os.getenv("SSH_PRIVATE_KEY_PATH"),
        ollama_shape=os.getenv("OLLAMA_SHAPE"),
        ollama_chat_model=os.getenv("OLLAMA_CHAT_MODEL"),
    )

    tfvars_file = TF_DIR / "terraform.tfvars"
    tfvars_file.write_text(tfvars_content)

    console.print(f"[green]Generated:[/green] {tfvars_file}\n")
    console.print("[bold]Next steps:[/bold]")
    console.print("  cd deploy/tf/app")
    console.print("  terraform init")
    console.print("  terraform plan -out=tfplan")
    console.print("  terraform apply tfplan\n")
    console.print("After Terraform completes: [bold]python manage.py info[/bold]")


@cli.command()
def info():
    """Print deployment access info and surface the wallet locally for testing."""
    if not ENV_FILE.exists():
        console.print("[red]Error:[/red] .env not found. Run 'python manage.py setup' first.")
        sys.exit(1)

    load_dotenv(ENV_FILE, override=True)
    console.print("[bold]Post-Apply Summary[/bold]\n")

    # Pull terraform outputs
    try:
        result = subprocess.run(
            ["terraform", "output", "-json"],
            cwd=TF_DIR,
            capture_output=True,
            text=True,
            check=True,
        )
        outputs = json.loads(result.stdout)
    except (FileNotFoundError, subprocess.CalledProcessError) as e:
        console.print(f"[red]Error:[/red] Could not read terraform outputs: {e}")
        console.print("Run 'cd deploy/tf/app && terraform apply' first.")
        sys.exit(1)

    def _out(name, default=""):
        return outputs.get(name, {}).get("value", default)

    lb_ip = _out("lb_public_ip")
    ops_ip = _out("ops_public_ip")
    db_name = _out("db_name")
    db_service_name = _out("db_service_name", f"{db_name}_high" if db_name else "")
    db_admin_password = _out("db_admin_password")

    # Copy wallet from tf generated dir to deploy/generated/wallet.zip
    source_wallet = TF_DIR / "generated" / "wallet.zip"
    if source_wallet.exists():
        GENERATED_DIR.mkdir(parents=True, exist_ok=True)
        target_wallet = GENERATED_DIR / "wallet.zip"
        shutil.copy2(source_wallet, target_wallet)
        console.print(f"[green]Wallet copied to:[/green] {target_wallet}\n")
    else:
        console.print(
            f"[yellow]Warning:[/yellow] Wallet not found at {source_wallet}. "
            "It will appear after a successful terraform apply."
        )

    ssh_key = os.getenv("SSH_PRIVATE_KEY_PATH", "")
    ssh_cmd = f"ssh -i {ssh_key} opc@{ops_ip}" if ssh_key else f"ssh opc@{ops_ip}"

    console.print(
        Panel(
            f"Web UI:        http://{lb_ip}/\n"
            f"Backend API:   http://{lb_ip}/api/v1/agent/chat\n"
            f"Health check:  curl http://{lb_ip}/actuator/health\n"
            f"Ops SSH:       {ssh_cmd}\n"
            f"DB name:       {db_name}\n"
            f"DB service:    {db_service_name}",
            title="Access",
        )
    )

    backend_ip = _out("backend_private_ip")
    web_ip = _out("web_private_ip")
    ollama_ip = _out("ollama_private_ip")

    ops_ssh = f"ssh -i {ssh_key} opc@{ops_ip}" if ssh_key else f"ssh opc@{ops_ip}"
    hop_ssh = "ssh -i /home/opc/private.key opc@{}"

    console.print("\n[bold]Troubleshooting (copy/paste in order)[/bold]")

    console.print(f"\n[bold cyan]Ops bastion ({ops_ip})[/bold cyan]")
    console.print(f"  {ops_ssh}")
    console.print("  sudo cloud-init status")
    console.print("  sudo tail -n 200 /var/log/cloud-init-output.log")
    console.print("  tail -n 200 /home/opc/ansible-playbook.log")

    for label, host, svc in [
        ("Backend", backend_ip, "backend"),
        ("Web", web_ip, "web"),
        ("Ollama", ollama_ip, "ollama"),
    ]:
        if not host:
            continue
        console.print(f"\n[bold cyan]{label} ({host}) — hop via ops[/bold cyan]")
        console.print(f"  {ops_ssh}")
        console.print(f"  {hop_ssh.format(host)}")
        console.print("  sudo cloud-init status")
        console.print("  sudo tail -n 200 /var/log/cloud-init-output.log")
        console.print(f"  sudo systemctl status {svc} --no-pager")
        console.print(f"  sudo journalctl -u {svc} -n 200 --no-pager")
    console.print()

    console.print("[bold]Point your local backend at Autonomous (laptop testing):[/bold]")
    console.print(
        "  unzip -o deploy/generated/wallet.zip -d deploy/generated/wallet\n"
        f"  export TNS_ADMIN=$(pwd)/deploy/generated/wallet\n"
        f'  export DB_URL="jdbc:oracle:thin:@{db_service_name}?TNS_ADMIN=$TNS_ADMIN"\n'
        f"  export DB_USERNAME=ADMIN\n"
        f'  export DB_PASSWORD="{db_admin_password}"\n'
        f"  cp src/chatserver/src/main/resources/application-cloud.yaml.example \\\n"
        f"     src/chatserver/src/main/resources/application-cloud.yaml\n"
        f"  cd src/chatserver && ./gradlew bootRun --args='--spring.profiles.active=cloud'\n"
    )


@cli.command()
def clean():
    """Clean up all generated and build files. Safe: refuses if tf state has resources."""
    console.print("[bold]Clean Up[/bold]\n")

    has_resources = False
    tf_state = TF_DIR / "terraform.tfstate"
    if tf_state.exists():
        try:
            state = json.loads(tf_state.read_text())
            has_resources = len(state.get("resources", [])) > 0
        except (json.JSONDecodeError, KeyError):
            has_resources = True

    if has_resources:
        console.print("[yellow]Terraform state has active resources.[/yellow]")
        console.print("Destroy infrastructure first:\n")
        console.print("  cd deploy/tf/app")
        console.print("  terraform destroy\n")
        console.print("Then re-run: [bold]python manage.py clean[/bold]")
        return

    files = [
        ENV_FILE,
        TF_DIR / "terraform.tfvars",
        TF_DIR / "terraform.tfstate",
        TF_DIR / "terraform.tfstate.backup",
        TF_DIR / "tfplan",
        TF_DIR / "outputs.json",
        TF_DIR / ".terraform.lock.hcl",
    ]
    dirs = [
        TF_DIR / "generated",
        TF_DIR / ".terraform",
        GENERATED_DIR,
        PROJECT_ROOT / "src" / "chatserver" / "build",
        PROJECT_ROOT / "src" / "chatserver" / ".gradle",
    ]

    deleted = []
    for f in files:
        if f.exists():
            f.unlink()
            deleted.append(str(f.relative_to(PROJECT_ROOT)))
    for d in dirs:
        if d.exists():
            shutil.rmtree(d)
            deleted.append(str(d.relative_to(PROJECT_ROOT)))

    if deleted:
        console.print("[green]Deleted:[/green]")
        for item in deleted:
            console.print(f"  {item}")
    else:
        console.print("Nothing to clean.")


if __name__ == "__main__":
    cli()
