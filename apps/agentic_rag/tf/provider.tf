provider "oci" {
  tenancy_ocid        = var.tenancy_ocid
  region              = var.region
  config_file_profile = var.config_file_profile
}

provider "oci" {
  alias        = "home"
  tenancy_ocid = var.tenancy_ocid
  region       = lookup(data.oci_identity_regions.home.regions[0], "name")
  config_file_profile = var.config_file_profile
}
