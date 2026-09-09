# A random admin password generated at apply time and surfaced as a sensitive output.
# The pattern satisfies Oracle's password complexity requirements (mixed case + digits
# + non-quote special, length >= 12).
#
# Specials are deliberately constrained: no `#` (dotenv treats it as an inline comment
# in unquoted values) and no single/double quotes (would break the quoted .env output).
resource "random_password" "db_admin" {
  length           = 20
  special          = true
  min_lower        = 2
  min_upper        = 2
  min_numeric      = 2
  min_special      = 2
  override_special = "_-@"
}

# TLS-only ADBs (no wallet) require an ACL. We auto-detect the machine's public IP
# and whitelist it. If your IP changes (laptop, VPN, coffee shop), re-run
# `terraform apply` and the ACL updates in-place.
data "http" "my_ip" {
  url = "https://api.ipify.org"
}

locals {
  my_ip = chomp(data.http.my_ip.response_body)
}

# Always Free Autonomous AI Database, version 26ai, TLS-only (no wallet required).
resource "oci_database_autonomous_database" "agent_memory" {
  compartment_id              = local.compartment_id
  db_name                     = var.db_name
  display_name                = var.db_display_name
  admin_password              = random_password.db_admin.result
  db_version                  = "26ai"
  db_workload                 = "OLTP"
  is_free_tier                = true
  is_mtls_connection_required = false
  whitelisted_ips             = [local.my_ip]
}

# Pick the MEDIUM consumer group with TLS-only auth — that's the right balance of
# concurrency vs. throughput for an app like this, and TLS-only means no wallet to ship.
locals {
  tls_profiles = [
    for p in oci_database_autonomous_database.agent_memory.connection_strings[0].profiles :
    p if p.consumer_group == "MEDIUM" && p.tls_authentication == "SERVER"
  ]
  connect_string = local.tls_profiles[0].value
}
