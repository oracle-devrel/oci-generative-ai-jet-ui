data "oci_identity_tenancy" "tenant_details" {
  tenancy_id = var.tenancy_ocid

  provider = oci
}

data "oci_identity_regions" "home" {
  filter {
    name   = "key"
    values = [data.oci_identity_tenancy.tenant_details.home_region_key]
  }

  provider = oci
}

data "oci_containerengine_cluster_option" "oke" {
  cluster_option_id = "all"
}

data "oci_database_autonomous_db_versions" "adb_versions" {
    compartment_id = var.compartment_ocid
    db_workload = var.autonomous_database_db_workload

     filter {
        name   = "version"
        values = ["23ai"]
    }
}