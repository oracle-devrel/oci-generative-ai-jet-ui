data "oci_database_autonomous_db_versions" "adb_versions" {
  compartment_id = var.compartment_ocid
  db_workload    = var.autonomous_database_db_workload

  filter {
    name   = "version"
    values = ["23ai"]
  }
}
