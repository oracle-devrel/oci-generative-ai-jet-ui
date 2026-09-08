# Terraform: provision the database

This stack provisions the Oracle infrastructure the app needs:

- An **Always Free Autonomous AI Database 26ai**, TLS-only (no wallet)
- A randomly generated `ADMIN` password
- An `.env` snippet you pipe straight into the project root

Cost: **$0** — every resource is in the Always Free pool.

## What it does NOT provision

Your OCI **API signing key** (the `~/.oci/config` + private key the Terraform provider itself uses to authenticate). That's a chicken-and-egg problem and stays a one-time manual step. If you don't have it yet:

1. OCI Console → Profile (top right) → **User settings** → API keys
2. **Add API key** → **Generate API key pair** → download both
3. Save private key to `~/.oci/oci_api_key.pem`
4. Paste the config snippet into `~/.oci/config`

## Use

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
# edit terraform.tfvars and set tenancy_ocid

terraform init
terraform apply
```

The DB takes 1–10 minutes to come up — free-tier provisioning queues behind paid requests in busy regions, so don't be alarmed if it sits at "Provisioning" for a while. You can watch progress in the OCI Console under Oracle Database → Autonomous Database.

When `terraform apply` returns, write the generated `.env` to the project root:

```bash
# macOS / Linux / WSL
terraform output -raw env_file > ../.env
```

```powershell
# PowerShell — DO NOT use `>` for redirection. PowerShell's default redirect writes
# UTF-16 with a BOM, which dotenv parses as garbage. Use one of these instead:

# PowerShell 7+
terraform output -raw env_file | Out-File ../.env -Encoding utf8NoBOM

# PowerShell 5.1
[IO.File]::WriteAllText("$PWD\..\.env", (terraform output -raw env_file))
```

Now you're ready to run `npm run schema && npm run seed`.

## Tear down

```bash
terraform destroy
```

Removes the Autonomous Database. Always Free resources are free regardless, but cleaning up keeps the Console tidy and frees the free-tier slot if you want to reuse it for something else.

## Choosing a region

OCI Generative AI is region-specific. Stick with `us-chicago-1` or `us-ashburn-1` unless you have a reason. The `variables.tf` validator will reject anything that doesn't currently host Generative AI.
