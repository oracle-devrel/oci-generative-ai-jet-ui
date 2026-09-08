resource "oci_database_autonomous_database" "picooraclaw" {
  count = var.use_autonomous_db ? 1 : 0

  compartment_id           = var.compartment_ocid
  display_name             = "picooraclaw-adb"
  db_name                  = "picoraclaw"
  db_workload              = "OLTP"
  is_free_tier             = true
  cpu_core_count           = 1
  data_storage_size_in_tbs = 1
  admin_password           = var.adb_admin_password
  is_auto_scaling_enabled  = false

  freeform_tags = {
    "app" = "picooraclaw"
  }
}

resource "oci_database_autonomous_database_wallet" "picooraclaw" {
  count = var.use_autonomous_db ? 1 : 0

  autonomous_database_id = oci_database_autonomous_database.picooraclaw[0].id
  password               = var.adb_admin_password
  base64_encode_content  = true
  generate_type          = "SINGLE"
}
