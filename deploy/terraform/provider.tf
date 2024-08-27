locals {
  home_region_key = [for key, value in data.oci_identity_region_subscriptions.region_subscriptions.region_subscriptions: key if value.is_home_region == true][0]
  home_region = data.oci_identity_region_subscriptions.region_subscriptions.region_subscriptions[local.home_region_key]
}

provider "oci" {
  tenancy_ocid         = var.tenancy_ocid
  region               = var.region
  config_file_profile  = var.config_file_profile
}

provider "oci" {
  alias                 = "home"
  tenancy_ocid          = var.tenancy_ocid
  region                = local.home_region.region_name
  config_file_profile   = var.config_file_profile
}
