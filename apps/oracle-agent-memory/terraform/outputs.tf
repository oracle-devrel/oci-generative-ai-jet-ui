output "db_password" {
  description = "ADMIN password (sensitive)."
  value       = random_password.db_admin.result
  sensitive   = true
}

output "db_connect_string" {
  description = "Full TNS connect string (TLS-only, no wallet needed)."
  value       = local.connect_string
  sensitive   = true
}

output "compartment_ocid" {
  value = local.compartment_id
}

output "region" {
  value = var.region
}

output "genai_endpoint" {
  value = "https://inference.generativeai.${var.region}.oci.oraclecloud.com"
}

# Convenience: pipe this straight into ../.env
#   terraform output -raw env_file > ../.env
output "env_file" {
  description = "A ready-to-use .env file. Pipe with: terraform output -raw env_file > ../.env"
  sensitive   = true
  # Values are single-quoted so dotenv treats them as literals.
  # Without quotes:  `#` starts an inline comment, `$VAR` may get interpolated
  # by some shells. Single quotes preserve every character as-is.
  value       = <<-EOT
ORACLE_USER=ADMIN
ORACLE_PASSWORD='${random_password.db_admin.result}'
ORACLE_CONNECT_STRING='${local.connect_string}'
OCI_GENAI_ENDPOINT=https://inference.generativeai.${var.region}.oci.oraclecloud.com
OCI_COMPARTMENT_ID=${local.compartment_id}
PORT=3001
DEMO_USER_ID=allen
EOT
}
