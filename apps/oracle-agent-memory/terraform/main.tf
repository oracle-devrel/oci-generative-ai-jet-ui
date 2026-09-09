terraform {
  required_version = ">= 1.5"
  required_providers {
    oci = {
      source  = "oracle/oci"
      version = "~> 6.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
    http = {
      source  = "hashicorp/http"
      version = "~> 3.4"
    }
  }
}

provider "oci" {
  # Reads ~/.oci/config (DEFAULT profile) by default.
  # If you keep multiple OCI profiles, set OCI_CONFIG_PROFILE in your env,
  # or set config_file_profile here.
  region = var.region
}
