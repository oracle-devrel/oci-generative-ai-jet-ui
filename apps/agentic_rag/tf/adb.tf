locals {
  db_version = data.oci_database_autonomous_db_versions.adb_versions.autonomous_db_versions[0].version
}

resource "oci_database_autonomous_database" "adb" {
  compartment_id = var.compartment_ocid
  db_name        = "${var.project_name}${local.deploy_id}"

  admin_password              = random_password.adb_admin_password.result
  cpu_core_count              = var.autonomous_database_cpu_core_count
  data_storage_size_in_tbs    = var.autonomous_database_data_storage_size_in_tbs
  db_workload                 = var.autonomous_database_db_workload
  db_version                  = local.db_version
  display_name                = "${var.project_name}${local.deploy_id}"
  is_mtls_connection_required = true
  whitelisted_ips             = var.autonomous_database_db_whitelisted_ips
  is_auto_scaling_enabled     = true
  license_model               = var.autonomous_database_db_license
}

resource "oci_database_autonomous_database_wallet" "adb_wallet" {
  autonomous_database_id = oci_database_autonomous_database.adb.id
  password               = random_password.adb_admin_password.result
  base64_encode_content  = "true"
}

resource "local_file" "adb_wallet_file" {
  content_base64 = oci_database_autonomous_database_wallet.adb_wallet.content
  filename       = "${path.module}/generated/wallet.zip"
}